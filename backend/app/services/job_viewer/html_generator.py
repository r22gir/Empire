"""Assemble one self-contained HTML file (THREE.js + scene + runtime)."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.job_viewer.privacy import assert_html_safe, scrub_text

STATIC = Path(__file__).resolve().parent / "static"


def _read(name: str) -> str:
    return (STATIC / name).read_text(encoding="utf-8")


def _panel_html(scene: dict) -> str:
    title = scrub_text(scene.get("title") or "Custom piece")
    subtitle = scrub_text(scene.get("subtitle") or "")
    draft = "DRAFT" if scene.get("draft") else ""
    view_btns = "".join(
        f'<button data-v="{key}">{label}</button>'
        for key, label in (("all", "Overall"), ("top", "Top"), ("front", "Front"), ("end", "End"))
        if key in (scene.get("views") or {"all": 1})
    )
    return f"""<div id="p">
<div class="brand-mark">EMPIRE WORKROOM</div>
<h1>EMPIRE WORKROOM</h1>
<div class="sub">{title}{(' · ' + draft) if draft else ''}</div>
<div>{subtitle}</div>
<h2>Fabric color</h2>
<div class="row">Backs <select id="cB"></select></div>
<div class="row">Seats <select id="cS"></select></div>
<button id="pSame">Match seats to backs</button>
<h2>Assembly</h2>
<button id="bA">Assembled</button><button id="bE">Exploded</button>
<input type="range" id="ex" min="0" max="1" step="0.01" value="0">
<h2>Move pieces</h2>
<label class="row"><input type="checkbox" id="mvOn" checked>Drag a piece to move it</label>
<label class="row"><input type="checkbox" id="mvAll" checked>Move whole piece (fabric+foam+ply)</label>
<button id="bRL">⟲ Rotate 15°</button><button id="bRR">⟳ Rotate 15°</button><button id="bR90">Rotate 90°</button><br>
<button id="bHide">Hide selected</button><button id="bShow">Show all</button><button id="bBack">↩ Put back selected</button>
<button id="bReset">⟲ RESET ALL (put every piece home)</button>
<div style="color:#555">Double-click / double-tap a piece = put it back. Bases stay locked.</div>
<h2>View</h2>
<div id="views">{view_btns}</div>
<h2>Groups</h2><div id="grps"></div>
<h2>Runs</h2><div id="runs"></div>
<h2>Layers</h2><div id="layers"></div>
<div style="margin-top:10px;color:#555">
<b>View:</b> drag empty space = rotate · right-drag = pan · wheel / pinch = zoom.<br>
<b>Pieces:</b> click = select · drag = move · Shift-drag = rotate · Alt-drag = lift · Q / E = 15° · R = 90° · Esc = deselect.
</div>
</div>
<div id="hdr">Empire Workroom — {title}{(' — <span>DRAFT</span>' if draft else '')}</div>
<div id="info"></div>
<div id="help">Rotate view: drag empty space · Pan: right-drag · Zoom: wheel/pinch · Move piece: drag it · Put back: double-click · Reset all: red button</div>
<div id="tip"></div>
<noscript><div style="position:fixed;left:290px;top:60px;font-size:16px">JavaScript is required. Open this file in Chrome, Edge, Firefox or Safari.</div></noscript>
"""


def render_html(scene: dict, *, extra_forbidden=None) -> str:
    css = _read("viewer.css")
    three = _read("three.r128.min.js")
    runtime = _read("viewer_runtime.js")
    data_json = json.dumps(scene, ensure_ascii=True, separators=(",", ":"))
    title = scrub_text(scene.get("title") or "Custom piece")
    html = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<title>Empire Workroom 3D Viewer — {title}</title>"
        f"<style>{css}</style></head><body>\n"
        f"{_panel_html(scene)}\n"
        f"<script>\n{three}\n</script>\n"
        f"<script>window.DATA={data_json};</script>\n"
        f"<script>\n{runtime}\n</script>\n"
        "</body></html>\n"
    )
    assert_html_safe(html, extra_forbidden)
    return html
