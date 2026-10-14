/* Empire Workroom 3D Job Viewer runtime. Expects global THREE + DATA. */
(function () {
  const D = window.DATA;
  if (!D || !D.parts) throw new Error('viewer DATA missing');

  const TILE = D.tileInches || 6;
  const LAY = D.layers || [];
  const H = new URLSearchParams(location.hash.slice(1));
  const vis = {};
  LAY.forEach(function (l) { vis['l:' + l[0]] = true; });
  (D.groups || []).forEach(function (g) { vis['g:' + g[0]] = true; });
  (D.runs || []).forEach(function (r) { vis['r:' + r[0]] = true; });

  function mk(id, arr, pre) {
    const box = document.getElementById(id);
    if (!box) return;
    arr.forEach(function (a) {
      const d = document.createElement('label');
      d.className = 'row';
      const sw = a[2] && String(a[2])[0] === '#' ? '<span class="sw" style="background:' + a[2] + '"></span>' : '';
      d.innerHTML = '<input type="checkbox" checked data-k="' + pre + a[0] + '">' + sw + a[1];
      box.appendChild(d);
    });
  }
  mk('grps', D.groups || [], 'g:');
  mk('runs', D.runs || [], 'r:');
  mk('layers', LAY, 'l:');

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf1ece1);
  const cam = new THREE.PerspectiveCamera(30, innerWidth / innerHeight, 1, 8000);
  let ren;
  try {
    ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  } catch (err) {
    document.body.insertAdjacentHTML('beforeend',
      '<div style="position:fixed;left:290px;top:60px;right:20px;padding:16px;background:#fff;border:2px solid #b02020;font-size:15px"><b>3D could not start in this browser.</b><br>This viewer needs WebGL. Open the file in Chrome, Edge, Firefox or Safari.<br><small>' + err.message + '</small></div>');
    throw err;
  }
  ren.outputEncoding = THREE.sRGBEncoding;
  ren.toneMapping = THREE.NoToneMapping;
  ren.toneMappingExposure = 1;
  ren.setPixelRatio(Math.min(devicePixelRatio || 1, 3));
  ren.shadowMap.enabled = true;
  ren.shadowMap.type = THREE.PCFSoftShadowMap;
  ren.setSize(innerWidth, innerHeight);
  ren.localClippingEnabled = true;
  document.body.appendChild(ren.domElement);

  scene.add(new THREE.AmbientLight(0xfff6e6, 0.7));
  scene.add(new THREE.HemisphereLight(0xfff6e6, 0x8a7a5a, 0.85));
  const dl = new THREE.DirectionalLight(0xffffff, 0.75);
  dl.position.set(80, 280, 220);
  dl.castShadow = true;
  dl.shadow.mapSize.set(2048, 2048);
  dl.shadow.radius = 4;
  dl.shadow.bias = -0.0004;
  Object.assign(dl.shadow.camera, { left: -400, right: 400, top: 400, bottom: -400, near: 10, far: 1600 });
  dl.shadow.camera.updateProjectionMatrix();
  scene.add(dl);
  const home = (D.views && D.views.all && D.views.all.tgt) || [80, 0, 30];
  const fl = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), new THREE.ShadowMaterial({ opacity: 0.22 }));
  fl.rotation.x = -Math.PI / 2;
  fl.position.set(home[0], -0.01, home[2]);
  fl.receiveShadow = true;
  scene.add(fl);
  dl.target.position.set(home[0], 0, home[2]);
  scene.add(dl.target);
  scene.add(new THREE.DirectionalLight(0xffffff, 0.3)).position.set(200, 80, -160);

  function mkWeave() {
    const S = 512, C = 8, P = S / C;
    const I = new Float32Array(S * S), T = new Float32Array(S * S);
    const hsh = function (i, j) { const h = Math.sin(i * 127.1 + j * 311.7) * 43758.5453; return h - Math.floor(h); };
    const nz = new Float32Array(256 * 256);
    for (let i = 0; i < nz.length; i++) nz[i] = Math.random();
    const gn = function (x, y) { return nz[((y & 255) << 8) | (x & 255)]; };
    for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
      const A = (x + y) / P, B = (x - y + S) / P;
      const ia = Math.floor(A), ib = Math.floor(B);
      let fa = A - ia, fb = B - ib;
      const m4 = (((ia + ib) % 4) + 4) % 4, warp = m4 < 2, kk = warp ? m4 : m4 - 2;
      let u = (kk + (warp ? fa : fb)) / 2, v = warp ? fb : fa;
      u = (u + 0.07 * Math.sin(Math.PI * v) + 1) % 1;
      const ex = Math.min(u, 1 - u), ev = Math.min(v, 1 - v);
      const gv = Math.min(1, ev / 0.06), gu = Math.min(1, ex / 0.04);
      const pill = Math.pow(Math.sin(Math.PI * v), 0.3) * Math.pow(Math.sin(Math.PI * u), 0.15);
      const h = pill * Math.pow(gv, 0.7) * Math.pow(gu, 0.7);
      const ridge = ((ev < 0.09 && ev > 0.05) || (ex < 0.06 && ex > 0.035)) ? 0.1 : 0;
      const cv = 0.92 + 0.08 * hsh(((ia % (2 * C)) + 2 * C) % (2 * C), ((ib % (2 * C)) + 2 * C) % (2 * C));
      const grain = 0.9 + 0.1 * (gn(x >> 1, y >> 1) * 0.5 + gn(x >> 2, y >> 2) * 0.3 + gn(x >> 4, y >> 4) * 0.2);
      const k = y * S + x;
      T[k] = h;
      I[k] = (0.62 + 0.38 * h + ridge) * cv * grain * (0.9 + 0.1 * v);
    }
    function mkTex(arr) {
      const c = document.createElement('canvas'); c.width = c.height = S;
      const g = c.getContext('2d'), id = g.createImageData(S, S);
      for (let i = 0; i < S * S; i++) {
        const q = Math.max(0, Math.min(255, 255 * arr[i]));
        id.data[4 * i] = id.data[4 * i + 1] = id.data[4 * i + 2] = q; id.data[4 * i + 3] = 255;
      }
      g.putImageData(id, 0, 0);
      const t = new THREE.CanvasTexture(c);
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.minFilter = THREE.LinearMipmapLinearFilter;
      if (ren.capabilities) t.anisotropy = ren.capabilities.getMaxAnisotropy();
      return t;
    }
    return [mkTex(T), mkTex(I.map(function (v) { return Math.min(1, v * 1.12); }))];
  }
  const weaves = mkWeave();
  const tex = weaves[0], texC = weaves[1];
  tex.repeat.set(1, 1); texC.repeat.set(1, 1);
  texC.encoding = THREE.sRGBEncoding; texC.needsUpdate = true;

  const fabrics = D.fabrics || [];
  function fabHex(id) {
    for (let i = 0; i < fabrics.length; i++) if (fabrics[i].id === id || fabrics[i].code === id) return fabrics[i].hex;
    return 0x8b4a1f;
  }
  function fillSelect(el, selected) {
    if (!el) return;
    el.innerHTML = '';
    fabrics.forEach(function (f) {
      const o = document.createElement('option');
      o.value = f.id; o.textContent = f.code;
      el.appendChild(o);
    });
    if (selected) el.value = selected;
  }
  let colB = H.get('backs') || D.defaultBack || (fabrics[0] && fabrics[0].id);
  let colS = H.get('seats') || D.defaultSeat || colB;
  fillSelect(document.getElementById('cB'), colB);
  fillSelect(document.getElementById('cS'), colS);

  const fabB = new THREE.MeshLambertMaterial({ map: texC, side: THREE.DoubleSide });
  const fabS = fabB.clone();

  function fr(x) {
    const s = x < 0 ? '-' : '';
    x = Math.abs(x);
    let w = Math.floor(x + 1e-6), f = Math.round((x - w) * 16);
    if (f === 16) { w++; f = 0; }
    if (!f) return s + w + '"';
    let d = 16;
    while (f % 2 === 0) { f /= 2; d /= 2; }
    return s + (w ? w + ' ' : '') + f + '/' + d + '"';
  }

  function smoothN(g) {
    g.computeVertexNormals();
    const P = g.attributes.position, N = g.attributes.normal, M = new Map();
    const k = function (i) { return Math.round(P.getX(i) * 500) + '_' + Math.round(P.getY(i) * 500) + '_' + Math.round(P.getZ(i) * 500); };
    for (let i = 0; i < P.count; i++) {
      const K = k(i); let a = M.get(K); if (!a) { a = [0, 0, 0]; M.set(K, a); }
      a[0] += N.getX(i); a[1] += N.getY(i); a[2] += N.getZ(i);
    }
    for (let i = 0; i < P.count; i++) {
      const a = M.get(k(i)), L = Math.hypot(a[0], a[1], a[2]) || 1;
      N.setXYZ(i, a[0] / L, a[1] / L, a[2] / L);
    }
    N.needsUpdate = true;
    return g;
  }

  function pillowGeo(q, lay) {
    const fab = lay === 'back_fabric';
    const y0 = fab ? -0.52 : 0;
    const w = q.w + (fab ? 0.02 : -0.06);
    const h = w / 2, sh = q.sh || 0, r = Math.min(1.75, h * 0.4), Dep = 1.25 + sh, C = 0.7;
    const height = q.h || 26.75;
    const s = new THREE.Shape();
    s.moveTo(-h, y0); s.lineTo(h, y0); s.lineTo(h, Dep - r - 0.6);
    s.bezierCurveTo(h, Dep - 0.1, h - r * 0.4, Dep + 0.15, h - r, Dep + 0.2);
    s.quadraticCurveTo(0, Dep + 0.2 + C * 2, -(h - r), Dep + 0.2);
    s.bezierCurveTo(-(h - r * 0.4), Dep + 0.15, -h, Dep - 0.1, -h, Dep - r - 0.6);
    s.lineTo(-h, y0);
    const g = new THREE.ExtrudeGeometry(s, { depth: height, bevelEnabled: true, bevelThickness: 0.75, bevelSize: 0.55, bevelSegments: 8, curveSegments: 24, steps: 1 });
    g.translate(0, 0, 0.5);
    g.scale(1, 1, height / (height + 1));
    const uv = g.attributes.uv, ps = g.attributes.position;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, ps.getX(i) / TILE, ps.getZ(i) / TILE);
    const up = new THREE.Vector3(0, 1, 0);
    const d = new THREE.Vector3((q.d && q.d[0]) || 0, 0, (q.d && q.d[2]) || 1);
    const n = new THREE.Vector3((q.nn && q.nn[0]) || 1, 0, (q.nn && q.nn[2]) || 0);
    if (d.lengthSq() < 1e-6) d.set(0, 0, 1);
    if (n.lengthSq() < 1e-6) n.set(1, 0, 0);
    d.normalize(); n.normalize();
    const M = new THREE.Matrix4().makeBasis(d, n, up);
    M.setPosition(q.c[0], q.c[1], q.c[2]);
    g.applyMatrix4(M);
    return smoothN(g);
  }

  function uvBox(g, sx, sy, sz) {
    const uv = g.attributes.uv, n = g.attributes.normal;
    for (let i = 0; i < uv.count; i++) {
      const nx = Math.abs(n.getX(i)), ny = Math.abs(n.getY(i));
      let a, b;
      if (nx > 0.5) { a = sz; b = sy; } else if (ny > 0.5) { a = sx; b = sz; } else { a = sx; b = sy; }
      uv.setXY(i, uv.getX(i) * a / TILE, uv.getY(i) * b / TILE);
    }
    uv.needsUpdate = true;
  }

  function rBox(sx, sy, sz, r, crown) {
    r = Math.max(0.05, Math.min(r, Math.min(sx, sy, sz) / 2 - 0.02));
    const m = 8, K = crown ? 12 : 2, N = 2 * m + K, S = [sx, sy, sz];
    const g = new THREE.BoxGeometry(sx, sy, sz, N, N, N);
    const P = g.attributes.position, NR = g.attributes.normal, UV = g.attributes.uv;
    const v = [0, 0, 0], c = [0, 0, 0];
    for (let i = 0; i < P.count; i++) {
      for (let a = 0; a < 3; a++) {
        const half = S[a] / 2, idx = Math.round((P.array[i * 3 + a] + half) / S[a] * N);
        let x = idx <= m ? -half + r * (1 - Math.cos(idx / m * Math.PI / 2))
          : idx >= N - m ? half - r * (1 - Math.cos((N - idx) / m * Math.PI / 2))
          : -half + r + (half - r) * 2 * (idx - m) / K;
        v[a] = x;
        c[a] = Math.max(-half + r, Math.min(half - r, x));
      }
      let dlt = [v[0] - c[0], v[1] - c[1], v[2] - c[2]], L = Math.hypot(dlt[0], dlt[1], dlt[2]), n;
      if (L > 1e-6) { n = dlt.map(function (e) { return e / L; }); for (let a = 0; a < 3; a++) v[a] = c[a] + n[a] * r; }
      else n = [NR.getX(i), NR.getY(i), NR.getZ(i)];
      if (crown && v[1] > 0) {
        const fx = 1 - Math.pow(v[0] / (sx / 2), 2), fz = 1 - Math.pow(v[2] / (sz / 2), 2);
        v[1] += crown * Math.max(0, fx) * Math.max(0, fz) * (v[1] / (sy / 2));
      }
      P.setXYZ(i, v[0], v[1], v[2]);
      const ax = [Math.abs(n[0]), Math.abs(n[1]), Math.abs(n[2])];
      let uu, vv;
      if (ax[0] >= ax[1] && ax[0] >= ax[2]) { uu = v[2]; vv = v[1]; }
      else if (ax[1] >= ax[2]) { uu = v[0]; vv = v[2]; }
      else { uu = v[0]; vv = v[1]; }
      UV.setXY(i, uu / TILE, vv / TILE);
    }
    return smoothN(g);
  }

  const objs = [];
  D.parts.forEach(function (p) {
    let g, sx, sy, sz;
    try {
    if (p.pillow) {
      g = pillowGeo(p.pillow, p.l);
      p.min = [0, 0, 0];
      p.max = [0, 0, 0];
    } else {
      sx = p.max[0] - p.min[0]; sy = p.max[1] - p.min[1]; sz = p.max[2] - p.min[2];
      const fab = p.l.indexOf('fabric') >= 0;
      const seat = p.l.indexOf('seat') >= 0;
      const r = fab ? (seat ? 0.55 : 0.35) : (p.l === 'base' ? 0.08 : 0.12);
      const crown = fab && seat ? 0.28 : 0;
      g = rBox(Math.max(sx, 0.08), Math.max(sy, 0.08), Math.max(sz, 0.08), r, crown);
    }
    let mat;
    if (p.l === 'back_fabric') mat = fabB;
    else if (p.l === 'seat_fabric') mat = fabS;
    else {
      const row = LAY.find(function (l) { return l[0] === p.l; });
      const hex = row && row[2] ? parseInt(String(row[2]).replace('#', ''), 16) : 0xc4b48a;
      if (!p.pillow) uvBox(g, sx || 1, sy || 1, sz || 1);
      mat = new THREE.MeshLambertMaterial({
        color: new THREE.Color(hex),
        side: THREE.DoubleSide,
      });
    }
    const m = new THREE.Mesh(g, mat);
    m.userData = p;
    m.castShadow = m.receiveShadow = true;
    p.off = new THREE.Vector3();
    p.key = String(p.n).split(' ')[0] + (p.l === 'base' ? '_base' : '');
    p.c = new THREE.Vector3((p.min[0] + p.max[0]) / 2, (p.min[1] + p.max[1]) / 2, (p.min[2] + p.max[2]) / 2);
    p.locked = p.l === 'base' || p.locked;
    m.add(new THREE.LineSegments(
      new THREE.EdgesGeometry(g, 40),
      new THREE.LineBasicMaterial({ color: 0x3a2c1c, transparent: true, opacity: p.l.indexOf('fabric') >= 0 ? 0 : 0.55, visible: p.l.indexOf('fabric') < 0 })
    ));
    scene.add(m);
    objs.push(m);
    } catch (err) { console.warn('viewer part skipped', p && p.n, err); }
  });

  const rotK = {}, piv = {};
  objs.forEach(function (o) {
    const p = o.userData;
    o.geometry.computeBoundingBox();
    const b = o.geometry.boundingBox.clone();
    if (!p.pillow) b.translate(p.c);
    (piv[p.key] = piv[p.key] || new THREE.Box3()).union(b);
  });
  Object.keys(piv).forEach(function (k) { piv[k] = piv[k].getCenter(new THREE.Vector3()); });

  let ex = parseFloat(H.get('explode') || '0'), secOn = false, sel = null;
  const clip = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 100);

  function setCol() {
    fabB.color.setHex(fabHex(colB)).convertSRGBToLinear();
    fabS.color.setHex(fabHex(colS)).convertSRGBToLinear();
    const cB = document.getElementById('cB'), cS = document.getElementById('cS');
    if (cB) cB.value = colB;
    if (cS) cS.value = colS;
  }

  function refresh() {
    setCol();
    objs.forEach(function (o) {
      const p = o.userData;
      o.visible = vis['l:' + p.l] !== false && vis['g:' + p.g] !== false && vis['r:' + p.r] !== false && !p.hid;
      if ((p.l.endsWith('_ply') || p.l.endsWith('_foam')) && ex < 0.01 && !secOn && vis['l:' + p.k + '_fabric']) {
        const fb = objs.find(function (x) { return x.userData.key === p.key && x.userData.l === p.k + '_fabric'; });
        if (fb && fb.userData.off.distanceTo(p.off) < 1e-3 && !fb.userData.hid) o.visible = false;
      }
      const e = p.l === 'base' ? [0, 0, 0, 0] : (p.e || [0, 1, 0, 1]);
      o.position.set(p.c.x + e[0] * e[3] * 8 * ex, p.c.y + e[1] * e[3] * 7 * ex, p.c.z + e[2] * e[3] * 8 * ex);
      if (p.k === 'back') o.position.y += 14 * ex;
      const t = rotK[p.key] || 0, Pv = piv[p.key] || p.c;
      const dlt = o.position.clone().sub(Pv).applyAxisAngle(new THREE.Vector3(0, 1, 0), t);
      o.position.copy(Pv).add(dlt);
      o.rotation.y = t;
      o.position.add(p.off);
      const cp = secOn ? [clip] : [];
      o.material.clippingPlanes = cp;
      if (o.children[0] && o.children[0].material) o.children[0].material.clippingPlanes = cp;
      if (o.children[0] && o.children[0].material) {
        o.children[0].material.color.setHex(o === sel ? 0xff2020 : 0x3a2c1c);
        const hs = sel && o.userData.key === sel.userData.key;
        o.children[0].material.visible = hs || String(o.userData.l).indexOf('fabric') < 0;
        o.children[0].material.opacity = hs ? 0.9 : (String(o.userData.l).indexOf('fabric') >= 0 ? 0 : 0.55);
        if (hs) o.children[0].material.color.setHex(0xff2020);
      }
    });
    const exEl = document.getElementById('ex');
    if (exEl) exEl.value = ex;
    const info = document.getElementById('info');
    if (info) {
      const dim = sel ? ('<b>' + sel.userData.n + '</b><br>' + (sel.userData.dimsLabel || (fr(sel.userData.dims[0]) + ' long × ' + fr(sel.userData.dims[1]) + ' × ' + fr(sel.userData.dims[2]) + ' thick')) + '<br>') : 'Click a part to identify<br>';
      info.innerHTML = dim + 'Backs: ' + (colB || '') + ' · Seats: ' + (colS || '') + ' · Explode ' + Math.round(ex * 100) + '%';
    }
    draw();
  }

  document.querySelectorAll('#p input[type=checkbox]').forEach(function (i) {
    i.onchange = function () { vis[i.dataset.k] = i.checked; refresh(); };
  });
  const cB = document.getElementById('cB'), cS = document.getElementById('cS');
  if (cB) cB.onchange = function () { colB = cB.value; refresh(); };
  if (cS) cS.onchange = function () { colS = cS.value; refresh(); };
  const pSame = document.getElementById('pSame');
  if (pSame) pSame.onclick = function () { colS = colB; refresh(); };
  const exEl = document.getElementById('ex');
  if (exEl) exEl.oninput = function (e) { ex = +e.target.value; refresh(); };
  const bA = document.getElementById('bA'), bE = document.getElementById('bE');
  if (bA) bA.onclick = function () { ex = 0; refresh(); };
  if (bE) bE.onclick = function () { ex = 1; refresh(); };

  let tgt = new THREE.Vector3(), th = 0.55, ph = 0.45, dist = 400;
  function view(v) {
    secOn = false;
    const preset = (D.views || {})[v] || (D.views || {}).all;
    if (preset) {
      tgt.set(preset.tgt[0], preset.tgt[1], preset.tgt[2]);
      th = preset.th; ph = preset.ph; dist = preset.dist;
    }
    if (v === 'sec') { secOn = true; clip.constant = tgt.x; }
    refresh();
  }
  document.querySelectorAll('[data-v]').forEach(function (b) { b.onclick = function () { view(b.dataset.v); }; });

  function place() {
    cam.position.set(tgt.x + Math.sin(th) * Math.cos(ph) * dist, tgt.y + Math.sin(ph) * dist, tgt.z + Math.cos(th) * Math.cos(ph) * dist);
    cam.lookAt(tgt);
  }
  function draw() { place(); ren.render(scene, cam); }

  let drag = null, moved = 0;
  const cv = ren.domElement;
  cv.oncontextmenu = function (e) { e.preventDefault(); };
  const rc = new THREE.Raycaster(), mv = new THREE.Vector2(), tip = document.getElementById('tip'), ptrs = new Map();
  const mvOn = document.getElementById('mvOn');
  const mvAll = document.getElementById('mvAll');

  function hit(e) {
    const R = cv.getBoundingClientRect();
    mv.set((e.clientX - R.left) / R.width * 2 - 1, -(e.clientY - R.top) / R.height * 2 + 1);
    rc.setFromCamera(mv, cam);
    return rc.intersectObjects(objs.filter(function (o) { return o.visible; }), false)
      .filter(function (i) { return !secOn || clip.distanceToPoint(i.point) >= 0; })[0];
  }
  function members(o) {
    if (!o || o.userData.locked || o.userData.l === 'base') return [];
    return (mvAll && mvAll.checked) ? objs.filter(function (x) { return x.userData.key === o.userData.key; }) : [o];
  }
  function pick(e, click) {
    const h = hit(e);
    if (click) { sel = h ? h.object : null; refresh(); return; }
    if (h && tip) {
      const p = h.object.userData;
      tip.style.display = 'block';
      tip.style.left = (e.clientX + 12) + 'px';
      tip.style.top = (e.clientY + 12) + 'px';
      tip.textContent = p.n + ': ' + (p.dimsLabel || (fr(p.dims[0]) + ' × ' + fr(p.dims[1])));
    } else if (tip) tip.style.display = 'none';
  }
  function rayPt(e, plane) {
    const R = cv.getBoundingClientRect();
    mv.set((e.clientX - R.left) / R.width * 2 - 1, -(e.clientY - R.top) / R.height * 2 + 1);
    rc.setFromCamera(mv, cam);
    const v = new THREE.Vector3();
    return rc.ray.intersectPlane(plane, v);
  }
  function pd() { const a = Array.from(ptrs.values()); return Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y); }
  function pc() { const a = Array.from(ptrs.values()); return { x: (a[0].x + a[1].x) / 2, y: (a[0].y + a[1].y) / 2 }; }

  cv.addEventListener('pointerdown', function (e) {
    cv.setPointerCapture(e.pointerId);
    ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (tip) tip.style.display = 'none';
    if (ptrs.size === 2) { drag = { pinch: true, d: pd(), c: pc() }; return; }
    if (ptrs.size > 2) return;
    const h = (mvOn && mvOn.checked && e.button === 0 && !secOn) ? hit(e) : null;
    if (h && (h.object.userData.locked || h.object.userData.l === 'base')) { sel = h.object; refresh(); }
    if (h && !h.object.userData.locked && h.object.userData.l !== 'base') {
      sel = h.object;
      const lift = e.altKey, spin = e.shiftKey, n = new THREE.Vector3();
      if (lift) { cam.getWorldDirection(n); n.y = 0; n.normalize(); } else n.set(0, 1, 0);
      const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(n, h.point);
      const ms = members(h.object);
      drag = { piece: true, plane: plane, start: h.point.clone(), ms: ms, offs: ms.map(function (o) { return o.userData.off.clone(); }), lift: lift, spin: spin, r0: rotK[h.object.userData.key] || 0, sx: e.clientX, x: e.clientX, y: e.clientY };
      moved = 0; refresh(); cv.style.cursor = 'grabbing';
    } else {
      drag = { x: e.clientX, y: e.clientY, pan: e.button === 2 || e.shiftKey }; moved = 0;
    }
  });

  cv.addEventListener('pointermove', function (e) {
    if (ptrs.has(e.pointerId)) ptrs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (!drag) { if (e.pointerType === 'mouse') pick(e, false); return; }
    if (drag.pinch) {
      if (ptrs.size < 2) return;
      const d = pd(), c = pc();
      dist *= drag.d / d;
      const r = new THREE.Vector3().setFromMatrixColumn(cam.matrix, 0), u = new THREE.Vector3().setFromMatrixColumn(cam.matrix, 1);
      tgt.addScaledVector(r, -(c.x - drag.c.x) * dist / 900).addScaledVector(u, (c.y - drag.c.y) * dist / 900);
      drag.d = d; drag.c = c; draw(); return;
    }
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    moved += Math.abs(dx) + Math.abs(dy);
    drag.x = e.clientX; drag.y = e.clientY;
    if (drag.piece && drag.spin) { setRot(drag.ms, drag.r0 + (e.clientX - drag.sx) * 0.01); return; }
    if (drag.piece) {
      const p = rayPt(e, drag.plane); if (!p) return;
      const dlt = p.sub(drag.start);
      if (drag.lift) { dlt.x = dlt.z = 0; }
      drag.ms.forEach(function (o, i) { o.userData.off.copy(drag.offs[i]).add(dlt); });
      refresh(); return;
    }
    if (drag.pan) {
      const r = new THREE.Vector3().setFromMatrixColumn(cam.matrix, 0), u = new THREE.Vector3().setFromMatrixColumn(cam.matrix, 1);
      tgt.addScaledVector(r, -dx * dist / 900).addScaledVector(u, dy * dist / 900);
    } else {
      th -= dx * 0.008; ph = Math.max(-1.5, Math.min(1.56, ph + dy * 0.008));
    }
    draw();
  });

  function setRot(ms, t) {
    const ks = new Set(ms.map(function (o) { return o.userData.key; }));
    ks.forEach(function (k) { rotK[k] = t; });
    refresh();
  }
  function rotSel(d) { if (!sel) return; setRot(members(sel), (rotK[sel.userData.key] || 0) + d); }

  let anim = null;
  function goHome(ms, dur) {
    dur = dur || 450;
    const st = ms.map(function (o) { return { o: o, off: o.userData.off.clone(), r: rotK[o.userData.key] || 0 }; });
    const t0 = performance.now();
    anim = true;
    (function step() {
      const t = Math.min(1, (performance.now() - t0) / dur), k = 1 - Math.pow(1 - t, 3);
      st.forEach(function (q) { q.o.userData.off.copy(q.off).multiplyScalar(1 - k); rotK[q.o.userData.key] = q.r * (1 - k); });
      refresh();
      if (t < 1) requestAnimationFrame(step);
      else { st.forEach(function (q) { q.o.userData.off.set(0, 0, 0); delete rotK[q.o.userData.key]; }); anim = null; refresh(); }
    })();
  }

  function up(e) {
    ptrs.delete(e.pointerId);
    if (!drag) return;
    if (drag.piece) {
      const o = drag.ms[0];
      if (o && o.userData.off.length() < 3 && Math.abs(rotK[o.userData.key] || 0) < 0.2 && o.userData.off.length() > 0) goHome(drag.ms, 200);
    }
    if (drag.pinch) { drag = null; return; }
    if (moved < 4) {
      const now = performance.now();
      if (e.pointerType !== 'mouse' && window._lt && now - window._lt < 350) {
        const h = hit(e);
        if (h && !h.object.userData.locked && h.object.userData.l !== 'base') { sel = h.object; goHome(members(h.object)); }
      }
      window._lt = now;
    }
    if (!drag.piece && moved < 4) pick(e, true);
    drag = null; cv.style.cursor = '';
  }
  cv.addEventListener('pointerup', up);
  cv.addEventListener('pointercancel', up);
  cv.addEventListener('dblclick', function (e) {
    const h = hit(e);
    if (h && !h.object.userData.locked && h.object.userData.l !== 'base') { sel = h.object; goHome(members(h.object)); }
  });
  cv.onwheel = function (e) { e.preventDefault(); dist *= Math.exp(e.deltaY * 0.001); draw(); };

  addEventListener('keydown', function (e) {
    if ((e.target.tagName === 'INPUT' && e.target.type !== 'checkbox') || e.target.tagName === 'SELECT') return;
    const k = e.key.toLowerCase(), st = Math.PI / 12;
    if (k === 'q') rotSel(st);
    else if (k === 'e') rotSel(-st);
    else if (k === 'r') rotSel(Math.PI / 2);
    else if (k === 'escape') { sel = null; refresh(); }
  });
  const bRL = document.getElementById('bRL'), bRR = document.getElementById('bRR'), bR90 = document.getElementById('bR90');
  if (bRL) bRL.onclick = function () { rotSel(Math.PI / 12); };
  if (bRR) bRR.onclick = function () { rotSel(-Math.PI / 12); };
  if (bR90) bR90.onclick = function () { rotSel(Math.PI / 2); };
  const bHide = document.getElementById('bHide'), bShow = document.getElementById('bShow');
  if (bHide) bHide.onclick = function () { if (!sel) return; members(sel).forEach(function (o) { o.userData.hid = true; }); sel = null; refresh(); };
  if (bShow) bShow.onclick = function () { objs.forEach(function (o) { o.userData.hid = false; }); refresh(); };
  const bReset = document.getElementById('bReset'), bBack = document.getElementById('bBack');
  if (bReset) bReset.onclick = function () {
    objs.forEach(function (o) { o.userData.hid = false; });
    ex = 0; sel = null;
    goHome(objs.filter(function (o) { return !o.userData.locked && o.userData.l !== 'base'; }), 600);
  };
  if (bBack) bBack.onclick = function () { if (sel) goHome(members(sel)); };

  addEventListener('resize', function () {
    cam.aspect = innerWidth / innerHeight; cam.updateProjectionMatrix();
    ren.setSize(innerWidth, innerHeight); draw();
  });

  const viewBox = document.getElementById('views');
  if (viewBox && D.views) {
    const labels = { all: 'Overall', top: 'Top', front: 'Front', end: 'End', sec: 'Section' };
    Object.keys(D.views).forEach(function (k) {
      if (viewBox.querySelector('[data-v="' + k + '"]')) return;
      const b = document.createElement('button');
      b.dataset.v = k;
      b.textContent = labels[k] || k;
      b.onclick = function () { view(k); };
      viewBox.appendChild(b);
    });
  }

  view(H.get('view') || 'all');
  if (H.get('explode')) ex = +H.get('explode');
  refresh();
})();
