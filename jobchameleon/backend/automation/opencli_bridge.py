"""OpenCLI browser bridge — drive the user's real, logged-in Chrome.

OpenCLI (https://github.com/jackwener/OpenCLI) turns any website into a CLI and
operates on the user's *logged-in* browser through a small daemon + Browser
Bridge extension. That is exactly what job-application automation needs: ATSs
that require sign-in, OAuth popups, or email-verification codes work because the
session is the user's own Chrome profile, not a throwaway Playwright context.

This module shells out to the ``opencli`` binary (installed in the image / host)
and drives the ``opencli browser <session> ...`` primitives: open, find, fill,
type, select, upload, click, wait, close.

When the ``opencli`` daemon cannot be reached (e.g. the gateway runs inside a
container while the browser bridge lives on the user's desktop), the bridge
fails closed with a human-readable status instead of guessing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from typing import Any

_log = logging.getLogger(__name__)

# Session name used for all browser automation (stable across multi-step flows).
SESSION = "work"

# Configurable binary + daemon. ``JC_OPENCLI_ENABLED`` lets an operator turn the
# whole feature off without touching the image.
_OPENCLI_BIN = os.environ.get("JC_OPENCLI_BIN", "opencli")
_OPENCLI_ENABLED = os.environ.get("JC_OPENCLI_ENABLED", "true").lower() in {
    "1", "true", "yes", "on",
}
_OPENCLI_TIMEOUT_S = int(os.environ.get("JC_OPENCLI_TIMEOUT_S", "90"))


class OpenCLIBridgeError(Exception):
    """Raised when OpenCLI itself is unavailable or a command fails."""


def opencli_available() -> bool:
    return _OPENCLI_ENABLED and shutil.which(_OPENCLI_BIN) is not None


async def opencli_status() -> dict:
    """Best-effort health: binary present + ``opencli doctor`` output."""
    if not _OPENCLI_ENABLED:
        return {"enabled": False, "available": False, "reason": "disabled by JC_OPENCLI_ENABLED"}
    binary = shutil.which(_OPENCLI_BIN)
    if not binary:
        return {
            "enabled": True,
            "available": False,
            "bin": _OPENCLI_BIN,
            "reason": "opencli binary not found (install via `npm i -g @jackwener/opencli`)",
        }
    try:
        proc = await asyncio.to_thread(
            _run_sync, ["doctor"], timeout=_OPENCLI_TIMEOUT_S
        )
        return {
            "enabled": True,
            "available": True,
            "bin": binary,
            "doctor_ok": proc.returncode == 0,
            "doctor": (proc.stdout or proc.stderr or "").strip()[-600:],
        }
    except OpenCLIBridgeError as exc:
        return {"enabled": True, "available": True, "bin": binary, "doctor_ok": False, "reason": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"enabled": True, "available": True, "bin": binary, "doctor_ok": False, "reason": str(exc)[:200]}


def _run_sync(args: list[str], timeout: int = _OPENCLI_TIMEOUT_S) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [_OPENCLI_BIN, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise OpenCLIBridgeError(
            "opencli binary not found — install it with `npm i -g @jackwener/opencli`"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise OpenCLIBridgeError(f"opencli {' '.join(args)} timed out after {timeout}s") from exc


async def _run(args: list[str], timeout: int = _OPENCLI_TIMEOUT_S) -> subprocess.CompletedProcess:
    return await asyncio.to_thread(_run_sync, args, timeout)


async def _run_browser(args: list[str], timeout: int = _OPENCLI_TIMEOUT_S) -> str:
    """Run ``opencli browser <SESSION> ...``; return stdout on success."""
    cmd = ["browser", SESSION, *args]
    proc = await _run(cmd, timeout=timeout)
    if proc.returncode != 0:
        detail = (proc.stdout or proc.stderr or "").strip()[-400:]
        raise OpenCLIBridgeError(f"`opencli {cmd[0]} {cmd[1]} {args[0]}` failed (rc={proc.returncode}): {detail}")
    return (proc.stdout or "").strip()


def _extract_json(text: str) -> Any:
    """Pull the first JSON value out of CLI output (the envelopes are JSON-ish)."""
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        pass
    for start, end in (("[", "]"), ("{", "}")):
        idx = text.find(start)
        if idx == -1:
            continue
        end_idx = text.rfind(end)
        if end_idx <= idx:
            continue
        try:
            return json.loads(text[idx : end_idx + 1])
        except (TypeError, ValueError):
            continue
    return None


def _field_type_from_attrs(attrs: dict) -> str:
    """Classify an input by its autocomplete/name/id/placeholder/label."""
    hay = " ".join(
        str(attrs.get(k) or "")
        for k in ("autocomplete", "name", "id", "placeholder", "aria-label", "label")
    ).lower()
    if "linkedin" in hay:
        return "linkedin_url"
    if "github" in hay:
        return "github"
    if "coverletter" in hay or "cover_letter" in hay or "cover letter" in hay:
        return "cover_letter"
    if "resume" in hay or hay == "cv" or "upload-cv" in hay or "attachments" in hay:
        return "resume"
    if "first" in hay and "name" in hay:
        return "first_name"
    if "last" in hay and "name" in hay:
        return "last_name"
    if "full" in hay and "name" in hay:
        return "full_name"
    if "email" in hay or "e-mail" in hay:
        return "email"
    if "phone" in hay or "mobile" in hay or "tel" in hay:
        return "phone"
    if "portfolio" in hay or "website" in hay or "homepage" in hay or "url" in hay:
        return "website"
    if "company" in hay or "employer" in hay or "organization" in hay:
        return "current_company"
    if "city" in hay or "town" in hay:
        return "city"
    return ""


# autocomplete attribute → field type (the strongest, standards-based signal)
_AUTOCOMPLETE_TO_FIELD = {
    "given-name": "first_name",
    "family-name": "last_name",
    "name": "full_name",
    "email": "email",
    "tel": "phone",
    "organization": "current_company",
    "organization-title": "current_company",
    "homepage": "website",
    "url": "website",
    "address-level2": "city",
    "address-level1": "city",
}


def _resolve_answer(field_type: str, candidate: dict) -> str:
    key_map = {
        "first_name": "first_name",
        "last_name": "last_name",
        "full_name": "name",
        "email": "email",
        "phone": "phone",
        "linkedin_url": "linkedin_url",
        "github": "github",
        "website": "website",
        "city": "city",
        "current_company": "current_company",
        "cover_letter": "cover_letter",
    }
    key = key_map.get(field_type)
    if not key:
        return ""
    value = candidate.get(key) or candidate.get(key.replace("_", "")) or ""
    # Fallback: split the candidate name for first/last when only `name` exists.
    if key in {"first_name", "last_name"} and not value:
        parts = str(candidate.get("name") or "").split()
        if key == "first_name":
            value = parts[0] if parts else ""
        else:
            value = " ".join(parts[1:]) if len(parts) > 1 else ""
    return str(value or "").strip()


async def find_form_fields() -> list[dict]:
    """Snapshot the page's form controls via ``find --css``.

    Returns a list of ``{ref, field_type, attrs, tag}`` for input/textarea/select
    elements that map to a candidate identity field.
    """
    out = await _run_browser(["find", "--css", "input,textarea,select"])
    data = _extract_json(out)
    entries = []
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict) and isinstance(data.get("matches"), list):
        raw = data["matches"]
    else:
        raw = _regex_find_entries(out)
    for item in raw:
        if not isinstance(item, dict):
            continue
        attrs = item.get("attrs") or {}
        if isinstance(attrs, str):
            attrs = _attrs_from_string(attrs)
        tag = str(item.get("tag") or attrs.get("tag") or "").lower()
        ref = str(item.get("ref") or item.get("nth") or item.get("index") or "")
        if not ref:
            continue
        input_type = str(attrs.get("type") or "").lower()
        if input_type in {"hidden", "submit", "button", "checkbox", "radio", "password", "search"}:
            continue
        if input_type == "file":
            field_type = "resume"
        else:
            auto_field = _AUTOCOMPLETE_TO_FIELD.get(str(attrs.get("autocomplete") or "").lower())
            field_type = auto_field or _field_type_from_attrs(attrs)
        if not field_type:
            continue
        entries.append(
            {
                "ref": ref,
                "tag": tag or input_type or "input",
                "field_type": field_type,
                "attrs": attrs,
            }
        )
    return entries


def _regex_find_entries(out: str) -> list[dict]:
    entries = []
    # Fallback parser for plain-text envelopes: lines like `[3] <input name=email>`.
    for line in out.splitlines():
        m = re.search(r"\[(\d+)\]\s*<([a-z]+)[^>]*", line)
        if not m:
            continue
        ref, tag = m.group(1), m.group(2)
        attrs = _attrs_from_string(line)
        entries.append({"ref": ref, "tag": tag, "attrs": attrs})
    return entries


def _attrs_from_string(text: str) -> dict:
    attrs: dict[str, str] = {}
    for name, value in re.findall(r"([a-zA-Z_:][\w:.-]*)=([\"'])(.*?)\2", text):
        attrs[name] = value
    for name in re.findall(r"\b(disabled|required|readonly|multiple|checked)\b", text):
        attrs.setdefault(name, "")
    return attrs


async def _fill_field(ref: str, value: str) -> dict:
    out = await _run_browser(["fill", ref, value])
    return {"ok": True, "ref": ref, "output": out[-200:]}


async def _select_field(ref: str, value: str) -> dict:
    out = await _run_browser(["select", ref, value])
    return {"ok": True, "ref": ref, "output": out[-200:]}


async def _upload_file(ref: str, path: str) -> dict:
    out = await _run_browser(["upload", ref, path])
    return {"ok": True, "ref": ref, "output": out[-200:]}


async def _click_submit() -> dict:
    """Click the submit control via the semantic locator (role=button name=*).

    Uses ``click --role button --name <name>`` so OpenCLI resolves the control
    itself — no ref guessing, no ambiguous-CSS surprises. Returns the first
    successful click.
    """
    for name in ("Submit Application", "Submit", "Apply", "Send Application", "Save"):
        try:
            out = await _run_browser(["click", "--role", "button", "--name", name])
        except OpenCLIBridgeError:
            continue
        return {"ok": True, "button": name, "output": out[-200:]}
    return {"ok": False, "button": None, "output": "no submit button found"}


async def apply_with_opencli(
    url: str,
    candidate: dict,
    resume_path: str = "",
) -> dict:
    """Open the job URL in the user's Chrome and fill + submit the application.

    Steps:
      1. ``opencli browser <session> open <url>`` (real, logged-in browser).
      2. Find form controls (``find --css input,textarea,select``).
      3. Fill every field that maps to the candidate identity / cover letter.
      4. Upload the resume to the file input.
      5. Click the submit button; wait for a page change; close the session.

    Returns a JSON-safe report for the UI / websocket broadcast.
    """
    if not opencli_available():
        raise OpenCLIBridgeError(
            "OpenCLI is not available — install the browser bridge extension and "
            "`npm i -g @jackwener/opencli`, then re-run."
        )

    report: dict[str, Any] = {
        "url": url,
        "opened": False,
        "fields_found": 0,
        "fields_filled": [],
        "resume_uploaded": resume_path is not None and resume_path != "",
        "submitted": False,
        "note": "",
    }

    # 1. Open the page in the real browser.
    open_out = await _run_browser(["open", url])
    report["opened"] = True
    report["page_id"] = open_out.strip()[-120:] or None

    # 2. Wait for the form to settle, then snapshot the controls.
    try:
        await _run_browser(["wait", "selector", "form", "--timeout", "8000"])
    except OpenCLIBridgeError:
        pass  # not every application page wraps fields in a <form>
    fields = await find_form_fields()
    report["fields_found"] = len(fields)

    # 3. Fill each matched field (dedupe refs, one value per input).
    filled = set()
    for field in fields:
        ref = field["ref"]
        if ref in filled:
            continue
        field_type = field["field_type"]
        if field_type == "resume":
            continue  # handled in step 4
        value = _resolve_answer(field_type, candidate)
        if not value:
            continue
        try:
            if field.get("tag") == "select":
                await _select_field(ref, value)
            else:
                await _fill_field(ref, value)
            filled.add(ref)
            report["fields_filled"].append({"field": field_type, "ref": ref})
        except OpenCLIBridgeError as exc:
            _log.warning("opencli fill failed for %s @%s: %s", field_type, ref, exc)

    # 4. Upload the resume to any file input.
    if resume_path:
        resume_ref = next((f["ref"] for f in fields if f["field_type"] == "resume"), None)
        if resume_ref and resume_ref not in filled:
            try:
                await _upload_file(resume_ref, resume_path)
                filled.add(resume_ref)
                report["resume_uploaded"] = True
            except OpenCLIBridgeError as exc:
                report["note"] = f"resume upload failed: {exc}"

    # 5. Submit.
    try:
        submit = await _click_submit()
        report["submitted"] = bool(submit.get("ok"))
        if not submit.get("ok"):
            report["note"] = (report.get("note") or "") + " no submit button found"
    except OpenCLIBridgeError as exc:
        report["note"] = (report.get("note") or "") + f" submit failed: {exc}"

    # Best-effort session cleanup; failures are non-fatal.
    try:
        await _run_browser(["close"])
    except OpenCLIBridgeError:
        pass

    return report
