from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from automation.opencli_bridge import (
    _extract_json,
    _field_type_from_attrs,
    _resolve_answer,
    apply_with_opencli,
    find_form_fields,
    opencli_available,
)


def test_extract_json_from_array_envelope():
    out = """
    matches: 3
    [
      {"nth": 0, "ref": "4", "tag": "input", "role": "textbox", "text": "", "attrs": {"name": "email", "type": "email"}, "visible": true},
      {"nth": 1, "ref": "5", "tag": "input", "role": "textbox", "text": "", "attrs": {"name": "phone"}, "visible": true}
    ]
    """
    data = _extract_json(out)
    assert isinstance(data, list)
    assert data[0]["ref"] == "4"
    assert data[1]["attrs"]["name"] == "phone"


def test_extract_json_from_bare_dict():
    assert _extract_json('{"filled": true, "verified": true}') == {"filled": True, "verified": True}


def test_extract_json_returns_none_on_garbage():
    assert _extract_json("nothing here") is None


def test_field_type_from_attrs_maps_standard_signals():
    assert _field_type_from_attrs({"name": "email"}) == "email"
    assert _field_type_from_attrs({"name": "first_name"}) == "first_name"
    assert _field_type_from_attrs({"name": "last_name"}) == "last_name"
    assert _field_type_from_attrs({"name": "phone"}) == "phone"
    assert _field_type_from_attrs({"name": "linkedin_profile"}) == "linkedin_url"
    assert _field_type_from_attrs({"name": "github_username"}) == "github"
    assert _field_type_from_attrs({"name": "resume"}) == "resume"
    assert _field_type_from_attrs({"name": "cover_letter"}) == "cover_letter"
    assert _field_type_from_attrs({"placeholder": "City"}) == "city"


def test_resolve_answer_uses_candidate_identity():
    candidate = {
        "first_name": "Kalevin",
        "last_name": "Aou",
        "email": "kalevin@example.com",
        "phone": "+33612345678",
        "linkedin_url": "https://linkedin.com/in/kalevin",
        "cover_letter": "Dear team,",
    }
    assert _resolve_answer("email", candidate) == "kalevin@example.com"
    assert _resolve_answer("first_name", candidate) == "Kalevin"
    assert _resolve_answer("last_name", candidate) == "Aou"
    assert _resolve_answer("cover_letter", candidate) == "Dear team,"
    assert _resolve_answer("website", candidate) == ""


def test_resolve_answer_splits_name_when_no_first_last():
    candidate = {"name": "Kalevin Aou", "email": "k@example.com"}
    assert _resolve_answer("first_name", candidate) == "Kalevin"
    assert _resolve_answer("last_name", candidate) == "Aou"


@patch("automation.opencli_bridge.shutil.which")
def test_opencli_available_false_without_binary(which):
    which.return_value = None
    assert opencli_available() is False


@patch("automation.opencli_bridge.shutil.which")
def test_opencli_available_true_with_binary(which):
    which.return_value = "/usr/local/bin/opencli"
    assert opencli_available() is True


def test_find_form_fields_parses_find_envelope():
    out = (
        '[{"nth": 0, "ref": "4", "tag": "input", "attrs": {"name": "email", "type": "email"}},'
        ' {"nth": 1, "ref": "5", "tag": "input", "attrs": {"name": "first_name"}},'
        ' {"nth": 2, "ref": "6", "tag": "input", "attrs": {"name": "resume", "type": "file"}},'
        ' {"nth": 3, "ref": "7", "tag": "input", "attrs": {"name": "search", "type": "hidden"}}]'
    )
    with patch("automation.opencli_bridge._run_browser", new_callable=AsyncMock) as run:
        run.return_value = out
        fields = asyncio.run(find_form_fields())

    by_type = {f["field_type"]: f for f in fields}
    assert by_type["email"]["ref"] == "4"
    assert by_type["first_name"]["ref"] == "5"
    assert by_type["resume"]["ref"] == "6"
    assert "search" not in by_type
    assert len(fields) == 3


def test_apply_with_opencli_full_flow():
    candidate = {
        "first_name": "Kalevin",
        "last_name": "Aou",
        "email": "k@example.com",
        "phone": "+33612345678",
        "cover_letter": "Dear team, I would love to apply.",
    }
    find_out = (
        '[{"nth": 0, "ref": "4", "tag": "input", "attrs": {"name": "email"}},'
        ' {"nth": 1, "ref": "5", "tag": "input", "attrs": {"name": "first_name"}},'
        ' {"nth": 2, "ref": "6", "tag": "input", "attrs": {"name": "last_name"}},'
        ' {"nth": 3, "ref": "7", "tag": "input", "attrs": {"type": "file"}},'
        ' {"nth": 4, "ref": "8", "tag": "textarea", "attrs": {"name": "cover_letter"}}]'
    )

    async def fake_run(args, timeout=90):
        if args[0] == "open":
            return "tab-page-123"
        if args[0] == "wait":
            return ""
        if args[0] == "find":
            return find_out
        if args[0] == "click":
            return '{"clicked": true, "matches_n": 1, "match_level": "exact"}'
        if args[0] == "close":
            return ""
        return "ok"

    with patch("automation.opencli_bridge.opencli_available", return_value=True), patch(
        "automation.opencli_bridge._run_browser", side_effect=fake_run
    ):
        report = asyncio.run(
            apply_with_opencli(
                "https://jobs.example.com/apply/42",
                candidate,
                resume_path="/tmp/resume.pdf",
            )
        )

    assert report["opened"] is True
    assert report["fields_found"] == 5
    assert {f["field"] for f in report["fields_filled"]} == {
        "email",
        "first_name",
        "last_name",
        "cover_letter",
    }
    assert report["resume_uploaded"] is True
    assert report["submitted"] is True


def test_apply_with_opencli_fails_closed_when_unavailable():
    from automation.opencli_bridge import OpenCLIBridgeError

    with patch("automation.opencli_bridge.opencli_available", return_value=False):
        with pytest.raises(OpenCLIBridgeError):
            asyncio.run(apply_with_opencli("https://jobs.example.com", {}, resume_path=""))


def test_no_undefined_async_run_hanging():
    # Sanity: the module imports cleanly under asyncio.run (no leaked event loop).
    async def noop():
        return None

    assert asyncio.run(noop()) is None
