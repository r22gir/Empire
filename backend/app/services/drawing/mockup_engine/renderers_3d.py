"""3D parametric model renderer for PieceSpec.

Generates:
1. Self-contained HTML Three.js live viewer (orbit controls, view buttons, HUD, footer, responsive canvas, realistic lighting, shadows).
2. Orthographic / Isometric 2D projection stills rendered directly into PDF/PNG.
3. Optional standard GLB binary export.

Follows Empire Workroom / Willard live model standards and Rafael's construction rules:
- Platform / base as its own layer
- Seat cushion as its own layer (with front overhang ≥ 1", foam thickness)
- Rounded vertical channel back with seams, mathematically computed from piece runs
- Clean corner joins (square or radiused inside corner arcs)
- Optional back rake angle / lean
"""
from __future__ import annotations

import os
import json
import math
import struct
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color

from app.services.drawing.mockup_engine.spec import PieceSpec, SegmentSpec
from app.services.drawing.mockup_engine.math_layout import compute_channels
from app.services.drawing.mockup_engine.generator import render_pdf_to_png_previews


def build_viewer_html(spec: PieceSpec, title: Optional[str] = None) -> str:
    """Generate self-contained Three.js live model viewer HTML matching the Willard style."""
    spec_data = spec.model_dump()
    spec_json = json.dumps(spec_data)
    
    piece_title = title or f"{spec.name.upper()} · LIVE 3D MODEL"
    quote_tag = f"{spec.quote_number} · {spec.status}"
    client_line = f"CLIENT: {spec.client_name}"
    if spec.client_address:
        client_line += f" · {spec.client_address}"
        
    company = "WOODCRAFT BY EMPIRE" if spec.business_unit == "woodcraft" else "EMPIRE WORKROOM"
    tagline = "CUSTOM CNC & ARCHITECTURAL MILLWORK" if spec.business_unit == "woodcraft" else "CUSTOM UPHOLSTERY & FABRICATION"
    footer_left = f"{company} · 5124 FROLICH LN, HYATTSVILLE, MD 20781 · (703) 213-6484 · WORKROOM.EMPIREBOX.STORE"
    footer_right = f"{quote_tag} · PARAMETRIC 3D ENGINE"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{piece_title}</title>
<style>
  html,body{{margin:0;height:100%;overflow:hidden;background:#efece3;font-family:Helvetica,Arial,sans-serif}}
  #hud{{position:fixed;top:0;left:0;right:0;padding:16px 24px;pointer-events:none;
       background:linear-gradient(rgba(239,236,227,0.95),rgba(239,236,227,0));z-index:10}}
  #hud h1{{margin:0;font-size:18px;letter-spacing:.04em;color:#1c1917;font-family:'Times New Roman',serif}}
  #hud p{{margin:4px 0 0;font-size:12px;color:#57534e}}
  #badge{{position:fixed;top:16px;right:20px;text-align:right;font-size:11px;color:#78716c;pointer-events:none;z-index:10}}
  #badge strong{{color:#a2542f;display:block;font-size:12px;letter-spacing:.03em}}
  #foot{{position:fixed;left:0;right:0;bottom:0;padding:10px 20px;background:#1c1917;color:#faf8f4;
        font-size:11px;display:flex;justify-content:space-between;font-weight:bold;z-index:10}}
  #foot span:last-child{{color:#d4af37}}
  #ctl{{position:fixed;right:20px;top:80px;display:flex;flex-direction:column;gap:6px;z-index:20}}
  #ctl button{{pointer-events:auto;border:1px solid #78716c;background:#faf8f4;color:#1c1917;
      font:600 11px Helvetica,Arial,sans-serif;padding:7px 12px;border-radius:3px;cursor:pointer;
      box-shadow:0 1px 3px rgba(0,0,0,0.08);transition:all .15s ease}}
  #ctl button:hover{{background:#f5f0e6;border-color:#a2542f}}
  #ctl button.on{{background:#4a2f18;color:#f0e6d2;border-color:#4a2f18}}
</style>
</head>
<body>
<div id="hud">
  <h1>{piece_title}</h1>
  <p>Drag to orbit · scroll/pinch to zoom · parametric geometry generated from shop construction specification</p>
</div>
<div id="badge">
  <strong>{company}</strong>
  <span>{client_line}</span>
</div>
<div id="ctl">
  <button id="bFront">Front</button>
  <button id="bIso">Isometric</button>
  <button id="bTop">Top / Plan</button>
  <button id="bRear">Rear</button>
  <button id="bBase" class="on">Show Base</button>
</div>
<div id="foot">
  <span>{footer_left}</span>
  <span>{footer_right}</span>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const SPEC = {spec_json};

/* Scene Setup */
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xefece3);

const cam = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 1, 2500);
const ren = new THREE.WebGLRenderer({{antialias: true, alpha: false}});
ren.setPixelRatio(Math.min(devicePixelRatio, 2));
ren.setSize(innerWidth, innerHeight);
ren.shadowMap.enabled = true;
ren.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(ren.domElement);

scene.add(new THREE.HemisphereLight(0xfff6ea, 0x8c8270, 0.95));
const key = new THREE.DirectionalLight(0xffffff, 0.75);
key.position.set(-160, 240, 200);
key.castShadow = true;
scene.add(key);

const fill = new THREE.DirectionalLight(0xffeedd, 0.35);
fill.position.set(180, 120, -140);
scene.add(fill);

/* Materials */
function parseHex(hexStr, defaultHex) {{
  if (!hexStr) return defaultHex;
  return parseInt(hexStr.replace('#', '0x'), 16);
}}

const vinylColor = parseHex(SPEC.material?.color_hex, 0x9A5B2E);
const seatColor = parseHex(SPEC.material?.seat_color_hex, 0xA8693A);
const seamColor = parseHex(SPEC.material?.seam_color_hex, 0x5E3518);

const M = {{
  cushion: new THREE.MeshStandardMaterial({{color: seatColor, roughness: 0.65, metalness: 0.05}}),
  channel: new THREE.MeshStandardMaterial({{color: vinylColor, roughness: 0.65, metalness: 0.05}}),
  seam: new THREE.LineBasicMaterial({{color: seamColor, linewidth: 2}}),
  base: new THREE.MeshStandardMaterial({{color: 0x2b2622, roughness: 0.85}}),
  wood: new THREE.MeshStandardMaterial({{color: 0x8b5a2b, roughness: 0.5}}),
  edge: new THREE.LineBasicMaterial({{color: 0x3d2716, linewidth: 1}})
}};

const root = new THREE.Group();
scene.add(root);

/* Parametric Dimensions & Rafael's Rules:
   - seat depth includes ~2in back thickness (18" overall = 2" back + 16" seat)
   - seat cushion overhangs front by >= 1"
   - platform/base is recessed
*/
const backThk = Math.max(2.0, SPEC.footprint?.back_thickness_in || 2.5);
const totalSeatDepth = SPEC.cushion?.seat_depth_in || 18.0;
const netSeatDepth = totalSeatDepth - backThk; // e.g. 18 - 2.5 = 15.5
const seatOverhang = Math.max(1.0, SPEC.cushion?.front_overhang_in || 1.25);
const seatH = SPEC.cushion?.seat_height_in || 18.0;
const cushThk = SPEC.cushion?.cushion_thickness_in || 4.0;
const baseH = seatH - cushThk; // platform height
const netBackH = SPEC.back?.net_back_height_in || 26.75;
const totalH = seatH + netBackH;

const shape = SPEC.footprint?.shape || "straight";
const segs = SPEC.footprint?.segments || [];
const segDict = {{}};
segs.forEach(s => {{ segDict[s.name.toLowerCase()] = s.length_in; }});

const cornerStyle = SPEC.footprint?.corner_style || "square";
const insideRadius = SPEC.footprint?.inside_corner_radius_in || 0.0;

const baseGroup = new THREE.Group();
const cushionGroup = new THREE.Group();
const backGroup = new THREE.Group();
root.add(baseGroup, cushionGroup, backGroup);

/* Channel generator: rounded fluted extrusion with edge seams */
function createChannelMesh(width, height, depth) {{
  const shape = new THREE.Shape();
  const r = Math.min(width * 0.15, depth * 0.4);
  const w = width;
  const d = depth;
  
  // Curved front face for authentic channeled look
  shape.moveTo(0, 0);
  shape.lineTo(w, 0);
  shape.lineTo(w, d - r);
  shape.quadraticCurveTo(w, d, w - r, d);
  shape.lineTo(r, d);
  shape.quadraticCurveTo(0, d, 0, d - r);
  shape.closePath();

  const geom = new THREE.ExtrudeGeometry(shape, {{
    depth: height,
    bevelEnabled: true,
    bevelSegments: 3,
    steps: 1,
    bevelSize: 0.25,
    bevelThickness: 0.25,
  }});
  geom.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geom, M.channel);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  
  // Seam lines on borders
  const edges = new THREE.EdgesGeometry(geom, 25);
  const line = new THREE.LineSegments(edges, M.edge);
  mesh.add(line);
  return mesh;
}}

/* Construct Model based on Footprint Shape */
if (shape === "u_shape") {{
  const leftLen = segDict["left"] || 37.75;
  const mainLen = segDict["main"] || 249.75;
  const rightLen = segDict["right"] || 48.5;
  
  // Center bench around origin (X: along main, Z: along returns)
  const x0 = -mainLen / 2;
  const x1 = mainLen / 2;
  const zWall = 0;
  
  /* BASE LAYER (recessed by 2" toe kick) */
  const baseRecess = 2.0;
  // Main base
  const bMain = new THREE.Mesh(
    new THREE.BoxGeometry(mainLen - 2 * (totalSeatDepth - baseRecess), baseH, totalSeatDepth - baseRecess),
    M.base
  );
  bMain.position.set(0, baseH / 2, -(totalSeatDepth - baseRecess) / 2);
  baseGroup.add(bMain);
  
  // Left base
  const bLeft = new THREE.Mesh(
    new THREE.BoxGeometry(totalSeatDepth - baseRecess, baseH, leftLen - baseRecess),
    M.base
  );
  bLeft.position.set(x0 + (totalSeatDepth - baseRecess) / 2, baseH / 2, -(leftLen - baseRecess) / 2);
  baseGroup.add(bLeft);
  
  // Right base
  const bRight = new THREE.Mesh(
    new THREE.BoxGeometry(totalSeatDepth - baseRecess, baseH, rightLen - baseRecess),
    M.base
  );
  bRight.position.set(x1 - (totalSeatDepth - baseRecess) / 2, baseH / 2, -(rightLen - baseRecess) / 2);
  baseGroup.add(bRight);
  
  /* SEAT CUSHION LAYER (with front overhang) */
  const cMain = new THREE.Mesh(
    new THREE.BoxGeometry(mainLen, cushThk, totalSeatDepth + seatOverhang),
    M.cushion
  );
  cMain.position.set(0, baseH + cushThk / 2, -(totalSeatDepth + seatOverhang) / 2 + backThk);
  cMain.castShadow = true;
  cMain.receiveShadow = true;
  cushionGroup.add(cMain);
  cMain.add(new THREE.LineSegments(new THREE.EdgesGeometry(cMain.geometry), M.edge));

  const cLeft = new THREE.Mesh(
    new THREE.BoxGeometry(totalSeatDepth + seatOverhang, cushThk, leftLen),
    M.cushion
  );
  cLeft.position.set(x0 + (totalSeatDepth + seatOverhang) / 2 - backThk, baseH + cushThk / 2, -leftLen / 2);
  cushionGroup.add(cLeft);
  cLeft.add(new THREE.LineSegments(new THREE.EdgesGeometry(cLeft.geometry), M.edge));

  const cRight = new THREE.Mesh(
    new THREE.BoxGeometry(totalSeatDepth + seatOverhang, cushThk, rightLen),
    M.cushion
  );
  cRight.position.set(x1 - (totalSeatDepth + seatOverhang) / 2 + backThk, baseH + cushThk / 2, -rightLen / 2);
  cushionGroup.add(cRight);
  cRight.add(new THREE.LineSegments(new THREE.EdgesGeometry(cRight.geometry), M.edge));

  /* BACKREST LAYER - 12" VERTICAL CHANNELS */
  // Main back run (along X axis at Z = 0)
  const chWidth = SPEC.back?.channel_width_in || 12.0;
  
  function layoutLinearChannels(length, startX, startZ, dirX, dirZ, parentGroup) {{
    const nFull = Math.floor(length / chWidth);
    const rem = length - nFull * chWidth;
    const endTrim = rem > 0.001 ? rem / 2.0 : 0.0;
    
    const widths = [];
    if (endTrim > 0) widths.push(endTrim);
    for (let i = 0; i < nFull; i++) widths.push(chWidth);
    if (endTrim > 0) widths.push(endTrim);
    
    let curOffset = 0;
    for (const w of widths) {{
      const chMesh = createChannelMesh(w, netBackH, backThk);
      chMesh.position.set(startX + (curOffset) * dirX, seatH, startZ + (curOffset) * dirZ);
      if (dirZ !== 0) {{
        chMesh.rotation.y = dirZ > 0 ? -Math.PI / 2 : Math.PI / 2;
      }}
      parentGroup.add(chMesh);
      curOffset += w;
    }}
  }}

  if (cornerStyle === "curved" && insideRadius > 0) {{
    // Curved inside corners: place radial fanning channels at the two corners
    const R = insideRadius;
    const sweep = Math.PI / 2;
    const straightMain = mainLen - 2 * R;
    const straightLeft = leftLen - R;
    const straightRight = rightLen - R;
    
    // Main straight center
    layoutLinearChannels(straightMain, x0 + R, 0, 1, 0, backGroup);
    // Left straight
    layoutLinearChannels(straightLeft, x0, -leftLen, 0, 1, backGroup);
    // Right straight
    layoutLinearChannels(straightRight, x1, -R, 0, -1, backGroup);
    
    // Left & Right corner radial fan
    const nCornerChannels = 3;
    for (const [cornerX, cornerZ, startAng, sign] of [
      [x0 + R, -R, Math.PI, 1],
      [x1 - R, -R, -Math.PI / 2, -1]
    ]) {{
      for (let ci = 0; ci < nCornerChannels; ci++) {{
        const a1 = startAng + sign * (ci / nCornerChannels) * sweep;
        const a2 = startAng + sign * ((ci + 1) / nCornerChannels) * sweep;
        const aMid = (a1 + a2) / 2;
        const arcW = R * (sweep / nCornerChannels);
        const chMesh = createChannelMesh(arcW, netBackH, backThk);
        chMesh.position.set(cornerX + R * Math.cos(aMid), seatH, cornerZ + R * Math.sin(aMid));
        chMesh.rotation.y = -aMid + Math.PI / 2;
        backGroup.add(chMesh);
      }}
    }}
  }} else {{
    // Square cleanly mitered corners
    layoutLinearChannels(mainLen, x0, 0, 1, 0, backGroup);
    layoutLinearChannels(leftLen, x0, -leftLen, 0, 1, backGroup);
    layoutLinearChannels(rightLen, x1, 0, 0, -1, backGroup);
  }}

}} else {{
  // Straight / generic bench layout
  const len = segDict["main"] || SPEC.footprint?.overall_width_in || 72.0;
  const x0 = -len / 2;
  
  // Base
  const bMesh = new THREE.Mesh(new THREE.BoxGeometry(len, baseH, totalSeatDepth - 2), M.base);
  bMesh.position.set(0, baseH / 2, -(totalSeatDepth - 2) / 2);
  baseGroup.add(bMesh);
  
  // Cushion
  const cMesh = new THREE.Mesh(new THREE.BoxGeometry(len, cushThk, totalSeatDepth + seatOverhang), M.cushion);
  cMesh.position.set(0, baseH + cushThk / 2, -(totalSeatDepth + seatOverhang) / 2 + backThk);
  cushionGroup.add(cMesh);
  
  // Back channels
  const chWidth = SPEC.back?.channel_width_in || 12.0;
  const nFull = Math.floor(len / chWidth);
  const rem = len - nFull * chWidth;
  const endTrim = rem > 0.001 ? rem / 2.0 : 0.0;
  const widths = [];
  if (endTrim > 0) widths.push(endTrim);
  for (let i = 0; i < nFull; i++) widths.push(chWidth);
  if (endTrim > 0) widths.push(endTrim);
  
  let curX = x0;
  for (const w of widths) {{
    const ch = createChannelMesh(w, netBackH, backThk);
    ch.position.set(curX, seatH, 0);
    backGroup.add(ch);
    curX += w;
  }}
}}

/* Camera Navigation & Controls (matching Willard viewer) */
const target = new THREE.Vector3(0, totalH * 0.45, -30);
let az = 0.65, el = 0.32, dist = Math.max(160, (SPEC.footprint?.overall_width_in || 260) * 0.95);
let drag = false, px = 0, py = 0;

function applyCam() {{
  cam.position.set(
    target.x + dist * Math.cos(el) * Math.sin(az),
    target.y + dist * Math.sin(el),
    target.z + dist * Math.cos(el) * Math.cos(az)
  );
  cam.lookAt(target);
}}
applyCam();

addEventListener('pointerdown', e => {{
  if (e.target.tagName === 'BUTTON') return;
  drag = true; px = e.clientX; py = e.clientY;
}});
addEventListener('pointerup', () => drag = false);
addEventListener('pointermove', e => {{
  if (!drag) return;
  az -= (e.clientX - px) * 0.006;
  el = Math.min(1.4, Math.max(-0.15, el + (e.clientY - py) * 0.005));
  px = e.clientX; py = e.clientY;
  applyCam();
}});
addEventListener('wheel', e => {{
  dist = Math.min(600, Math.max(40, dist + e.deltaY * 0.25));
  applyCam();
}}, {{passive: true}});

function fly(a, e2, d) {{
  az = a; el = e2; dist = d; applyCam();
}}

document.getElementById('bFront').onclick = () => fly(0.0, 0.20, dist);
document.getElementById('bIso').onclick   = () => fly(0.65, 0.38, dist);
document.getElementById('bTop').onclick   = () => fly(0.0, 1.45, dist * 0.9);
document.getElementById('bRear').onclick  = () => fly(Math.PI, 0.25, dist);

const bBase = document.getElementById('bBase');
bBase.onclick = () => {{
  baseGroup.visible = !baseGroup.visible;
  bBase.classList.toggle('on', baseGroup.visible);
  bBase.textContent = baseGroup.visible ? "Show Base" : "Hide Base";
}};

addEventListener('resize', () => {{
  cam.aspect = innerWidth / innerHeight;
  cam.updateProjectionMatrix();
  ren.setSize(innerWidth, innerHeight);
}});

(function loop() {{
  requestAnimationFrame(loop);
  if (!drag) {{
    az += 0.0008;
    applyCam();
  }}
  ren.render(scene, cam);
}})();
</script>
</body>
</html>"""
    return html


# ── 3D View Projection Still Stills (Isometric & Orthographic) ──────────

def _iso_project(x: float, y: float, z: float, ox: float, oy: float, s: float) -> Tuple[float, float]:
    """Isometric projection (30 deg): x=width, y=depth, z=height."""
    cos30 = 0.866025
    sin30 = 0.5
    return (
        ox + (x * cos30 - y * cos30) * s,
        oy + z * s - (x * sin30 + y * sin30) * s * 0.6,
    )


def _render_3d_still_sheet(
    spec: PieceSpec,
    output_pdf: str,
    view_type: str = "iso",
) -> None:
    """Render high-resolution 3D perspective / isometric projection still to PDF."""
    W, H = landscape(letter)
    c = canvas.Canvas(output_pdf, pagesize=landscape(letter))
    c.setTitle(f"{spec.name} 3D Still — {view_type.upper()}")

    # Background
    paper = HexColor("#EFECE3")
    c.setFillColor(paper)
    c.rect(0, 0, W, H, stroke=0, fill=1)

    company = "WOODCRAFT BY EMPIRE" if spec.business_unit == "woodcraft" else "EMPIRE WORKROOM"
    tagline = "CUSTOM CNC & ARCHITECTURAL MILLWORK" if spec.business_unit == "woodcraft" else "PARAMETRIC 3D MODEL RENDER"

    # Top band
    ink = HexColor("#1C1917")
    gold = HexColor("#C9A13B")
    white = HexColor("#FFFFFF")
    c.setFillColor(ink)
    c.rect(0, H - 46, W, 46, stroke=0, fill=1)

    c.setFillColor(white)
    c.setFont("Times-Bold", 16)
    c.drawString(24, H - 30, company)

    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(240, H - 18, tagline)
    c.setFillColor(HexColor("#DDDDDD"))
    c.setFont("Helvetica", 6.8)
    c.drawString(240, H - 29, "5124 Frolich Ln, Hyattsville, MD 20781")
    c.drawString(240, H - 39, "(703) 213-6484 · workroom.empirebox.store")

    client_str = f"CLIENT: {spec.client_name}"
    if spec.client_address:
        client_str += f" · {spec.client_address}"
    c.setFillColor(HexColor("#C0B298"))
    c.setFont("Helvetica-Bold", 7.0)
    c.drawRightString(W - 24, H - 12, client_str)

    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(W - 24, H - 24, f"3D STILL · {view_type.upper()}")
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(W - 24, H - 36, f"{spec.quote_number} · {spec.status}")

    # Title
    c.setFillColor(ink)
    c.setFont("Times-Bold", 14)
    c.drawString(24, H - 68, f"{spec.name.upper()} — 3D {view_type.upper()} STILL")
    c.setFillColor(HexColor("#6B5A44"))
    c.setFont("Times-Italic", 8.5)
    c.drawString(24, H - 80, "True parametric geometry modeled from construction specification")

    # Geometry Setup
    back_c = HexColor(spec.material.color_hex or "#9A5B2E")
    seat_c = HexColor(spec.material.seat_color_hex or "#A8693A")
    base_c = HexColor("#2B2622")
    seam_c = HexColor(spec.material.seam_color_hex or "#5E3518")
    shade_c = Color(back_c.red * 0.78, back_c.green * 0.78, back_c.blue * 0.78)

    seg_dict = {s.name.lower(): s.length_in for s in spec.footprint.segments}
    m_len = seg_dict.get("main", 249.75)
    l_len = seg_dict.get("left", 37.75)
    r_len = seg_dict.get("right", 48.5)
    d = spec.cushion.seat_depth_in
    cush_thk = spec.cushion.cushion_thickness_in
    seat_h = spec.cushion.seat_height_in
    base_h = seat_h - cush_thk
    net_back_h = spec.back.net_back_height_in
    tot_h = seat_h + net_back_h

    # Scale and center
    s = 1.75
    ox = W / 2
    oy = H * 0.42

    if view_type == "iso":
        # Draw base
        # Main base
        def p3(x, y, z):
            return _iso_project(x, y, z, ox, oy, s)

        # Draw Base Platform
        c.setFillColor(base_c)
        c.setStrokeColor(ink)
        c.setLineWidth(0.8)
        
        # Left base return
        pts_bl = [p3(-m_len / 2, 0, 0), p3(-m_len / 2 + d, 0, 0), p3(-m_len / 2 + d, l_len, 0), p3(-m_len / 2, l_len, 0)]
        p = c.beginPath()
        p.moveTo(*pts_bl[0])
        for pt in pts_bl[1:]: p.lineTo(*pt)
        p.close()
        c.drawPath(p, fill=1, stroke=1)

        # Main base front
        pts_bm = [p3(-m_len / 2 + d, 0, 0), p3(m_len / 2 - d, 0, 0), p3(m_len / 2 - d, 0, base_h), p3(-m_len / 2 + d, 0, base_h)]
        p = c.beginPath()
        p.moveTo(*pts_bm[0])
        for pt in pts_bm[1:]: p.lineTo(*pt)
        p.close()
        c.drawPath(p, fill=1, stroke=1)

        # Draw Seat Cushions
        c.setFillColor(seat_c)
        c.setStrokeColor(seam_c)
        c.setLineWidth(1.0)
        
        # Main cushion top
        pts_cm = [
            p3(-m_len / 2 + d, 0, seat_h),
            p3(m_len / 2 - d, 0, seat_h),
            p3(m_len / 2 - d, d, seat_h),
            p3(-m_len / 2 + d, d, seat_h),
        ]
        p = c.beginPath()
        p.moveTo(*pts_cm[0])
        for pt in pts_cm[1:]: p.lineTo(*pt)
        p.close()
        c.drawPath(p, fill=1, stroke=1)

        # Left return cushion top
        pts_cl = [
            p3(-m_len / 2, 0, seat_h),
            p3(-m_len / 2 + d, 0, seat_h),
            p3(-m_len / 2 + d, l_len, seat_h),
            p3(-m_len / 2, l_len, seat_h),
        ]
        p = c.beginPath()
        p.moveTo(*pts_cl[0])
        for pt in pts_cl[1:]: p.lineTo(*pt)
        p.close()
        c.drawPath(p, fill=1, stroke=1)

        # Right return cushion top
        pts_cr = [
            p3(m_len / 2 - d, 0, seat_h),
            p3(m_len / 2, 0, seat_h),
            p3(m_len / 2, r_len, seat_h),
            p3(m_len / 2 - d, r_len, seat_h),
        ]
        p = c.beginPath()
        p.moveTo(*pts_cr[0])
        for pt in pts_cr[1:]: p.lineTo(*pt)
        p.close()
        c.drawPath(p, fill=1, stroke=1)

        # Draw Channels across Main Back
        ch_w = spec.back.channel_width_in
        ch_widths, end_trim = compute_channels(m_len, ch_w)
        cur_x = -m_len / 2
        for w_i in ch_widths:
            # Channel face
            c.setFillColor(back_c)
            c.setStrokeColor(seam_c)
            c.setLineWidth(0.8)
            
            pts_ch = [
                p3(cur_x, 0, seat_h),
                p3(cur_x + w_i, 0, seat_h),
                p3(cur_x + w_i, 0, tot_h),
                p3(cur_x, 0, tot_h),
            ]
            p = c.beginPath()
            p.moveTo(*pts_ch[0])
            for pt in pts_ch[1:]: p.lineTo(*pt)
            p.close()
            c.drawPath(p, fill=1, stroke=1)

            # Curved highlight seam line
            c.setStrokeColor(Color(1, 1, 1, 0.25))
            c.setLineWidth(1.0)
            pt_m1 = p3(cur_x + w_i / 2, 0, seat_h + 1)
            pt_m2 = p3(cur_x + w_i / 2, 0, tot_h - 1)
            c.line(pt_m1[0], pt_m1[1], pt_m2[0], pt_m2[1])

            cur_x += w_i

        # Left return channels
        l_widths, l_end = compute_channels(l_len, ch_w)
        cur_y = 0
        for w_i in l_widths:
            c.setFillColor(shade_c)
            c.setStrokeColor(seam_c)
            c.setLineWidth(0.8)
            pts_l = [
                p3(-m_len / 2, cur_y, seat_h),
                p3(-m_len / 2, cur_y + w_i, seat_h),
                p3(-m_len / 2, cur_y + w_i, tot_h),
                p3(-m_len / 2, cur_y, tot_h),
            ]
            p = c.beginPath()
            p.moveTo(*pts_l[0])
            for pt in pts_l[1:]: p.lineTo(*pt)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
            cur_y += w_i

    elif view_type == "front":
        # Front elevation 3D projection
        s_front = 2.7
        bx = (W - m_len * s_front) / 2
        by = H * 0.25
        
        # Base platform
        c.setFillColor(base_c)
        c.rect(bx, by, m_len * s_front, base_h * s_front, fill=1, stroke=1)
        
        # Cushion
        c.setFillColor(seat_c)
        c.rect(bx, by + base_h * s_front, m_len * s_front, cush_thk * s_front, fill=1, stroke=1)
        
        # Back Channels
        ch_widths, end_trim = compute_channels(m_len, spec.back.channel_width_in)
        cx = bx
        for w_i in ch_widths:
            c.setFillColor(back_c)
            c.setStrokeColor(seam_c)
            c.rect(cx, by + seat_h * s_front, w_i * s_front, net_back_h * s_front, fill=1, stroke=1)
            # Channel center soft seam highlight
            c.setStrokeColor(Color(1, 1, 1, 0.2))
            c.line(cx + (w_i * s_front) / 2, by + seat_h * s_front + 2, cx + (w_i * s_front) / 2, by + tot_h * s_front - 2)
            cx += w_i * s_front

    elif view_type == "top":
        # Top plan projection
        s_top = 2.6
        bx = (W - m_len * s_top) / 2
        by = H * 0.62
        
        # Back wall line & back band
        c.setFillColor(back_c)
        c.rect(bx, by - 3 * s_top, m_len * s_top, 3 * s_top, fill=1, stroke=1)
        # Left back
        c.rect(bx, by - l_len * s_top, 3 * s_top, l_len * s_top, fill=1, stroke=1)
        # Right back
        c.rect(bx + m_len * s_top - 3 * s_top, by - r_len * s_top, 3 * s_top, r_len * s_top, fill=1, stroke=1)

        # Cushions
        c.setFillColor(seat_c)
        c.rect(bx + 3 * s_top, by - d * s_top, (m_len - 6) * s_top, (d - 3) * s_top, fill=1, stroke=1)
        c.rect(bx + 3 * s_top, by - l_len * s_top, (d - 3) * s_top, (l_len - d) * s_top, fill=1, stroke=1)
        c.rect(bx + (m_len - d) * s_top, by - r_len * s_top, (d - 3) * s_top, (r_len - d) * s_top, fill=1, stroke=1)

    elif view_type == "rear":
        # Rear projection
        s_rear = 2.7
        bx = (W - m_len * s_rear) / 2
        by = H * 0.25
        c.setFillColor(shade_c)
        c.rect(bx, by, m_len * s_rear, tot_h * s_rear, fill=1, stroke=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(W / 2, by + tot_h * s_rear / 2, "CLOSED REAR WALL FACE (SOLID)")

    # Bottom footer band
    c.setFillColor(ink)
    c.rect(0, 0, W, 24, stroke=0, fill=1)
    c.setFillColor(HexColor("#BBBBBB"))
    c.setFont("Helvetica", 7)
    c.drawString(24, 9, f"{company} · 5124 Frolich Ln, Hyattsville, MD 20781 · drawn from quoted dimensions")
    c.drawRightString(W - 24, 9, f"3D STILL · {view_type.upper()} · 2026-10-08 · NOT SENT")

    c.showPage()
    c.save()


def export_spec_to_glb(spec: PieceSpec, output_glb_path: str) -> str:
    """Generate minimal valid standard GLB binary containing bounding box meshes."""
    # Build standard GLB file header + JSON chunk + Binary buffer
    # Header: 12 bytes [magic (0x46546C67), version (2), length]
    json_obj = {
        "asset": {"version": "2.0", "generator": "Empire 3D Parametric Engine"},
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": spec.name, "mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": 8,
                "type": "VEC3",
                "max": [spec.footprint.overall_width_in or 100, spec.cushion.seat_height_in + spec.back.net_back_height_in, 30],
                "min": [0, 0, 0]
            }
        ],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 96, "target": 34962}],
        "buffers": [{"byteLength": 96}]
    }
    
    json_str = json.dumps(json_obj)
    while len(json_str) % 4 != 0:
        json_str += " "
        
    json_bytes = json_str.encode("utf-8")
    
    # 8 corner vertices (3 floats each = 24 floats = 96 bytes)
    w = float(spec.footprint.overall_width_in or 100)
    h = float(spec.cushion.seat_height_in + spec.back.net_back_height_in)
    d = float(spec.cushion.seat_depth_in or 30)
    raw_verts = [
        0.0, 0.0, 0.0,
        w, 0.0, 0.0,
        w, h, 0.0,
        0.0, h, 0.0,
        0.0, 0.0, d,
        w, 0.0, d,
        w, h, d,
        0.0, h, d,
    ]
    bin_bytes = struct.pack(f"{len(raw_verts)}f", *raw_verts)
    
    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    
    with open(output_glb_path, "wb") as f:
        # GLB Header
        f.write(struct.pack("<4sII", b"glTF", 2, total_len))
        # Chunk 0 (JSON)
        f.write(struct.pack("<II4s", len(json_bytes), 0x4E4F534A, b"JSON"))
        f.write(json_bytes)
        # Chunk 1 (BIN)
        f.write(struct.pack("<II4s", len(bin_bytes), 0x004E4942, b"BIN\x00"))
        f.write(bin_bytes)
        
    return output_glb_path


def render_3d(
    spec: PieceSpec,
    output_dir: str,
    prefix: str = "model_3d",
    export_glb: bool = True,
) -> Dict[str, Any]:
    """Complete 3D rendering pipeline for a PieceSpec.

    Returns:
    - html_path: Self-contained live Three.js viewer HTML
    - stills: List of 4 rendered PNG image paths (iso, front, top, rear)
    - glb_path: Optional binary GLB model file path
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Generate live HTML viewer
    html_content = build_viewer_html(spec)
    html_filename = f"{prefix}_viewer.html"
    html_path = str(out_path / html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 2. Render 4 Headless 3D Projection Stills (iso, front, top, rear)
    views = ["iso", "front", "top", "rear"]
    still_pngs = []
    
    for v in views:
        pdf_still = str(out_path / f"{prefix}_{v}.pdf")
        png_prefix = str(out_path / f"{prefix}_{v}")
        _render_3d_still_sheet(spec, pdf_still, view_type=v)
        pngs = render_pdf_to_png_previews(pdf_still, png_prefix)
        if pngs:
            # Rename first page preview to clean name
            target_png = str(out_path / f"{prefix}_{v}.png")
            if os.path.exists(pngs[0]):
                os.replace(pngs[0], target_png)
                still_pngs.append(target_png)
                # Cleanup single-use PDF
                if os.path.exists(pdf_still):
                    os.remove(pdf_still)

    # 3. Optional GLB export
    glb_path = None
    if export_glb:
        glb_filename = f"{prefix}.glb"
        glb_path = str(out_path / glb_filename)
        export_spec_to_glb(spec, glb_path)

    return {
        "html_path": html_path,
        "html_filename": html_filename,
        "stills": still_pngs,
        "still_filenames": [os.path.basename(p) for p in still_pngs],
        "glb_path": glb_path,
        "glb_filename": os.path.basename(glb_path) if glb_path else None,
    }
