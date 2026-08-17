"""Minimal embedded web console for the JobChameleon gateway.

The JobChameleon sidecar normally exposes no HTTP UI — its interface is the Tauri
desktop shell. Serving a small console at ``/`` (exempt from the bearer-token
middleware, like ``/health``) gives users something sane to open in a browser
instead of a raw ``{"detail": "invalid token"}`` JSON error.

The page is server-rendered with a tiny amount of inline JS that calls the same
authenticated endpoints the Tauri shell uses, using the token the server itself
holds. Styling mirrors the ML-Auditor dashboard (deep navy, teal/blue accent,
Cormorant/Cinzel type) so the two surfaces feel like one product.
"""

from __future__ import annotations

import html as _html

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>JobChameleon — Console</title>
<style>
  :root {
    --bg: hsl(222 45% 4%);
    --panel: hsl(220 40% 6%);
    --panel-2: hsl(222 35% 8%);
    --border: hsl(222 28% 15%);
    --text: hsl(42 30% 94%);
    --muted: hsl(165 18% 64%);
    --teal: hsl(164 60% 48%);
    --teal-bright: hsl(164 60% 56%);
    --blue: hsl(199 80% 55%);
    --ok: hsl(150 55% 52%);
    --warn: hsl(45 85% 55%);
    --err: hsl(0 72% 58%);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; min-height: 100%; }
  body {
    background:
      radial-gradient(70rem 45rem at 12% -12%, hsl(164 70% 42% / 0.12), transparent 55%),
      radial-gradient(55rem 40rem at 108% 12%, hsl(199 70% 45% / 0.10), transparent 55%),
      radial-gradient(45rem 32rem at 50% 120%, hsl(175 60% 42% / 0.06), transparent 60%),
      var(--bg);
    color: var(--text);
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
    background-attachment: fixed;
  }
  ::selection { background: hsl(164 60% 48% / 0.35); color: hsl(42 30% 96%); }
  header {
    padding: 26px 32px 18px;
    border-bottom: 1px solid var(--border);
    background: hsl(222 45% 4% / 0.7);
    backdrop-filter: blur(8px);
    display: flex; align-items: baseline; gap: 16px; flex-wrap: wrap;
  }
  header h1 {
    margin: 0; font-size: 22px; letter-spacing: 0.08em;
    font-family: "Cinzel", "Times New Roman", serif;
    background: linear-gradient(120deg, var(--teal-bright) 10%, var(--blue) 90%);
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  header .sub { color: var(--muted); font-size: 13px; }
  main {
    padding: 26px 32px 48px; display: grid; gap: 20px;
    max-width: 1200px; margin: 0 auto;
  }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
  .card {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 12px; padding: 18px 20px;
    box-shadow: 0 1px 0 hsl(164 60% 48% / 0.05);
  }
  .card h2 {
    margin: 0 0 12px; font-size: 12px; text-transform: uppercase;
    letter-spacing: 0.16em; color: var(--teal-bright);
    font-family: "Cinzel", "Times New Roman", serif;
  }
  .kv { display: grid; grid-template-columns: 150px 1fr; gap: 6px 12px; font-size: 13px; }
  .kv dt { color: var(--muted); }
  .kv dd { margin: 0; font-family: ui-monospace, monospace; word-break: break-word; }
  .pill {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 600; border: 1px solid transparent;
  }
  .pill.ok      { background: hsl(150 55% 52% / 0.12); color: var(--ok);   border-color: hsl(150 55% 52% / 0.35); }
  .pill.degraded{ background: hsl(45 85% 55% / 0.12);  color: var(--warn); border-color: hsl(45 85% 55% / 0.35); }
  .pill.err     { background: hsl(0 72% 58% / 0.12);   color: var(--err);  border-color: hsl(0 72% 58% / 0.35); }
  .pill.lead    { background: hsl(164 60% 48% / 0.12); color: var(--teal-bright); border-color: hsl(164 60% 48% / 0.35); }
  .error { color: var(--err); font-size: 13px; }
  a { color: var(--teal-bright); text-decoration: none; }
  a:hover { color: var(--blue); text-decoration: underline; }
  pre {
    background: hsl(222 45% 3%); border: 1px solid var(--border); border-radius: 8px;
    padding: 12px; font-size: 12px; overflow: auto; max-height: 360px; color: var(--muted);
  }
  .hint { color: var(--muted); font-size: 12px; margin-top: 10px; line-height: 1.5; }

  .lead {
    display: grid; gap: 6px; padding: 14px 16px; margin-bottom: 12px;
    background: var(--panel-2); border: 1px solid var(--border); border-radius: 10px;
  }
  .lead:hover { border-color: hsl(164 60% 48% / 0.4); }
  .lead .lt { font-size: 14px; font-weight: 600; }
  .lead .lc { color: var(--muted); font-size: 13px; }
  .lead .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .lead .score { margin-left: auto; font-variant-numeric: tabular-nums; color: var(--teal-bright); font-weight: 700; }
  .lead .meta { color: var(--muted); font-size: 12px; }
  .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
  button {
    font: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
    color: var(--text); background: hsl(164 60% 48% / 0.12);
    border: 1px solid hsl(164 60% 48% / 0.35); border-radius: 8px;
    padding: 6px 12px; transition: all 0.15s ease;
  }
  button:hover { background: hsl(164 60% 48% / 0.22); border-color: var(--teal-bright); }
  button:disabled { opacity: 0.45; cursor: not-allowed; }
  button.primary {
    background: var(--teal); color: hsl(222 45% 6%);
    border-color: var(--teal);
  }
  button.primary:hover { background: var(--teal-bright); }
  button.ghost { background: transparent; border-color: var(--border); color: var(--muted); }
  button.ghost:hover { color: var(--text); border-color: var(--muted); }
  .feed {
    font-size: 12px; color: var(--muted); margin-top: 8px;
    font-family: ui-monospace, monospace; white-space: pre-wrap;
  }
  .feed.ok { color: var(--ok); }
  .feed.err { color: var(--err); }
  .status-line { display: flex; gap: 8px; align-items: center; }
</style>
</head>
<body>
<header>
  <h1>JobChameleon</h1>
  <span class="sub">Gateway console</span>
  <span class="status-line">
    <span id="s-opencli" class="pill err">opencli …</span>
  </span>
</header>
<main>
  <section class="grid">
    <section class="card">
      <h2>Status</h2>
      <div class="kv">
        <dt>Service</dt><dd><span id="s-status" class="pill">…</span></dd>
        <dt>Uptime</dt><dd id="s-uptime">…</dd>
        <dt>API</dt><dd><a href="/docs" target="_blank" rel="noopener">/docs</a> · <a href="/openapi.json" target="_blank" rel="noopener">openapi.json</a></dd>
        <dt>WebSocket</dt><dd id="s-ws">…</dd>
      </div>
    </section>

    <section class="card">
      <h2>Subsystems</h2>
      <div id="s-subsystems" class="error">Loading…</div>
    </section>

    <section class="card">
      <h2>Configuration</h2>
      <div id="s-config" class="kv"><dd>Loading…</dd></div>
    </section>
  </section>

  <section class="card">
    <h2>Leads</h2>
    <div id="s-leads" class="error">Loading…</div>
    <p class="hint">
      “Apply with OpenCLI” drives your real, logged-in Chrome through the OpenCLI
      Browser Bridge — sign-in / OAuth / email-verification flows work because the
      session is your own browser. Requires the Browser Bridge extension and the
      <code>opencli</code> CLI reachable from this gateway. “Preview” fills the form
      in the headless actuator without submitting; “Read form” returns the detected
      fields and their answers.
    </p>
  </section>

  <section class="card">
    <h2>Raw health</h2>
    <pre id="s-health">…</pre>
  </section>
</main>
<script>
"use strict";
const TOKEN = "__JC_TOKEN__";

async function j(url, opts = {}) {
  const res = await fetch(url, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + TOKEN,
      ...(opts.headers || {}),
    },
  });
  return { ok: res.ok, status: res.status, body: await res.json().catch(() => null) };
}

function pill(status) {
  const cls = status === "ok" || status === "alive" ? "ok"
    : status === "degraded" ? "degraded" : "err";
  return `<span class="pill ${cls}">${status || "unknown"}</span>`;
}

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function kv(entries) {
  return entries.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${v}</dd>`).join("");
}

async function leadAction(jobId, path, btn, label) {
  if (!btn) return;
  const feed = document.getElementById("feed-" + jobId);
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = label + "…";
  try {
    const res = await j("/api/v1/leads/" + encodeURIComponent(jobId) + path, { method: "POST" });
    if (res.ok && res.body) {
      feed.className = "feed ok";
      feed.textContent = label + " started: " + JSON.stringify(res.body);
    } else {
      feed.className = "feed err";
      feed.textContent = (res.body && res.body.detail) ? label + " blocked: " + res.body.detail : label + " failed (HTTP " + res.status + ")";
    }
  } catch (err) {
    feed.className = "feed err";
    feed.textContent = label + " error: " + err;
  } finally {
    btn.textContent = original;
    btn.disabled = false;
  }
}

function renderLeads(items) {
  const box = document.getElementById("s-leads");
  if (!items || !items.length) {
    box.className = "error";
    box.textContent = "No leads yet — generate some from the desktop app first.";
    return;
  }
  box.className = "";
  box.innerHTML = items.map((l) => {
    const jobId = esc(l.job_id || l.id || "");
    const title = esc(l.title || "Untitled");
    const company = esc(l.company || "Unknown company");
    const status = esc(l.status || "discovered");
    const level = esc(l.seniority_level || l.source_meta?.seniority_level || "");
    const score = l.score != null ? "score " + esc(l.score) : "";
    const location = esc(l.location || "");
    const platform = esc(l.platform || "");
    return `<div class="lead">
      <div class="row">
        <span class="lt">${title}</span>
        <span class="pill lead">${status}</span>
        ${level ? `<span class="pill">${level}</span>` : ""}
        <span class="score">${score}</span>
      </div>
      <div class="lc">${company}</div>
      <div class="meta">${location}${location && platform ? " · " : ""}${platform}</div>
      <div class="actions">
        <button class="primary" onclick="leadAction('${jobId}', '/apply/opencli', this, 'Apply with OpenCLI')">Apply with OpenCLI</button>
        <button onclick="leadAction('${jobId}', '/apply/preview', this, 'Preview')">Preview</button>
        <button class="ghost" onclick="leadAction('${jobId}', '/form/read', this, 'Read form')">Read form</button>
      </div>
      <div class="feed" id="feed-${jobId}"></div>
    </div>`;
  }).join("");
}

async function loadOpencli() {
  const el = document.getElementById("s-opencli");
  const res = await j("/api/v1/automation/opencli/status");
  if (res.ok && res.body && res.body.available) {
    el.className = "pill ok";
    el.textContent = "opencli ready";
  } else {
    el.className = "pill degraded";
    el.textContent = "opencli unavailable";
  }
}

(async () => {
  try {
    const health = await j("/health");
    const h = health.body || {};
    document.getElementById("s-status").innerHTML = pill(h.status);
    document.getElementById("s-uptime").textContent =
      h.uptime_seconds != null ? Math.round(h.uptime_seconds) + "s" : "—";
    document.getElementById("s-health").textContent = JSON.stringify(h, null, 2);

    const subs = document.getElementById("s-subsystems");
    if (h.components) {
      subs.innerHTML = `<div class="kv">${kv(
        Object.entries(h.components).map(([name, c]) => [name, pill(c.status || "err")])
      )}</div>`;
    } else {
      subs.textContent = "Run health again with a token for details.";
    }

    const cfg = document.getElementById("s-config");
    const cfgRes = await j("/api/v1/settings");
    if (cfgRes.ok && cfgRes.body) {
      const s = cfgRes.body;
      const rows = [];
      if (s.llm_provider) rows.push(["LLM provider", esc(s.llm_provider)]);
      if (s.nvidia_model) rows.push(["NVIDIA model", esc(s.nvidia_model)]);
      if (s.generation_model) rows.push(["Generation model", esc(s.generation_model)]);
      if (s.leads_score_threshold != null) rows.push(["Lead threshold", esc(s.leads_score_threshold)]);
      if (rows.length) {
        cfg.innerHTML = `<div class="kv">${kv(rows)}</div>`;
      } else {
        cfg.textContent = "No configuration exposed.";
      }
    } else {
      cfg.textContent = "Settings endpoint unavailable: " + (cfgRes.body?.detail || cfgRes.status);
    }

    await loadOpencli();

    const leadsRes = await j("/api/v1/leads?limit=30");
    renderLeads(leadsRes.ok ? leadsRes.body : null);
  } catch (err) {
    document.getElementById("s-status").innerHTML =
      `<span class="pill err">error</span>`;
    document.getElementById("s-health").textContent = String(err);
  }
})();
</script>
</body>
</html>
"""


def render_console(token: str) -> str:
    return _PAGE.replace("__JC_TOKEN__", _html.escape(token or "", quote=True))
