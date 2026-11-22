"""Renderer: sinh trang HTML/JS hoàn chỉnh từ catalog (thuần Python).

Không có template ngoài, không JS viết tay trong dự án — mọi thứ trang
hiển thị đều bắt nguồn từ ``catalog.py``. Bridge vẫn là ``BotApi`` trong
``app.py`` (không đổi).
"""

from __future__ import annotations

from typing import Any

from COCbot.webui import catalog

_FIELD_TYPES = {"number", "select", "switch"}


def _field_html(field: dict[str, Any]) -> str:
    """Render một field khai báo trong catalog."""
    kind = field["type"]
    if kind not in _FIELD_TYPES:
        raise ValueError(f"catalog: field type khong ho tro: {kind!r}")
    name = field["name"]
    label = field.get("label", name)
    if kind == "number":
        return (
            f'<div class="row"><label>{label}</label>'
            f'<input type="number" data-field="{name}" '
            f'value="{field.get("default", 0)}"></div>'
        )
    if kind == "select":
        options = "".join(
            f'<option>{opt}</option>' for opt in field.get("options", [])
        )
        return (
            f'<div class="row"><label>{label}</label>'
            f'<select data-field="{name}">{options}</select></div>'
        )
    # switch
    checked = "checked" if field.get("default") else ""
    return (
        f'<div class="row"><label>{label}</label>'
        f'<div class="switch"><input type="checkbox" data-field="{name}" '
        f'data-type="switch" {checked}><span></span></div></div>'
    )


def _card_html(card: dict[str, Any]) -> str:
    """Render một card (gồm cả card điều khiển đặc biệt)."""
    title = card.get("title", "")
    body: list[str] = []
    for field in card.get("fields", []):
        body.append(_field_html(field))
    if card.get("status"):
        body.append('<div class="row"><div id="status" class="status">'
                    "Chưa chạy — bấm Start (MEmu tự dò)</div></div>")
    if card.get("buttons"):
        buttons = "".join(
            f'<button id="{b["id"]}" class="btn-{b["style"]}" '
            f'disabled="{"" if b["id"] == "start" else "disabled"}">'
            f'{b["label"]}</button>'
            for b in card["buttons"]
        )
        body.append(f'<div class="row">{buttons}</div>')
    inner = "\n".join(body)
    return (
        f'<div class="card"><h2>{title}</h2>{inner}</div>'
    )


def _tabs_html() -> tuple[str, str, str]:
    """Return (tab bar, tab panes, default pane id)."""
    bar: list[str] = []
    panes: list[str] = []
    first = catalog.TABS[0]["id"] if catalog.TABS else ""
    for tab in catalog.TABS:
        active = " active" if tab["id"] == first else ""
        bar.append(
            f'<button class="tab-btn{active}" data-tab="{tab["id"]}">'
            f'{tab["label"]}</button>'
        )
        if tab.get("special") == "log":
            inner = ('<div id="log"></div>')
        else:
            inner = "\n".join(_card_html(c) for c in tab.get("cards", []))
        display = "block" if tab["id"] == first else "none"
        panes.append(
            f'<div class="pane" id="pane-{tab["id"]}" '
            f'style="display:{display}">{inner}</div>'
        )
    return "\n".join(bar), "\n".join(panes), first


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text);
       font: 13px/1.45 "Segoe UI", sans-serif; user-select: none; }
header { background: var(--header); color: #fff; padding: 10px 14px;
         display: flex; align-items: center; gap: 10px;
         -webkit-app-region: drag; }
header .logo { width: 26px; height: 26px; border-radius: 6px;
               background: var(--primary); display: flex;
               align-items: center; justify-content: center;
               font-weight: 700; font-size: 12px; }
header h1 { font-size: 14px; font-weight: 600; letter-spacing: .5px; }
header .dot { margin-left: auto; width: 10px; height: 10px;
              border-radius: 50%; background: #8aa39a; }
header .dot.running { background: #3ddc84; }
header .dot.paused { background: #f0b429; }
main { padding: 12px; display: flex; flex-direction: column;
       gap: 10px; height: calc(100vh - 46px); }
.card { background: var(--card); border: 1px solid var(--border);
        border-radius: 10px; padding: 10px 12px; }
.card h2 { font-size: 11px; letter-spacing: 1px; color: var(--muted);
           margin-bottom: 8px; text-transform: uppercase; }
.row { display: flex; gap: 8px; align-items: center; }
.row + .row { margin-top: 8px; }
label { flex: 0 0 150px; font-size: 12px; }
input[type=number] { width: 100%; padding: 5px 8px;
        border: 1px solid var(--border); border-radius: 6px;
        font-size: 13px; background: #FAFCFB; }
select { padding: 5px 8px; border: 1px solid var(--border);
         border-radius: 6px; font-size: 13px; background: #FAFCFB; flex: 1; }
.switch { position: relative; width: 34px; height: 19px; }
.switch input { opacity: 0; width: 0; height: 0; }
.switch span { position: absolute; inset: 0; background: #cfd8d4;
               border-radius: 19px; transition: .15s; cursor: pointer; }
.switch span::after { content: ""; position: absolute; width: 13px;
      height: 13px; left: 3px; top: 3px; background: #fff;
      border-radius: 50%; transition: .15s; }
.switch input:checked + span { background: var(--primary); }
.switch input:checked + span::after { left: 18px; }
button { border: 0; border-radius: 8px; padding: 9px 14px;
         font: 600 13px "Segoe UI"; color: #fff; cursor: pointer;
         flex: 1; transition: filter .15s; }
button:hover { filter: brightness(1.08); }
button:disabled { filter: grayscale(.6); cursor: not-allowed; }
.btn-primary { background: var(--primary); }
.btn-warn { background: var(--warn); }
.btn-danger { background: var(--danger); }
.tab-bar { display: flex; gap: 6px; }
.tab-btn { background: var(--card); color: var(--text);
           border: 1px solid var(--border); border-radius: 8px;
           padding: 7px 10px; font: 600 12px "Segoe UI"; flex: 1; }
.tab-btn.active { background: var(--primary); color: #fff;
                  border-color: var(--primary); }
.status { font-size: 12px; color: var(--muted); }
#log { flex: 1; min-height: 0; background: var(--log-bg);
       color: var(--log-fg); border-radius: 10px; padding: 8px 10px;
       overflow-y: auto; font: 11.5px/1.5 Consolas, monospace;
       user-select: text; }
#log .warn { color: #f0b429; } #log .err { color: #ff8f7a; }
#log .ok { color: #3ddc84; }
"""


# JS glue sinh sẵn từ catalog: mọi handler đều generic theo data-field.
_JS = """
let logIndex = 0;
const el = (id) => document.getElementById(id);
const api = () => pywebview.api;

function classify(line) {
  const s = line.toLowerCase();
  if (s.includes("error") || s.includes("loi")) return "err";
  if (s.includes("warn")) return "warn";
  if (s.includes("success") || s.includes("ok")) return "ok";
  return "";
}

function collectForm() {
  const cfg = {};
  document.querySelectorAll("[data-field]").forEach((node) => {
    if (node.dataset.type === "switch") cfg[node.dataset.field] = node.checked;
    else if (node.type === "number") cfg[node.dataset.field] = parseInt(node.value) || 0;
    else cfg[node.dataset.field] = node.value;
  });
  return cfg;
}

async function applySettings(s) {
  document.querySelectorAll("[data-field]").forEach((node) => {
    const v = s[node.dataset.field];
    if (v === undefined) return;
    if (node.dataset.type === "switch") node.checked = !!v;
    else node.value = v;
  });
}

async function pollLogs() {
  try {
    const res = await api().get_logs(logIndex);
    const box = el("log");
    if (!box) return;
    for (const line of res.lines) {
      const div = document.createElement("div");
      div.className = classify(line);
      div.textContent = line;
      box.appendChild(div);
    }
    if (res.lines.length) box.scrollTop = box.scrollHeight;
    logIndex = res.index;
  } catch (e) {}
}

async function pollState() {
  try {
    const s = await api().get_state();
    el("dot").className = "dot " + (s.running ? (s.paused ? "paused" : "running") : "");
    el("start").disabled = s.running;
    el("stop").disabled = !s.running;
    el("pause").disabled = !s.running;
    el("pause").textContent = s.paused ? "Resume" : "Pause";
    el("status").textContent = s.running
      ? (s.paused ? "Dang pause — cho Resume" : "Dang chay @ " + (s.host || "?"))
      : "Chua chay — bam Start (MEmu tu do)";
  } catch (e) {}
}

window.addEventListener("pywebviewready", async () => {
  applySettings(await api().get_settings());
  pollLogs(); pollState();
  setInterval(pollLogs, 600);
  setInterval(pollState, 1200);

  document.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll("[data-tab]").forEach((b) =>
        b.classList.toggle("active", b === btn));
      document.querySelectorAll(".pane").forEach((p) =>
        p.style.display = (p.id === "pane-" + btn.dataset.tab) ? "block" : "none");
    };
  });

  el("start").onclick = async () => {
    const res = await api().start(collectForm());
    if (!res.ok) alert(res.error);
    pollState();
  };
  el("pause").onclick = async () => {
    const s = await api().get_state();
    if (s.paused) await api().resume(); else await api().pause();
    pollState();
  };
  el("stop").onclick = async () => { await api().stop(); pollState(); };
});
"""


def render_page() -> str:
    """Return the full HTML page generated from the catalog."""
    tokens = "".join(
        f"    --{key}: {value};\n" for key, value in catalog.THEME.items()
    )
    bar, panes, _first = _tabs_html()
    control = _card_html(catalog.CONTROL_CARD)
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{catalog.TITLE}</title>
<style>
:root {{
{tokens}    --width: {catalog.WINDOW['width']}px;
    --height: {catalog.WINDOW['height']}px;
}}
{_CSS}</style>
</head>
<body>
<header>
  <div class="logo">M</div>
  <h1>{catalog.TITLE}</h1>
  <div id="dot" class="dot"></div>
</header>
<main>
{control}
<div class="tab-bar">
{bar}
</div>
{panes}
</main>
<script>
{_JS}</script>
</body>
</html>
"""
