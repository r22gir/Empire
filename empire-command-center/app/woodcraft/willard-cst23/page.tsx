'use client';

import React, { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import {
  Layers,
  Sliders,
  FileText,
  Download,
  AlertCircle,
  CheckCircle2,
  Maximize2,
  RotateCw,
  Eye,
  ExternalLink,
  ChevronRight,
  Sun,
  Moon,
  Info,
  Box,
  Compass,
} from 'lucide-react';

// Fraction formatter (fractions only)
function formatFraction(val: number | null | undefined, maxDenom = 32): string {
  if (val == null || isNaN(val)) return '0"';
  if (Math.abs(val) < 1e-6) return '0"';
  const sign = val < 0 ? '-' : '';
  const absVal = Math.abs(val);
  const units = Math.round(absVal * maxDenom);
  const whole = Math.floor(units / maxDenom);
  const rem = units - whole * maxDenom;
  if (rem === 0) return `${sign}${whole}"`;
  const gcd = (a: number, b: number): number => (b ? gcd(b, a % b) : a);
  const g = gcd(rem, maxDenom);
  const n = rem / g;
  const d = maxDenom / g;
  if (whole > 0) return `${sign}${whole} ${n}/${d}"`;
  return `${sign}${n}/${d}"`;
}

interface OpenItem {
  id: string;
  title: string;
  status: string;
  current_spec: string;
  range: string;
  impact: string;
  rule_note: string;
}

const OPEN_ITEMS_STATIC: OpenItem[] = [
  {
    id: 'ITEM-1',
    title: 'Channel height range',
    status: 'OPEN',
    current_spec: 'Nominal 36" back channel height (above 17" seat = 53" overall crown height)',
    range: '24" to 38"',
    impact: 'Field wall conditions at The Willard Scotch Bar and the 82" overall cap require verifying clear height under sconces/moldings.',
    rule_note: 'Wood cut and foam cut are 1:1 true size; fabric cut adds 2" to 3" for top/bottom stapling.',
  },
  {
    id: 'ITEM-2',
    title: 'Empty R24 dado pocket',
    status: 'OPEN',
    current_spec: 'R24 circular dado pocket located in the base curved rib assembly',
    range: '24" radius pocket',
    impact: 'Resolve whether pocket is designated for wiring / LED under-bench light conduit chase, weight reduction, or alignment spline.',
    rule_note: 'Do not remove from CNC cut files until confirmed by lead fabricator.',
  },
  {
    id: 'ITEM-3',
    title: 'Foam/board thickness',
    status: 'OPEN',
    current_spec: 'Back channels: 1/2" or 3/4" Baltic birch board + 2" HR foam. Seat: 5" multi-density foam stack.',
    range: 'Back foam: 1" to 4" (nominal 2"). Seat foam: 2" to 6" (nominal 5"). Board: 1/2" vs 3/4".',
    impact: 'Affects inside seat depth clearance (26" radial) and back rake feel. Changing foam thickness changes fabric wrap dimensions.',
    rule_note: 'Foam cut = exact wood board cut size. Fabric cut = channel width + 2" to 3" for stapling wrap.',
  },
];

const SHEETS_STATIC = [
  {
    sheet_num: 1,
    title: 'Sheet 1 of 8: Base Plates & Bottom Rail Ribs',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'BP-01', name: 'Curved Base Bottom Plate (Left)', size: '44 1/2" × 26 3/4"', op: 'CNC Route Profile' },
      { id: 'BP-02', name: 'Curved Base Bottom Plate (Right)', size: '44 1/2" × 26 3/4"', op: 'CNC Route Profile' },
      { id: 'BR-01', name: 'Front Rail Support Rib A', size: '38" × 11 1/4"', op: 'CNC Route Pocket' },
    ],
  },
  {
    sheet_num: 2,
    title: 'Sheet 2 of 8: Deck Substrate & Sinuous Spring Rails',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'DK-01', name: 'Radial Seat Deck Substrate (Left)', size: '42 3/8" × 24 3/4"', op: 'CNC Route / Boring' },
      { id: 'DK-02', name: 'Radial Seat Deck Substrate (Right)', size: '42 3/8" × 24 3/4"', op: 'CNC Route / Boring' },
      { id: 'SR-01', name: 'Sinuous Spring Front Anchor Rail', size: '41 1/2" × 3 1/2"', op: 'CNC Route Clips' },
      { id: 'SR-02', name: 'Sinuous Spring Rear Anchor Rail', size: '41 1/2" × 3 1/2"', op: 'CNC Route Clips' },
    ],
  },
  {
    sheet_num: 3,
    title: 'Sheet 3 of 8: Radial Frame Joists J1–J5',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'J-01', name: 'Radial Joist J1 (Left End)', size: '26" × 11 1/4"', op: 'CNC Route Tenons' },
      { id: 'J-02', name: 'Radial Joist J2', size: '24 3/4" × 11 1/4"', op: 'CNC Route Dadoes' },
      { id: 'J-03', name: 'Radial Joist J3', size: '24 3/4" × 11 1/4"', op: 'CNC Route Dadoes' },
      { id: 'J-04', name: 'Radial Joist J4', size: '24 3/4" × 11 1/4"', op: 'CNC Route Dadoes' },
      { id: 'J-05', name: 'Radial Joist J5 (Center Splice L)', size: '24 3/4" × 11 1/4"', op: 'CNC Splice Lap' },
    ],
  },
  {
    sheet_num: 4,
    title: 'Sheet 4 of 8: Radial Frame Joists J6–J9 & Blocking',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'J-06', name: 'Radial Joist J6 (Center Splice R)', size: '24 3/4" × 11 1/4"', op: 'CNC Splice Lap' },
      { id: 'J-07', name: 'Radial Joist J7', size: '24 3/4" × 11 1/4"', op: 'CNC Route Dadoes' },
      { id: 'J-08', name: 'Radial Joist J8', size: '24 3/4" × 11 1/4"', op: 'CNC Route Dadoes' },
      { id: 'J-09', name: 'Radial Joist J9 (Right End)', size: '26" × 11 1/4"', op: 'CNC Route Tenons' },
    ],
  },
  {
    sheet_num: 5,
    title: 'Sheet 5 of 8: Channel Back Boards CH-1 to CH-4 (Left Unit)',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'CHB-01', name: 'Channel Back Board #1', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
      { id: 'CHB-02', name: 'Channel Back Board #2', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
      { id: 'CHB-03', name: 'Channel Back Board #3', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
      { id: 'CHB-04', name: 'Channel Back Board #4', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
    ],
  },
  {
    sheet_num: 6,
    title: 'Sheet 6 of 8: Channel Back Boards CH-5 to CH-8 (Right Unit)',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'CHB-05', name: 'Channel Back Board #5', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
      { id: 'CHB-06', name: 'Channel Back Board #6', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
      { id: 'CHB-07', name: 'Channel Back Board #7', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
      { id: 'CHB-08', name: 'Channel Back Board #8', size: '9 5/32" × 36"', op: 'CNC Chamfer Edge' },
    ],
  },
  {
    sheet_num: 7,
    title: 'Sheet 7 of 8: Vertical Stood Ribs R1–R9 (Back Rake Skeleton)',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'VR-01', name: 'Vertical Rib Stack Left (R1-R3)', size: '44" × 8"', op: 'CNC 10° Rake Route' },
      { id: 'VR-02', name: 'Vertical Rib Stack Center (R4-R6)', size: '44" × 8"', op: 'CNC 10° Rake Route' },
      { id: 'VR-03', name: 'Vertical Rib Stack Right (R7-R9)', size: '44" × 8"', op: 'CNC 10° Rake Route' },
    ],
  },
  {
    sheet_num: 8,
    title: 'Sheet 8 of 8: Armrest End Components (Laminated / Slide-In)',
    material: '3/4" Baltic Birch 48" × 96"',
    parts: [
      { id: 'ARM-L', name: 'Armrest Assembly Blank (Left)', size: '27 5/8" × 44"', op: 'CNC Contour Profile' },
      { id: 'ARM-R', name: 'Armrest Assembly Blank (Right)', size: '27 5/8" × 44"', op: 'CNC Contour Profile' },
    ],
  },
];

export default function WillardCST23Page() {
  // Theme state: 'gold' | 'dark'
  const [theme, setTheme] = useState<'gold' | 'dark'>('dark');

  // Foam & Fabric Layers Controls
  const [backFoamEnabled, setBackFoamEnabled] = useState(true);
  const [backFoamThickness, setBackFoamThickness] = useState(2.0); // 0.5" to 4.0"
  const [backFabricEnabled, setBackFabricEnabled] = useState(true);

  const [seatFoamEnabled, setSeatFoamEnabled] = useState(true);
  const [seatFoamThickness, setSeatFoamThickness] = useState(5.0); // 1.0" to 7.0"
  const [seatFabricEnabled, setSeatFabricEnabled] = useState(true);

  const [showFrame, setShowFrame] = useState(false);

  // Channel Sizing Controls
  const [channelCount] = useState(8);
  const [channelWidth, setChannelWidth] = useState(9.15625); // 9 5/32" nominal
  const [channelHeight, setChannelHeight] = useState(36.0); // 36" nominal (range 24-38)
  const [staplingAllowance, setStaplingAllowance] = useState(2.5); // 2" to 3"

  // Armrest Options
  const [armType, setArmType] = useState<'laminated_end' | 'slide_in'>('laminated_end');
  const [armUpholstered, setArmUpholstered] = useState(true);
  const [armFringe, setArmFringe] = useState(true);

  // Active sheet tab
  const [activeSheetNum, setActiveSheetNum] = useState(1);

  // Three.js Canvas container ref
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const dynamicMeshesRef = useRef<THREE.Group | null>(null);

  // Calculated dimensions & cuts (fractions only)
  const woodCutWidthStr = formatFraction(channelWidth);
  const woodCutHeightStr = formatFraction(channelHeight);
  const woodCutSizeStr = `${woodCutWidthStr} × ${woodCutHeightStr}`;

  const foamCutDepthStr = formatFraction(backFoamThickness);
  const foamCutSizeStr = `${woodCutWidthStr} × ${woodCutHeightStr} × ${foamCutDepthStr}`;

  const fabricCutWidth = channelWidth + staplingAllowance;
  const fabricCutHeight = channelHeight + staplingAllowance;
  const fabricCutWidthStr = formatFraction(fabricCutWidth);
  const fabricCutHeightStr = formatFraction(fabricCutHeight);
  const fabricCutSizeStr = `${fabricCutWidthStr} × ${fabricCutHeightStr}`;

  // Three.js Scene Setup & Render Loop
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Dimensions
    const width = container.clientWidth || 640;
    const height = container.clientHeight || 480;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(theme === 'dark' ? 0x141210 : 0xf0ece4);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 3000);
    camera.position.set(-110, 80, 140);
    camera.lookAt(0, 20, 10);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Lights
    const hemiLight = new THREE.HemisphereLight(0xfff5e6, 0x8a7a5a, 0.95);
    scene.add(hemiLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.85);
    dirLight.position.set(-120, 180, 160);
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0xd4af37, 0.35);
    fillLight.position.set(120, -50, -100);
    scene.add(fillLight);

    // Floor grid
    const grid = new THREE.GridHelper(180, 18, theme === 'dark' ? 0xd4af37 : 0xb8960c, theme === 'dark' ? 0x332b22 : 0xd8d0c2);
    grid.position.y = 0;
    scene.add(grid);

    // Dynamic meshes group
    const dynamicGroup = new THREE.Group();
    scene.add(dynamicGroup);
    dynamicMeshesRef.current = dynamicGroup;

    // Simple Orbit Controls
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let sphTheta = -0.7;
    let sphPhi = 1.15;
    let sphRadius = 185;
    const target = new THREE.Vector3(0, 22, 10);

    const updateCameraPos = () => {
      sphPhi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05, sphPhi));
      camera.position.x = target.x + sphRadius * Math.sin(sphPhi) * Math.sin(sphTheta);
      camera.position.y = target.y + sphRadius * Math.cos(sphPhi);
      camera.position.z = target.z + sphRadius * Math.sin(sphPhi) * Math.cos(sphTheta);
      camera.lookAt(target);
    };
    updateCameraPos();

    const onPointerDown = (e: PointerEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!isDragging) return;
      const dx = e.clientX - prevMouseX;
      const dy = e.clientY - prevMouseY;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
      sphTheta -= dx * 0.008;
      sphPhi -= dy * 0.008;
      updateCameraPos();
    };

    const onPointerUp = () => {
      isDragging = false;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      sphRadius = Math.max(60, Math.min(400, sphRadius + e.deltaY * 0.15));
      updateCameraPos();
    };

    const dom = renderer.domElement;
    dom.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    dom.addEventListener('wheel', onWheel, { passive: false });

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (!container || !renderer || !camera) return;
      const nw = container.clientWidth;
      const nh = container.clientHeight;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    });
    ro.observe(container);

    let reqId: number;
    const animate = () => {
      reqId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(reqId);
      ro.disconnect();
      dom.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      dom.removeEventListener('wheel', onWheel);
      renderer.dispose();
    };
  }, [theme]);

  // Procedural Textures & Materials Generator
  const createNympheusTexture = () => {
    const c = document.createElement('canvas');
    c.width = 256;
    c.height = 512;
    const g = c.getContext('2d')!;
    g.fillStyle = '#2d422a'; // Emerald velvet base
    g.fillRect(0, 0, 256, 512);

    g.strokeStyle = '#3d5939';
    g.lineWidth = 4;
    g.beginPath();
    g.moveTo(128, 512);
    g.bezierCurveTo(60, 380, 196, 320, 128, 220);
    g.bezierCurveTo(60, 140, 196, 80, 128, 0);
    g.stroke();

    for (const cy of [420, 270, 110]) {
      g.fillStyle = '#b8960c';
      g.beginPath();
      g.ellipse(128, cy, 14, 22, 0, 0, Math.PI * 2);
      g.fill();

      g.fillStyle = '#d4af37';
      g.beginPath();
      g.ellipse(128, cy - 4, 8, 12, 0, 0, Math.PI * 2);
      g.fill();
    }
    const t = new THREE.CanvasTexture(c);
    t.anisotropy = 4;
    return t;
  };

  const createVinylTexture = (base: string) => {
    const c = document.createElement('canvas');
    c.width = 128;
    c.height = 128;
    const g = c.getContext('2d')!;
    g.fillStyle = base;
    g.fillRect(0, 0, 128, 128);
    for (let i = 0; i < 600; i++) {
      g.fillStyle = Math.random() < 0.5 ? 'rgba(0,0,0,0.1)' : 'rgba(255,230,190,0.08)';
      g.fillRect(Math.random() * 128, Math.random() * 128, 1.5, 1.5);
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(4, 4);
    return t;
  };

  const createFringeTexture = () => {
    const c = document.createElement('canvas');
    c.width = 256;
    c.height = 64;
    const g = c.getContext('2d')!;
    g.fillStyle = '#5c3a1e';
    g.fillRect(0, 0, 256, 64);
    g.fillStyle = '#8a5f33';
    g.fillRect(0, 0, 256, 12); // header
    for (let x = 2; x < 256; x += 4) {
      g.strokeStyle = x % 8 < 4 ? '#d4af37' : '#e6c86e';
      g.lineWidth = 2.2;
      g.beginPath();
      g.moveTo(x, 12);
      g.lineTo(x, 62);
      g.stroke();
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = THREE.RepeatWrapping;
    t.repeat.set(12, 1);
    return t;
  };

  // Rebuild 3D Model meshes when layer / sizing / armrest options change
  useEffect(() => {
    const group = dynamicMeshesRef.current;
    if (!group) return;

    // Clear previous objects
    while (group.children.length > 0) {
      const obj = group.children[0];
      group.remove(obj);
      if ((obj as THREE.Mesh).geometry) (obj as THREE.Mesh).geometry.dispose();
    }

    const edgeMat = new THREE.LineBasicMaterial({ color: 0x1f1810, linewidth: 1.5 });
    const outline = (mesh: THREE.Mesh, deg = 26) => {
      mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry, deg), edgeMat));
      return mesh;
    };

    // CST-23 Canonical Radial Parameters
    const R_FRONT = 37.07;
    const RR = 63.82;
    const TH = 1.3522; // 77.47 deg sweep
    const C0 = RR;
    const STOCK = 1.5;

    const pos = (a: number, r: number, h: number) => {
      return new THREE.Vector3(r * Math.sin(a), h, -(r * Math.cos(a) - C0));
    };

    const arcBox = (
      a1: number,
      a2: number,
      r1: number,
      r2: number,
      h1: number,
      h2: number,
      mat: THREE.Material,
      segs = 12
    ) => {
      const g = new THREE.BufferGeometry();
      const v: number[] = [];
      const idx: number[] = [];

      for (let i = 0; i <= segs; i++) {
        const a = a1 + ((a2 - a1) * i) / segs;
        for (const [r, h] of [
          [r1, h1],
          [r2, h1],
          [r2, h2],
          [r1, h2],
        ]) {
          const p = pos(a, r, h);
          v.push(p.x, p.y, p.z);
        }
      }

      for (let i = 0; i < segs; i++) {
        const b = i * 4;
        const q = (o1: number, o2: number, o3: number, o4: number) => {
          idx.push(b + o1, b + o2, b + o3, b + o1, b + o3, b + o4);
        };
        q(0, 4, 5, 1);
        q(3, 2, 6, 7);
        q(0, 3, 7, 4);
        q(1, 5, 6, 2);
      }
      idx.push(0, 1, 2, 0, 2, 3);
      const b = segs * 4;
      idx.push(b, b + 3, b + 2, b, b + 2, b + 1);

      g.setIndex(idx);
      g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
      g.computeVertexNormals();
      return new THREE.Mesh(g, mat);
    };

    // Common Materials
    const birchMat = new THREE.MeshStandardMaterial({ color: 0xd9c5a0, roughness: 0.65, side: THREE.DoubleSide });
    const woodDarkMat = new THREE.MeshStandardMaterial({ color: 0x8f6535, roughness: 0.5, side: THREE.DoubleSide });
    const foamMat = new THREE.MeshStandardMaterial({ color: 0xe8df92, roughness: 0.95, side: THREE.DoubleSide });
    const seatFoamMat = foamMat;
    const seatVinylMat = new THREE.MeshStandardMaterial({
      map: createVinylTexture('#8a5f33'),
      roughness: 0.72,
      side: THREE.DoubleSide,
    });
    const baseVinylMat = new THREE.MeshStandardMaterial({
      map: createVinylTexture('#6a4522'),
      roughness: 0.8,
      side: THREE.DoubleSide,
    });
    const backVelvetMat = new THREE.MeshStandardMaterial({
      map: createNympheusTexture(),
      roughness: 0.88,
      side: THREE.DoubleSide,
    });
    const fringeMat = new THREE.MeshStandardMaterial({
      map: createFringeTexture(),
      roughness: 0.8,
      side: THREE.DoubleSide,
    });

    const A0 = -TH / 2;
    const A1 = TH / 2;
    const dEnd = (STOCK + 0.15) / (R_FRONT - 0.5);
    const A0c = A0 + dEnd;
    const A1c = A1 - dEnd;

    // 1. CARCASS & BASE PLATES (Always present or enhanced in frame mode)
    const baseBand = arcBox(A0c, A1c, R_FRONT, R_FRONT + 3.5, 1.0, 12.0, baseVinylMat, 16);
    group.add(outline(baseBand, 35));

    // 2. SEAT LAYERS (Wood Substrate + Foam Layer + Vinyl Fabric Layer)
    const seatSubstrateHeight = 12.0;
    const seatBoardTop = 13.0;
    // Wood deck substrate
    const seatDeck = arcBox(A0c, A1c, R_FRONT + 0.5, R_FRONT + 25.5, seatSubstrateHeight, seatBoardTop, birchMat, 16);
    group.add(outline(seatDeck, 30));

    // Seat Foam Layer (Adjustable thickness)
    const seatFoamTop = seatBoardTop + (seatFoamEnabled ? seatFoamThickness : 0.2);
    if (seatFoamEnabled) {
      const seatFoamMesh = arcBox(
        A0c + 0.005,
        A1c - 0.005,
        R_FRONT + 0.6,
        R_FRONT + 25.0,
        seatBoardTop,
        seatFoamTop,
        seatFoamMat,
        16
      );
      group.add(outline(seatFoamMesh, 35));
    }

    // Seat Fabric Layer (Vinyl wrap over foam or substrate)
    if (seatFabricEnabled) {
      const fabricSeatTop = seatFoamTop + 0.35;
      const seatFabricMesh = arcBox(
        A0c,
        A1c,
        R_FRONT + 0.3,
        R_FRONT + 25.3,
        seatFoamTop - 0.2,
        fabricSeatTop,
        seatVinylMat,
        18
      );
      group.add(outline(seatFabricMesh, 40));
    }

    // Front Nose along arc
    const noseMat = seatFabricEnabled ? seatVinylMat : seatFoamEnabled ? seatFoamMat : birchMat;
    const nose = arcBox(A0c, A1c, R_FRONT - 0.5, R_FRONT + 1.2, 12.0, seatFoamTop + 0.2, noseMat, 18);
    group.add(outline(nose, 30));

    // 3. BACK CHANNELS LAYERS (Wood Backing + Foam Layer + Nympheus Fabric Layer)
    const dCh = (STOCK + 0.35) / (R_FRONT + 18.0);
    const A0i = A0 + dCh;
    const A1i = A1 - dCh;
    const xFace = (h: number) => (h <= 19 ? 18.0 : 18.0 + ((h - 19) / 25) * 5.75);

    const seatTopHeight = seatFabricEnabled ? seatFoamTop + 0.35 : seatFoamTop;
    const channelBaseH = Math.max(17.0, seatTopHeight);
    const channelTopH = channelBaseH + channelHeight;

    for (let i = 0; i < channelCount; i++) {
      const a1 = A0i + ((A1i - A0i) * i) / channelCount + 0.003;
      const a2 = A0i + ((A1i - A0i) * (i + 1)) / channelCount - 0.003;

      // 3A. Wood Channel Backer Board (True Size, 3/4" Baltic Birch)
      const woodBacker = arcBox(a1, a2, R_FRONT + 23.5, R_FRONT + 24.25, channelBaseH, channelTopH, birchMat, 6);
      group.add(outline(woodBacker, 25));

      // 3B. Foam Layer (Adjustable thickness)
      if (backFoamEnabled) {
        const foamThick = backFoamThickness;
        const foamMesh = arcBox(
          a1 + 0.002,
          a2 - 0.002,
          R_FRONT + 23.5 - foamThick,
          R_FRONT + 23.5,
          channelBaseH,
          channelTopH,
          foamMat,
          6
        );
        group.add(outline(foamMesh, 28));
      }

      // 3C. Fabric Layer (GP&J Baker Nympheus Velvet Emerald BP10814-2)
      if (backFabricEnabled) {
        const foamThick = backFoamEnabled ? backFoamThickness : 0.2;
        const frontR = R_FRONT + 23.5 - foamThick - 0.25;
        const fabricMesh = arcBox(a1, a2, frontR, frontR + 0.5, channelBaseH - 0.5, channelTopH + 0.5, backVelvetMat, 6);
        group.add(outline(fabricMesh, 30));

        // Soft Crown Cap
        const midA = (a1 + a2) / 2;
        const capGeo = new THREE.CylinderGeometry(0.5, 0.5, channelWidth * 0.95, 10);
        capGeo.rotateZ(Math.PI / 2);
        const capMesh = new THREE.Mesh(capGeo, backVelvetMat);
        capMesh.position.copy(pos(midA, frontR + 0.5, channelTopH + 0.4));
        capMesh.rotation.y = -midA;
        group.add(capMesh);
      }
    }

    // 4. ARMRESTS (Laminated END Arm vs Slide-In, Upholstered Face vs Wood, Fringe Returns)
    const armShape = () => {
      const s = new THREE.Shape();
      s.moveTo(0, 0);
      s.lineTo(0, 18.2);
      s.quadraticCurveTo(1.0, 19.2, 2.4, 19);
      s.lineTo(16.1, 19);
      s.quadraticCurveTo(17.5, 19.1, 17.9, 20.2);
      s.lineTo(23.65, 42.0);
      s.quadraticCurveTo(24.1, 44, 26.1, 44);
      s.lineTo(27.65, 44);
      s.lineTo(27.65, 0);
      s.closePath();
      return s;
    };

    const armMat = armUpholstered ? seatVinylMat : woodDarkMat;
    const armGeo = new THREE.ExtrudeGeometry(armShape(), {
      depth: armType === 'laminated_end' ? 1.75 : 1.25,
      bevelEnabled: armUpholstered,
      bevelSegments: 2,
      steps: 1,
      bevelSize: 0.15,
      bevelThickness: 0.15,
    });

    for (const side of [1, -1]) {
      const aArm = (side * TH) / 2;
      const armMesh = outline(new THREE.Mesh(armGeo, armMat), 24);
      const rootPos = pos(aArm, R_FRONT - 0.3, 0);
      armMesh.position.copy(rootPos);
      armMesh.rotation.y = Math.PI / 2 - aArm + (side === -1 ? Math.PI : 0);
      if (side === -1) {
        armMesh.scale.x = -1;
      }
      group.add(armMesh);

      // Arm fringe returns
      if (armFringe) {
        const fringeGeo = new THREE.BufferGeometry();
        const fv: number[] = [];
        const fidx: number[] = [];
        const fn = 10;
        const norm = new THREE.Vector3(Math.cos(aArm), 0, Math.sin(aArm)).multiplyScalar(side * 0.25);
        for (let j = 0; j <= fn; j++) {
          const r = R_FRONT + (26.75 * j) / fn;
          for (const h of [7, 1]) {
            const p = pos(aArm, r, h).add(norm);
            fv.push(p.x, p.y, p.z);
          }
        }
        for (let j = 0; j < fn; j++) {
          const b = j * 2;
          fidx.push(b, b + 2, b + 3, b, b + 3, b + 1);
        }
        fringeGeo.setIndex(fidx);
        fringeGeo.setAttribute('position', new THREE.Float32BufferAttribute(fv, 3));
        fringeGeo.computeVertexNormals();
        group.add(new THREE.Mesh(fringeGeo, fringeMat));
      }
    }

    // 5. FRONTLINE BULLION FRINGE (Fabricut Rupi 158 6" Bullion Fringe)
    const fg = new THREE.BufferGeometry();
    const fv: number[] = [];
    const fidx: number[] = [];
    const fsegs = 20;
    for (let i = 0; i <= fsegs; i++) {
      const a = A0c + ((A1c - A0c) * i) / fsegs;
      for (const h of [7, 1]) {
        const p = pos(a, R_FRONT - 0.35, h);
        fv.push(p.x, p.y, p.z);
      }
    }
    for (let i = 0; i < fsegs; i++) {
      const b = i * 2;
      fidx.push(b, b + 2, b + 3, b, b + 3, b + 1);
    }
    fg.setIndex(fidx);
    fg.setAttribute('position', new THREE.Float32BufferAttribute(fv, 3));
    fg.computeVertexNormals();
    group.add(new THREE.Mesh(fg, fringeMat));

    // 6. FRAME SKELETON (When showFrame is active)
    if (showFrame) {
      // Joists J1 to J9
      for (let j = 0; j <= 8; j++) {
        const aj = A0 + (TH * j) / 8;
        const joistMesh = arcBox(aj - 0.012, aj + 0.012, R_FRONT + 1.0, R_FRONT + 25.0, 1.2, 11.5, birchMat, 4);
        group.add(outline(joistMesh, 15));
      }
      // Vertical Ribs R1 to R9 along back rake
      for (let r = 0; r <= 8; r++) {
        const ar = A0 + (TH * r) / 8;
        const ribMesh = arcBox(ar - 0.01, ar + 0.01, R_FRONT + 23.5, R_FRONT + 25.5, 13.0, channelTopH - 1.0, woodDarkMat, 4);
        group.add(outline(ribMesh, 15));
      }
    }
  }, [
    backFoamEnabled,
    backFoamThickness,
    backFabricEnabled,
    seatFoamEnabled,
    seatFoamThickness,
    seatFabricEnabled,
    showFrame,
    channelCount,
    channelWidth,
    channelHeight,
    staplingAllowance,
    armType,
    armUpholstered,
    armFringe,
  ]);

  // View Presets
  const setCameraView = (view: 'front' | 'iso' | 'rear' | 'arm' | 'top') => {
    const cam = cameraRef.current;
    if (!cam) return;
    if (view === 'front') cam.position.set(0, 35, 190);
    if (view === 'iso') cam.position.set(-110, 80, 140);
    if (view === 'rear') cam.position.set(0, 45, -170);
    if (view === 'arm') cam.position.set(-105, 30, 45);
    if (view === 'top') cam.position.set(0, 220, 10);
    cam.lookAt(0, 22, 10);
  };

  // Color classes depending on theme
  const isDark = theme === 'dark';
  const bgMain = isDark ? 'bg-[#0f0e0d] text-[#f5f5f4]' : 'bg-[#f7f5f0] text-[#1c1917]';
  const cardBg = isDark ? 'bg-[#181614] border-[#2e2a25]' : 'bg-white border-[#e5e0d8]';
  const headerBg = isDark ? 'bg-[#141210] border-[#2e2a25]' : 'bg-white border-[#e5e0d8]';
  const accentGold = '#d4af37';

  return (
    <div className={`min-h-screen ${bgMain} font-sans transition-colors duration-200 pb-16`}>
      {/* Top Header / Breadcrumb */}
      <header className={`border-b ${headerBg} sticky top-0 z-30 px-4 py-3 backdrop-blur-md`}>
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <a
              href="/woodcraft"
              className="text-xs font-bold uppercase tracking-wider text-[#b8960c] hover:underline flex items-center gap-1"
            >
              WoodCraft
            </a>
            <ChevronRight size={14} className="text-stone-500" />
            <div>
              <h1 className="text-base sm:text-lg font-bold flex items-center gap-2">
                <span>Willard CST-23 3D Assembly Review</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 font-semibold border border-amber-500/20">
                  Reviewed Custom Piece
                </span>
              </h1>
              <p className="text-xs text-stone-400">
                Maggie O&apos;Neill / The Willard Scotch Bar · Hyattsville, MD · Fractions Only
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Theme switcher */}
            <button
              onClick={() => setTheme(isDark ? 'gold' : 'dark')}
              className={`p-2 rounded-lg border text-xs font-medium flex items-center gap-1.5 transition-colors ${
                isDark ? 'bg-stone-800 border-stone-700 text-amber-400' : 'bg-stone-100 border-stone-300 text-stone-800'
              }`}
              title="Toggle Dark / Gold Theme"
            >
              {isDark ? <Sun size={14} /> : <Moon size={14} />}
              <span className="hidden sm:inline">{isDark ? 'Gold Theme' : 'Dark Theme'}</span>
            </button>

            <a
              href="https://claude.ai/artifact/SopYioZ9n3atoMyeC4gnKu"
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 rounded-lg border border-amber-500/40 text-xs font-semibold text-amber-500 hover:bg-amber-500/10 flex items-center gap-1.5"
            >
              <ExternalLink size={13} />
              <span className="hidden sm:inline">Claude Artifact</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Content Container */}
      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* CST-23 Governed Custom Rule Banner */}
        <div
          className={`p-4 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
            isDark ? 'bg-amber-950/20 border-amber-600/30' : 'bg-amber-50 border-amber-300'
          }`}
        >
          <div className="flex items-start gap-3">
            <Info size={20} className="text-amber-500 shrink-0 mt-0.5" />
            <div className="text-xs space-y-1">
              <div className="font-bold uppercase tracking-wider text-amber-500">
                Willard CST-23 Reviewed Piece Rules
              </div>
              <p className={isDark ? 'text-stone-300' : 'text-stone-700'}>
                <strong>Wood/board cut = true size, no add-ons.</strong> Foam cut = same as wood cut. Fabric cut =
                foam/channel width plus 2 to 3 inches for stapling. Always list wood cut and fabric cut as separate
                labeled sizes. Willard CST-23 is a reviewed custom piece; general rules do not override it.{' '}
                <strong>Fractions only.</strong>
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="px-3 py-1 rounded bg-amber-500 text-stone-900 font-bold text-xs">
              8-Sheet Nest Pack
            </span>
          </div>
        </div>

        {/* 3D Assembly Viewport & Controls Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: 3D Viewport (7 Cols) */}
          <div className={`lg:col-span-7 flex flex-col rounded-2xl border overflow-hidden ${cardBg}`}>
            {/* Viewport Header */}
            <div className="px-4 py-3 border-b flex flex-wrap items-center justify-between gap-2 bg-black/20">
              <div className="flex items-center gap-2">
                <Box size={16} className="text-amber-500" />
                <span className="text-xs font-bold uppercase tracking-wider">Interactive 3D Assembly Model</span>
              </div>
              {/* Camera Presets */}
              <div className="flex items-center gap-1">
                {(['iso', 'front', 'rear', 'arm', 'top'] as const).map((view) => (
                  <button
                    key={view}
                    onClick={() => setCameraView(view)}
                    className="px-2 py-1 rounded text-[11px] font-semibold border border-stone-600/40 hover:bg-amber-500/10 hover:border-amber-500/50 uppercase transition-colors"
                  >
                    {view}
                  </button>
                ))}
              </div>
            </div>

            {/* 3D Canvas Box */}
            <div
              ref={mountRef}
              className="w-full h-[400px] sm:h-[480px] relative touch-none select-none cursor-grab active:cursor-grabbing"
            />

            {/* Viewport Footer HUD */}
            <div className="px-4 py-2.5 border-t text-[11px] flex flex-wrap items-center justify-between gap-2 bg-black/20 text-stone-400">
              <span>Drag to orbit · Scroll to zoom · Pinch on mobile</span>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 inline-block" /> Nympheus Velvet
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-700 inline-block" /> Vintage Ale Vinyl
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-400 inline-block" /> 6&quot; Bullion Fringe
                </span>
              </div>
            </div>
          </div>

          {/* Right Column: Layer & Sizing Controls (5 Cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Foam & Fabric Layer Controls */}
            <div className={`p-4 rounded-xl border space-y-4 ${cardBg}`}>
              <div className="flex items-center justify-between pb-2 border-b border-stone-700/30">
                <div className="flex items-center gap-2">
                  <Layers size={16} className="text-amber-500" />
                  <h2 className="text-xs font-bold uppercase tracking-wider">1. Foam &amp; Fabric Layers</h2>
                </div>
                <button
                  onClick={() => setShowFrame(!showFrame)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold border transition-colors ${
                    showFrame ? 'bg-amber-500 text-stone-900 border-amber-400' : 'border-stone-600 text-stone-300'
                  }`}
                >
                  {showFrame ? 'Frame: ON' : 'Show Frame'}
                </button>
              </div>

              {/* Back Channel Layers */}
              <div className="space-y-3 p-3 rounded-lg bg-black/10 border border-stone-700/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-400">Back Channels</span>
                  <div className="flex items-center gap-2">
                    <label className="text-[11px] flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={backFoamEnabled}
                        onChange={(e) => setBackFoamEnabled(e.target.checked)}
                        className="accent-amber-500"
                      />
                      <span>Foam Layer</span>
                    </label>
                    <label className="text-[11px] flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={backFabricEnabled}
                        onChange={(e) => setBackFabricEnabled(e.target.checked)}
                        className="accent-amber-500"
                      />
                      <span>Fabric Layer</span>
                    </label>
                  </div>
                </div>

                {/* Back Foam Thickness */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-stone-400">Back Foam Thickness:</span>
                    <span className="font-mono font-bold text-amber-400">
                      {formatFraction(backFoamThickness)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0.5}
                    max={4.0}
                    step={0.25}
                    disabled={!backFoamEnabled}
                    value={backFoamThickness}
                    onChange={(e) => setBackFoamThickness(parseFloat(e.target.value))}
                    className="w-full accent-amber-500 h-1.5 bg-stone-700 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-stone-500 font-mono">
                    <span>1/2&quot;</span>
                    <span>Nominal: 2&quot;</span>
                    <span>4&quot;</span>
                  </div>
                </div>
                <div className="text-[10px] text-stone-400">
                  Fabric: <em>GP&amp;J Baker Nympheus Velvet Emerald BP10814-2</em>
                </div>
              </div>

              {/* Seat Deck Layers */}
              <div className="space-y-3 p-3 rounded-lg bg-black/10 border border-stone-700/20">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-400">Seat Deck</span>
                  <div className="flex items-center gap-2">
                    <label className="text-[11px] flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seatFoamEnabled}
                        onChange={(e) => setSeatFoamEnabled(e.target.checked)}
                        className="accent-amber-500"
                      />
                      <span>Foam Layer</span>
                    </label>
                    <label className="text-[11px] flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={seatFabricEnabled}
                        onChange={(e) => setSeatFabricEnabled(e.target.checked)}
                        className="accent-amber-500"
                      />
                      <span>Fabric Layer</span>
                    </label>
                  </div>
                </div>

                {/* Seat Foam Thickness */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-stone-400">Seat Foam Thickness:</span>
                    <span className="font-mono font-bold text-amber-400">
                      {formatFraction(seatFoamThickness)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={1.0}
                    max={7.0}
                    step={0.5}
                    disabled={!seatFoamEnabled}
                    value={seatFoamThickness}
                    onChange={(e) => setSeatFoamThickness(parseFloat(e.target.value))}
                    className="w-full accent-amber-500 h-1.5 bg-stone-700 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-stone-500 font-mono">
                    <span>1&quot;</span>
                    <span>Nominal: 5&quot;</span>
                    <span>7&quot;</span>
                  </div>
                </div>
                <div className="text-[10px] text-stone-400">
                  Fabric: <em>Keyston Bros Vintage Ale SVI001 Vinyl</em>
                </div>
              </div>
            </div>

            {/* Channel Width & Height Sizing Controls */}
            <div className={`p-4 rounded-xl border space-y-4 ${cardBg}`}>
              <div className="flex items-center gap-2 pb-2 border-b border-stone-700/30">
                <Sliders size={16} className="text-amber-500" />
                <h2 className="text-xs font-bold uppercase tracking-wider">2. Channel Sizing Controls</h2>
              </div>

              {/* Channel Width */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-stone-400">Channel Width (Wood Cut):</span>
                  <span className="font-mono font-bold text-amber-400">{woodCutWidthStr}</span>
                </div>
                <input
                  type="range"
                  min={8.0}
                  max={12.0}
                  step={0.03125}
                  value={channelWidth}
                  onChange={(e) => setChannelWidth(parseFloat(e.target.value))}
                  className="w-full accent-amber-500 h-1.5 bg-stone-700 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-stone-500 font-mono">
                  <span>8&quot;</span>
                  <span>Nominal: 9 5/32&quot;</span>
                  <span>12&quot;</span>
                </div>
              </div>

              {/* Channel Height */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-stone-400">Channel Height (Open Item 1):</span>
                  <span className="font-mono font-bold text-amber-400">{woodCutHeightStr}</span>
                </div>
                <input
                  type="range"
                  min={24.0}
                  max={38.0}
                  step={0.5}
                  value={channelHeight}
                  onChange={(e) => setChannelHeight(parseFloat(e.target.value))}
                  className="w-full accent-amber-500 h-1.5 bg-stone-700 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-stone-500 font-mono">
                  <span>24&quot; Min</span>
                  <span>Nominal: 36&quot;</span>
                  <span>38&quot; Max</span>
                </div>
              </div>

              {/* Stapling Allowance */}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-stone-400">Fabric Stapling Allowance:</span>
                  <span className="font-mono font-bold text-amber-400">+{formatFraction(staplingAllowance)}</span>
                </div>
                <input
                  type="range"
                  min={2.0}
                  max={3.0}
                  step={0.125}
                  value={staplingAllowance}
                  onChange={(e) => setStaplingAllowance(parseFloat(e.target.value))}
                  className="w-full accent-amber-500 h-1.5 bg-stone-700 rounded-lg cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-stone-500 font-mono">
                  <span>+2&quot;</span>
                  <span>Nominal: +2 1/2&quot;</span>
                  <span>+3&quot;</span>
                </div>
              </div>
            </div>

            {/* Armrest Options */}
            <div className={`p-4 rounded-xl border space-y-3 ${cardBg}`}>
              <div className="flex items-center gap-2 pb-2 border-b border-stone-700/30">
                <Compass size={16} className="text-amber-500" />
                <h2 className="text-xs font-bold uppercase tracking-wider">3. Armrest Options</h2>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setArmType('laminated_end')}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold border text-center transition-colors ${
                    armType === 'laminated_end'
                      ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                      : 'border-stone-700 text-stone-400 hover:border-stone-500'
                  }`}
                >
                  Laminated END Arm
                </button>
                <button
                  onClick={() => setArmType('slide_in')}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold border text-center transition-colors ${
                    armType === 'slide_in'
                      ? 'bg-amber-500/20 border-amber-500 text-amber-400'
                      : 'border-stone-700 text-stone-400 hover:border-stone-500'
                  }`}
                >
                  Slide-In Panel
                </button>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 text-xs">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={armUpholstered}
                    onChange={(e) => setArmUpholstered(e.target.checked)}
                    className="accent-amber-500"
                  />
                  <span>Upholstered Face (Vinyl)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={armFringe}
                    onChange={(e) => setArmFringe(e.target.checked)}
                    className="accent-amber-500"
                  />
                  <span>Fringe Returns (Rupi 158)</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Live Cut Sizing Schedule Table (Fractions Only) */}
        <div className={`p-5 rounded-2xl border space-y-4 ${cardBg}`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-stone-700/30">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-wider text-amber-500">
                Channel Sizing Schedule (Fractions Only)
              </h2>
              <p className="text-xs text-stone-400">
                Separate labeled sizes: Wood cut = true size; Foam cut = same as wood; Fabric cut = +2&quot; to 3&quot; stapling wrap.
              </p>
            </div>
            {/* Labeled Quick Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="px-2.5 py-1 rounded bg-stone-800/80 border border-stone-700 text-xs font-mono">
                <span className="text-stone-400 text-[10px] block">Wood Cut (True Size):</span>
                <span className="text-amber-400 font-bold">{woodCutSizeStr}</span>
              </div>
              <div className="px-2.5 py-1 rounded bg-stone-800/80 border border-stone-700 text-xs font-mono">
                <span className="text-stone-400 text-[10px] block">Fabric Cut (With Wrap):</span>
                <span className="text-amber-400 font-bold">{fabricCutSizeStr}</span>
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-stone-700/40 text-stone-400 font-mono text-[11px]">
                  <th className="py-2.5 px-3">Part ID</th>
                  <th className="py-2.5 px-3">Part Description</th>
                  <th className="py-2.5 px-3 text-amber-400">Wood / Board Cut (True Size)</th>
                  <th className="py-2.5 px-3">Foam Cut (Same As Wood)</th>
                  <th className="py-2.5 px-3 text-amber-400">Fabric Cut (Stapling + Wrap)</th>
                  <th className="py-2.5 px-3">Material &amp; CNC Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-800/30 font-mono">
                {/* 8 Back Channels */}
                {Array.from({ length: channelCount }).map((_, idx) => (
                  <tr key={`ch-${idx}`} className="hover:bg-amber-500/5 transition-colors">
                    <td className="py-2 px-3 font-bold text-amber-500">CH-{String(idx + 1).padStart(2, '0')}</td>
                    <td className="py-2 px-3 text-stone-300">Wedge Back Channel #{idx + 1}</td>
                    <td className="py-2 px-3 font-bold text-amber-300">{woodCutSizeStr}</td>
                    <td className="py-2 px-3 text-stone-300">{foamCutSizeStr}</td>
                    <td className="py-2 px-3 font-bold text-amber-300">{fabricCutSizeStr}</td>
                    <td className="py-2 px-3 text-[11px] text-stone-400 font-sans">
                      GP&amp;J Baker Nympheus Velvet Emerald (+{formatFraction(staplingAllowance)} allowance)
                    </td>
                  </tr>
                ))}

                {/* Seat Cushions */}
                <tr className="hover:bg-amber-500/5 transition-colors">
                  <td className="py-2 px-3 font-bold text-amber-500">CUSH-L</td>
                  <td className="py-2 px-3 text-stone-300">Seat Deck Cushion Left Half</td>
                  <td className="py-2 px-3 font-bold text-amber-300">41 1/2&quot; × 24 3/4&quot;</td>
                  <td className="py-2 px-3 text-stone-300">41 1/2&quot; × 24 3/4&quot; × {formatFraction(seatFoamThickness)}</td>
                  <td className="py-2 px-3 font-bold text-amber-300">
                    {formatFraction(41.5 + staplingAllowance)} × {formatFraction(24.75 + staplingAllowance)}
                  </td>
                  <td className="py-2 px-3 text-[11px] text-stone-400 font-sans">
                    Keyston Bros Vintage Ale Vinyl
                  </td>
                </tr>
                <tr className="hover:bg-amber-500/5 transition-colors">
                  <td className="py-2 px-3 font-bold text-amber-500">CUSH-R</td>
                  <td className="py-2 px-3 text-stone-300">Seat Deck Cushion Right Half</td>
                  <td className="py-2 px-3 font-bold text-amber-300">41 1/2&quot; × 24 3/4&quot;</td>
                  <td className="py-2 px-3 text-stone-300">41 1/2&quot; × 24 3/4&quot; × {formatFraction(seatFoamThickness)}</td>
                  <td className="py-2 px-3 font-bold text-amber-300">
                    {formatFraction(41.5 + staplingAllowance)} × {formatFraction(24.75 + staplingAllowance)}
                  </td>
                  <td className="py-2 px-3 text-[11px] text-stone-400 font-sans">
                    Keyston Bros Vintage Ale Vinyl
                  </td>
                </tr>

                {/* Armrests */}
                <tr className="hover:bg-amber-500/5 transition-colors">
                  <td className="py-2 px-3 font-bold text-amber-500">ARM-01</td>
                  <td className="py-2 px-3 text-stone-300">
                    Left Armrest ({armType === 'laminated_end' ? 'Laminated END' : 'Slide-In'})
                  </td>
                  <td className="py-2 px-3 font-bold text-amber-300">27 5/8&quot; × 44&quot;</td>
                  <td className="py-2 px-3 text-stone-300">{armUpholstered ? '27 5/8" × 44" × 1/2"' : 'N/A (Exposed Wood)'}</td>
                  <td className="py-2 px-3 font-bold text-amber-300">
                    {armUpholstered
                      ? `${formatFraction(27.625 + staplingAllowance)} × ${formatFraction(44.0 + staplingAllowance)}`
                      : 'N/A'}
                  </td>
                  <td className="py-2 px-3 text-[11px] text-stone-400 font-sans">
                    {armUpholstered ? 'Vinyl Upholstered Face' : 'Exposed Baltic Birch Multiplex Edge'}
                  </td>
                </tr>
                <tr className="hover:bg-amber-500/5 transition-colors">
                  <td className="py-2 px-3 font-bold text-amber-500">ARM-02</td>
                  <td className="py-2 px-3 text-stone-300">
                    Right Armrest ({armType === 'laminated_end' ? 'Laminated END' : 'Slide-In'})
                  </td>
                  <td className="py-2 px-3 font-bold text-amber-300">27 5/8&quot; × 44&quot;</td>
                  <td className="py-2 px-3 text-stone-300">{armUpholstered ? '27 5/8" × 44" × 1/2"' : 'N/A (Exposed Wood)'}</td>
                  <td className="py-2 px-3 font-bold text-amber-300">
                    {armUpholstered
                      ? `${formatFraction(27.625 + staplingAllowance)} × ${formatFraction(44.0 + staplingAllowance)}`
                      : 'N/A'}
                  </td>
                  <td className="py-2 px-3 text-[11px] text-stone-400 font-sans">
                    {armUpholstered ? 'Vinyl Upholstered Face' : 'Exposed Baltic Birch Multiplex Edge'}
                  </td>
                </tr>

                {/* Fringe Trim */}
                {armFringe && (
                  <tr className="hover:bg-amber-500/5 transition-colors">
                    <td className="py-2 px-3 font-bold text-amber-500">TRIM-01</td>
                    <td className="py-2 px-3 text-stone-300">Fringe Header &amp; Bullion Drops</td>
                    <td className="py-2 px-3 text-stone-400">N/A (Trim)</td>
                    <td className="py-2 px-3 text-stone-400">N/A</td>
                    <td className="py-2 px-3 font-bold text-amber-300">84&quot; Linear (Front) + 54&quot; (Returns)</td>
                    <td className="py-2 px-3 text-[11px] text-stone-400 font-sans">
                      Fabricut Rupi 158 6&quot; Bullion Fringe (Header 7&quot; AFF, 1&quot; clearance)
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Revised CNC Production Pack (Nests on 8 Sheets) */}
        <div className={`p-5 rounded-2xl border space-y-4 ${cardBg}`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-stone-700/30">
            <div>
              <div className="flex items-center gap-2">
                <FileText size={18} className="text-amber-500" />
                <h2 className="text-sm font-bold uppercase tracking-wider text-amber-500">
                  4. Revised CNC Production Pack (Nests on 8 Sheets)
                </h2>
              </div>
              <p className="text-xs text-stone-400 mt-1">
                <strong>Pack Note:</strong> Revised pack nests on <strong>8 sheets</strong> (Claude artifact previously
                stated 9). Stored on Chief e&apos;s box at{' '}
                <code className="text-amber-400 font-mono">/workspace/willard_cst23_rev/</code>.
              </p>
            </div>

            {/* Direct download / local access actions */}
            <div className="flex flex-wrap items-center gap-2">
              <a
                href="/workspace/willard_cst23_rev/Willard_CST23_RevPack_CutList.pdf"
                className="px-3 py-1.5 rounded-lg border border-amber-500/40 text-xs font-semibold text-amber-400 hover:bg-amber-500/10 flex items-center gap-1.5"
                download
              >
                <Download size={13} />
                <span>Cut List PDF</span>
              </a>
              <a
                href="/workspace/willard_cst23_rev/Willard_CST23_Revised_Pack.zip"
                className="px-3 py-1.5 rounded-lg bg-amber-500 text-stone-900 text-xs font-bold hover:bg-amber-400 flex items-center gap-1.5"
                download
              >
                <Download size={13} />
                <span>Download Revised Pack (ZIP)</span>
              </a>
            </div>
          </div>

          {/* 8 Sheet Selector Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
            {SHEETS_STATIC.map((s) => (
              <button
                key={s.sheet_num}
                onClick={() => setActiveSheetNum(s.sheet_num)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold whitespace-nowrap transition-colors border ${
                  activeSheetNum === s.sheet_num
                    ? 'bg-amber-500 text-stone-900 border-amber-400'
                    : 'border-stone-700/40 text-stone-400 hover:border-stone-500'
                }`}
              >
                Sheet {s.sheet_num}
              </button>
            ))}
          </div>

          {/* Active Sheet Card */}
          {(() => {
            const curSheet = SHEETS_STATIC.find((s) => s.sheet_num === activeSheetNum) || SHEETS_STATIC[0];
            return (
              <div className="p-4 rounded-xl border border-stone-700/30 bg-black/10 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-xs font-bold text-amber-400">{curSheet.title}</h3>
                  <span className="text-[11px] font-mono text-stone-400">Material: {curSheet.material}</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {curSheet.parts.map((p) => (
                    <div key={p.id} className="p-3 rounded-lg border border-stone-800 bg-black/20 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-amber-400 text-xs">{p.id}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-stone-800 text-stone-400">{p.op}</span>
                      </div>
                      <div className="text-xs font-semibold text-stone-200">{p.name}</div>
                      <div className="text-xs font-mono text-stone-400">Cut Size: {p.size}</div>
                    </div>
                  ))}
                </div>

                <div className="pt-2 text-[11px] text-stone-400 flex items-center justify-between">
                  <span>
                    Linked SVG File:{' '}
                    <code className="text-amber-400">
                      /workspace/willard_cst23_rev/sheets/sheet_0{curSheet.sheet_num}.svg
                    </code>
                  </span>
                  <span>Part count: {curSheet.parts.length}</span>
                </div>
              </div>
            );
          })()}
        </div>

        {/* 5. Tracked Open Items (Fractions Only) */}
        <div className={`p-5 rounded-2xl border space-y-4 ${cardBg}`}>
          <div className="flex items-center gap-2 pb-3 border-b border-stone-700/30">
            <AlertCircle size={18} className="text-amber-500" />
            <h2 className="text-sm font-bold uppercase tracking-wider text-amber-500">
              5. Open Items Tracking Under WoodCraft by Empire (Fractions Only)
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {OPEN_ITEMS_STATIC.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-xl border border-stone-700/30 bg-black/10 flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-amber-400">{item.id}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-semibold border border-amber-500/30">
                      {item.status}
                    </span>
                  </div>
                  <h3 className="text-xs font-bold text-stone-200">{item.title}</h3>
                  <div className="text-xs text-stone-400 space-y-1">
                    <div>
                      <strong className="text-stone-300">Spec:</strong> {item.current_spec}
                    </div>
                    <div>
                      <strong className="text-stone-300">Permitted Range:</strong>{' '}
                      <span className="font-mono text-amber-400">{item.range}</span>
                    </div>
                    <div>
                      <strong className="text-stone-300">Impact:</strong> {item.impact}
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-stone-800 text-[11px] text-amber-500/90 font-mono">
                  {item.rule_note}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* WoodCraft by Empire Project Data Footer */}
        <footer className="pt-6 border-t border-stone-800/40 text-center text-xs text-stone-500 space-y-2">
          <p>
            <strong>WoodCraft by Empire</strong> · Project Ref: <code>WC-PRJ-CST23</code> · The Willard InterContinental
            (Scotch Bar CST-23)
          </p>
          <p>
            All cut sheets, 3D assembly models, and documentation synchronized under WoodCraft project data · Fractions Only
          </p>
        </footer>
      </main>
    </div>
  );
}
