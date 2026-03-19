'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Ruler, RotateCcw, Camera, Tag, Loader2, CheckCircle, Scissors, Crosshair, FileText, Trash2, Circle, Spline, Square, Pentagon, Undo2, Redo2, X, ChevronDown, ChevronRight, Edit3 } from 'lucide-react';
import type * as THREE_NS from 'three';

/* ═══════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════ */

interface Measurement {
  p1: any;
  p2: any;
  distRaw: number;        // raw scene units
  label: string;
}

interface TreatmentArea {
  id: string;
  label: string;
  points: any[];           // THREE.Vector3[]
  widthRaw: number;
  heightRaw: number;
}

interface ThreeViewerProps {
  modelUrl: string;
  width?: number;
  height?: number;
  onCapture?: (dataUrl: string) => void;
  onExportData?: (data: {
    measurements: { label: string; value_inches: number; calibrated: boolean }[];
    treatmentAreas: { label: string; width_inches: number; height_inches: number }[];
    scaleFactor: number | null;
    screenshot: string;
  }) => void;
}

/* ═══════════════════════════════════════════════════════════
   Calibration presets
   ═══════════════════════════════════════════════════════════ */

const CALIBRATION_PRESETS = [
  { label: 'Standard door height', inches: 80 },
  { label: 'Standard window (36")', inches: 36 },
  { label: 'Outlet plate height', inches: 4.5 },
  { label: 'Floor tile (12")', inches: 12 },
  { label: 'Credit card width', inches: 3.375 },
  { label: 'Custom...', inches: 0 },
];

/* ═══════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════ */

export default function ThreeViewer({ modelUrl, width = 500, height = 400, onCapture, onExportData }: ThreeViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<any>(null);
  const rendererRef = useRef<any>(null);
  const cameraRef = useRef<any>(null);
  const controlsRef = useRef<any>(null);
  const modelRef = useRef<any>(null);
  const animFrameRef = useRef<number>(0);
  const threeRef = useRef<any>(null);

  const [ready, setReady] = useState(false);
  const [loadError, setLoadError] = useState('');

  // Tool modes (only one active at a time)
  type ToolMode = 'none' | 'measure' | 'annotate' | 'calibrate' | 'treatment';
  const [toolMode, setToolMode] = useState<ToolMode>('none');

  // Annotations
  const [annotations, setAnnotations] = useState<{ x: number; y: number; label: string }[]>([]);

  // Measurements
  const [measurePoints, setMeasurePoints] = useState<any[]>([]);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);

  // Calibration
  const [scaleFactor, setScaleFactor] = useState<number | null>(null); // inches per scene unit
  const [calibratePoints, setCalibratePoints] = useState<any[]>([]);
  const [showCalibDialog, setShowCalibDialog] = useState(false);
  const [calibDistRaw, setCalibDistRaw] = useState(0);
  const [calibInches, setCalibInches] = useState('');

  // Treatment areas
  const [treatmentAreas, setTreatmentAreas] = useState<TreatmentArea[]>([]);
  const [currentTreatmentPts, setCurrentTreatmentPts] = useState<any[]>([]);
  const [treatmentLabel, setTreatmentLabel] = useState('');
  // Treatment shape sub-modes
  type TreatmentShape = 'polygon' | 'rectangle' | 'curve' | 'arch';
  const [treatmentShape, setTreatmentShape] = useState<TreatmentShape>('polygon');
  // For arch mode: center point + radius point
  const [archCenter, setArchCenter] = useState<any>(null);
  // For rectangle mode: just 2 corner clicks
  const [rectCorners, setRectCorners] = useState<any[]>([]);

  // Selection & editing
  const [selectedAreaId, setSelectedAreaId] = useState<string | null>(null);
  const [expandedAreaId, setExpandedAreaId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState('');

  // Undo/redo history
  type HistoryAction =
    | { type: 'add_area'; area: TreatmentArea }
    | { type: 'delete_area'; area: TreatmentArea; index: number }
    | { type: 'edit_area'; id: string; prev: TreatmentArea; next: TreatmentArea }
    | { type: 'add_measurement'; measurement: Measurement }
    | { type: 'delete_measurement'; measurement: Measurement; index: number };
  const [undoStack, setUndoStack] = useState<HistoryAction[]>([]);
  const [redoStack, setRedoStack] = useState<HistoryAction[]>([]);

  const pushUndo = useCallback((action: HistoryAction) => {
    setUndoStack(prev => [...prev.slice(-9), action]); // keep last 10
    setRedoStack([]); // clear redo on new action
  }, []);

  // ── Add treatment area with undo tracking ──
  const addTreatmentArea = useCallback((area: TreatmentArea) => {
    setTreatmentAreas(prev => [...prev, area]);
    pushUndo({ type: 'add_area', area });
  }, [pushUndo]);

  // ── Delete treatment area by id with undo tracking ──
  const deleteTreatmentAreaById = useCallback((id: string) => {
    setTreatmentAreas(prev => {
      const idx = prev.findIndex(a => a.id === id);
      if (idx === -1) return prev;
      pushUndo({ type: 'delete_area', area: prev[idx], index: idx });
      return prev.filter(a => a.id !== id);
    });
    if (selectedAreaId === id) { setSelectedAreaId(null); setExpandedAreaId(null); }
  }, [pushUndo, selectedAreaId]);

  // Helpers
  const toInches = (raw: number) => scaleFactor ? Math.round(raw * scaleFactor * 10) / 10 : null;
  const formatDist = (raw: number) => {
    const inches = toInches(raw);
    return inches !== null ? `${inches}"` : `${Math.round(raw * 100) / 100} units`;
  };

  const activateTool = (mode: ToolMode) => {
    setToolMode(prev => prev === mode ? 'none' : mode);
    setMeasurePoints([]);
    setCalibratePoints([]);
    setCurrentTreatmentPts([]);
    setArchCenter(null);
    setRectCorners([]);
  };

  // ── Initialize Three.js ──
  useEffect(() => {
    let disposed = false;
    const init = async () => {
      if (!canvasRef.current) return;
      const THREE = await import('three');
      const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');
      threeRef.current = THREE;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xf5f3ef);
      sceneRef.current = scene;

      const camera = new THREE.PerspectiveCamera(50, width / height, 0.01, 1000);
      camera.position.set(3, 2.5, 3);
      cameraRef.current = camera;

      const renderer = new THREE.WebGLRenderer({ canvas: canvasRef.current, antialias: true, preserveDrawingBuffer: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.2;
      rendererRef.current = renderer;

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.minDistance = 0.5;
      controls.maxDistance = 50;
      controlsRef.current = controls;

      scene.add(new THREE.AmbientLight(0xffffff, 0.6));
      const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
      dirLight.position.set(5, 8, 5);
      dirLight.castShadow = true;
      scene.add(dirLight);
      const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
      fillLight.position.set(-3, 2, -3);
      scene.add(fillLight);

      scene.add(new THREE.GridHelper(10, 20, 0xcccccc, 0xe5e5e5));

      try {
        const hashExt = modelUrl.includes('#.') ? modelUrl.split('#.').pop()?.toLowerCase() : null;
        const ext = hashExt || modelUrl.split('.').pop()?.toLowerCase() || 'glb';
        const cleanUrl = modelUrl.split('#')[0];
        let loadedObj: THREE_NS.Object3D | null = null;

        if (ext === 'obj') {
          const { OBJLoader } = await import('three/examples/jsm/loaders/OBJLoader.js');
          const loader = new OBJLoader();
          loadedObj = await new Promise<THREE_NS.Object3D>((resolve, reject) => { loader.load(cleanUrl, resolve, undefined, reject); });
        } else if (ext === 'ply') {
          const { PLYLoader } = await import('three/examples/jsm/loaders/PLYLoader.js');
          const loader = new PLYLoader();
          const geometry = await new Promise<THREE_NS.BufferGeometry>((resolve, reject) => { loader.load(cleanUrl, resolve, undefined, reject); });
          geometry.computeVertexNormals();
          loadedObj = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xcccccc, flatShading: true }));
        } else {
          const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js');
          const loader = new GLTFLoader();
          const gltf = await new Promise<any>((resolve, reject) => { loader.load(cleanUrl, resolve, undefined, reject); });
          loadedObj = gltf.scene;
        }

        if (disposed || !loadedObj) return;

        const box = new THREE.Box3().setFromObject(loadedObj);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = maxDim > 0 ? 3 / maxDim : 1;
        loadedObj.position.sub(center);
        loadedObj.scale.multiplyScalar(scale);
        const scaledBox = new THREE.Box3().setFromObject(loadedObj);
        loadedObj.position.y -= scaledBox.min.y;
        scene.add(loadedObj);
        modelRef.current = loadedObj;

        const finalBox = new THREE.Box3().setFromObject(loadedObj);
        const finalSize = finalBox.getSize(new THREE.Vector3());
        const dist = Math.max(finalSize.x, finalSize.y, finalSize.z) * 2;
        camera.position.set(dist * 0.8, dist * 0.6, dist * 0.8);
        controls.target.copy(finalBox.getCenter(new THREE.Vector3()));
        controls.update();
        setReady(true);
      } catch (err: any) {
        console.error('3D load error:', err);
        setLoadError(err.message || 'Failed to load 3D model');
      }

      const animate = () => {
        if (disposed) return;
        animFrameRef.current = requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      };
      animate();
    };
    init();
    return () => {
      disposed = true;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      rendererRef.current?.dispose();
      controlsRef.current?.dispose();
    };
  }, [modelUrl, width, height]);

  // ── Raycast helper ──
  const raycast = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!canvasRef.current || !cameraRef.current || !sceneRef.current || !threeRef.current) return null;
    const THREE = threeRef.current;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(x, y), cameraRef.current);
    const intersects = raycaster.intersectObjects(sceneRef.current.children, true);
    return intersects.find((i: any) => !i.object.userData?.isMeasure && !i.object.userData?.isTreatment && i.object.type !== 'GridHelper') || null;
  }, []);

  // ── Add sphere marker to scene ──
  const addMarker = useCallback((point: any, color: number = 0xb8960c, tag: string = 'isMeasure') => {
    if (!threeRef.current || !sceneRef.current) return;
    const THREE = threeRef.current;
    const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.03, 16, 16), new THREE.MeshBasicMaterial({ color }));
    sphere.position.copy(point);
    sphere.userData[tag] = true;
    sceneRef.current.add(sphere);
  }, []);

  // ── Add line to scene ──
  const addLine = useCallback((p1: any, p2: any, color: number = 0xb8960c, tag: string = 'isMeasure') => {
    if (!threeRef.current || !sceneRef.current) return;
    const THREE = threeRef.current;
    const geom = new THREE.BufferGeometry().setFromPoints([p1, p2]);
    const line = new THREE.Line(geom, new THREE.LineBasicMaterial({ color, linewidth: 2 }));
    line.userData[tag] = true;
    sceneRef.current.add(line);
  }, []);

  // ── Canvas click handler ──
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (toolMode === 'none') return;
    const hit = raycast(e);
    if (!hit) return;

    const rect = canvasRef.current!.getBoundingClientRect();

    if (toolMode === 'annotate') {
      const label = prompt('Enter dimension label (e.g. "36 in"):');
      if (label) {
        setAnnotations(prev => [...prev, { x: e.clientX - rect.left, y: e.clientY - rect.top, label }]);
      }
      return;
    }

    if (toolMode === 'calibrate') {
      if (calibratePoints.length === 0) {
        setCalibratePoints([hit.point.clone()]);
        addMarker(hit.point, 0x2563eb, 'isMeasure');
      } else {
        const p1 = calibratePoints[0];
        const p2 = hit.point.clone();
        addMarker(p2, 0x2563eb, 'isMeasure');
        addLine(p1, p2, 0x2563eb, 'isMeasure');
        const dist = p1.distanceTo(p2);
        setCalibDistRaw(dist);
        setCalibratePoints([]);
        setShowCalibDialog(true);
      }
      return;
    }

    if (toolMode === 'measure') {
      if (measurePoints.length === 0) {
        setMeasurePoints([hit.point.clone()]);
        addMarker(hit.point);
      } else {
        const p1 = measurePoints[0];
        const p2 = hit.point.clone();
        addMarker(p2);
        addLine(p1, p2);
        const dist = p1.distanceTo(p2);
        setMeasurements(prev => [...prev, {
          p1, p2, distRaw: Math.round(dist * 1000) / 1000,
          label: `Measurement #${prev.length + 1}`,
        }]);
        setMeasurePoints([]);
      }
      return;
    }

    if (toolMode === 'treatment') {
      const pt = hit.point.clone();

      if (treatmentShape === 'rectangle') {
        // Rectangle: 2 opposite corners
        addMarker(pt, 0xb8960c, 'isTreatment');
        const newCorners = [...rectCorners, pt];
        setRectCorners(newCorners);
        if (newCorners.length === 2) {
          const [c1, c2] = newCorners;
          const THREE = threeRef.current;
          if (THREE && sceneRef.current) {
            const c3 = new THREE.Vector3(c2.x, c1.y, c2.z);
            const c4 = new THREE.Vector3(c1.x, c2.y, c1.z);
            const corners = [c1, c3, c2, c4];
            corners.forEach((c, i) => addLine(c, corners[(i + 1) % 4], 0xb8960c, 'isTreatment'));
            // Fill
            const shape = new THREE.Shape();
            const pts2d = corners.map((p: any) => new THREE.Vector2(p.x, p.z));
            shape.setFromPoints(pts2d);
            const geom = new THREE.ShapeGeometry(shape);
            const mat = new THREE.MeshBasicMaterial({ color: 0xb8960c, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
            const mesh = new THREE.Mesh(geom, mat);
            mesh.rotation.x = -Math.PI / 2;
            mesh.position.y = c1.y + 0.01;
            mesh.userData.isTreatment = true;
            sceneRef.current.add(mesh);
          }
          const wRaw = Math.abs(c2.x - c1.x) || Math.abs(c2.z - c1.z);
          const hRaw = Math.abs(c2.y - c1.y) || Math.abs(c2.z - c1.z);
          const label = treatmentLabel.trim() || `Treatment Area ${treatmentAreas.length + 1}`;
          addTreatmentArea({ id: Date.now().toString(), label, points: newCorners, widthRaw: wRaw, heightRaw: hRaw });
          setRectCorners([]);
          setTreatmentLabel('');
        }
        return;
      }

      if (treatmentShape === 'arch') {
        addMarker(pt, 0xb8960c, 'isTreatment');
        if (!archCenter) {
          // First click = base center of the arch
          setArchCenter(pt);
        } else {
          // Second click = edge point (determines radius)
          const THREE = threeRef.current;
          if (THREE && sceneRef.current) {
            const radius = archCenter.distanceTo(pt);
            // Draw arch as a semicircle in the vertical plane facing the camera
            const segments = 32;
            const archPts: any[] = [];
            for (let i = 0; i <= segments; i++) {
              const angle = (Math.PI * i) / segments; // 0 to PI (semicircle)
              const dx = Math.cos(angle) * radius;
              const dy = Math.sin(angle) * radius;
              archPts.push(new THREE.Vector3(archCenter.x + dx, archCenter.y + dy, archCenter.z));
            }
            // Close the bottom
            archPts.push(archPts[0].clone());
            // Draw lines
            for (let i = 0; i < archPts.length - 1; i++) {
              addLine(archPts[i], archPts[i + 1], 0xb8960c, 'isTreatment');
            }
            // Fill — project to shape in x-y plane
            const shape = new THREE.Shape();
            shape.moveTo(archPts[0].x - archCenter.x, 0);
            for (let i = 0; i <= segments; i++) {
              const angle = (Math.PI * i) / segments;
              shape.lineTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
            }
            shape.lineTo(-radius, 0);
            const geom = new THREE.ShapeGeometry(shape);
            const mat = new THREE.MeshBasicMaterial({ color: 0xb8960c, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
            const mesh = new THREE.Mesh(geom, mat);
            mesh.position.copy(archCenter);
            mesh.userData.isTreatment = true;
            sceneRef.current.add(mesh);

            const wRaw = radius * 2;
            const hRaw = radius;
            const label = treatmentLabel.trim() || `Arch ${treatmentAreas.length + 1}`;
            addTreatmentArea({ id: Date.now().toString(), label, points: [archCenter, pt], widthRaw: wRaw, heightRaw: hRaw });
          }
          setArchCenter(null);
          setTreatmentLabel('');
        }
        return;
      }

      if (treatmentShape === 'curve') {
        // Bezier curve mode: collect control points, finish on double-click
        addMarker(pt, 0xb8960c, 'isTreatment');
        const newPts = [...currentTreatmentPts, pt];
        setCurrentTreatmentPts(newPts);
        if (newPts.length > 1) {
          addLine(newPts[newPts.length - 2], pt, 0xb8960c, 'isTreatment');
        }
        return;
      }

      // Default: polygon mode
      addMarker(pt, 0xb8960c, 'isTreatment');
      const newPts = [...currentTreatmentPts, pt];
      setCurrentTreatmentPts(newPts);
      if (newPts.length > 1) {
        addLine(newPts[newPts.length - 2], pt, 0xb8960c, 'isTreatment');
      }
    }
  }, [toolMode, treatmentShape, measurePoints, calibratePoints, currentTreatmentPts, rectCorners, archCenter, raycast, addMarker, addLine, addTreatmentArea, treatmentAreas, treatmentLabel]);

  // ── Double-click to finish treatment area (polygon or curve) ──
  const handleDoubleClick = useCallback(() => {
    if (toolMode !== 'treatment' || currentTreatmentPts.length < 3) return;

    const THREE = threeRef.current;
    if (!THREE || !sceneRef.current) return;

    if (treatmentShape === 'curve') {
      // Generate smooth bezier curve through control points
      const curve = new THREE.CatmullRomCurve3(currentTreatmentPts, true, 'catmullrom', 0.5);
      const curvePoints = curve.getPoints(64);

      // Draw the smooth curve
      for (let i = 0; i < curvePoints.length - 1; i++) {
        addLine(curvePoints[i], curvePoints[i + 1], 0xb8960c, 'isTreatment');
      }

      // Fill with shape
      const shape = new THREE.Shape();
      const pts2d = curvePoints.map((p: any) => new THREE.Vector2(p.x, p.z));
      shape.setFromPoints(pts2d);
      const geom = new THREE.ShapeGeometry(shape);
      const mat = new THREE.MeshBasicMaterial({ color: 0xb8960c, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.y = currentTreatmentPts[0].y + 0.01;
      mesh.userData.isTreatment = true;
      sceneRef.current.add(mesh);

      // Bounding box from curve points
      const xs = curvePoints.map((p: any) => p.x);
      const ys = curvePoints.map((p: any) => p.y);
      const zs = curvePoints.map((p: any) => p.z);
      const wRaw = Math.max(...xs) - Math.min(...xs);
      const hRaw = Math.max(...ys) - Math.min(...ys) || Math.max(...zs) - Math.min(...zs);

      const label = treatmentLabel.trim() || `Curved Area ${treatmentAreas.length + 1}`;
      addTreatmentArea({ id: Date.now().toString(), label, points: [...currentTreatmentPts], widthRaw: wRaw, heightRaw: hRaw });
    } else {
      // Polygon mode: close and fill
      addLine(currentTreatmentPts[currentTreatmentPts.length - 1], currentTreatmentPts[0], 0xb8960c, 'isTreatment');

      const shape = new THREE.Shape();
      const pts2d = currentTreatmentPts.map((p: any) => new THREE.Vector2(p.x, p.z));
      shape.setFromPoints(pts2d);
      const geom = new THREE.ShapeGeometry(shape);
      const mat = new THREE.MeshBasicMaterial({ color: 0xb8960c, transparent: true, opacity: 0.25, side: THREE.DoubleSide });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.y = currentTreatmentPts[0].y + 0.01;
      mesh.userData.isTreatment = true;
      sceneRef.current.add(mesh);

      const xs = currentTreatmentPts.map((p: any) => p.x);
      const ys = currentTreatmentPts.map((p: any) => p.y);
      const zs = currentTreatmentPts.map((p: any) => p.z);
      const wRaw = Math.max(...xs) - Math.min(...xs);
      const hRaw = Math.max(...ys) - Math.min(...ys) || Math.max(...zs) - Math.min(...zs);

      const label = treatmentLabel.trim() || `Treatment Area ${treatmentAreas.length + 1}`;
      addTreatmentArea({ id: Date.now().toString(), label, points: [...currentTreatmentPts], widthRaw: wRaw, heightRaw: hRaw });
    }

    setCurrentTreatmentPts([]);
    setTreatmentLabel('');
  }, [toolMode, treatmentShape, currentTreatmentPts, treatmentLabel, treatmentAreas, addLine, addTreatmentArea]);

  // ── Apply calibration ──
  const applyCalibration = () => {
    const inches = parseFloat(calibInches);
    if (!inches || !calibDistRaw) return;
    const factor = inches / calibDistRaw;
    setScaleFactor(factor);
    setShowCalibDialog(false);
    setCalibInches('');
  };

  // ── Reset view ──
  const resetView = () => {
    if (!cameraRef.current || !controlsRef.current || !modelRef.current || !threeRef.current) return;
    const THREE = threeRef.current;
    const box = new THREE.Box3().setFromObject(modelRef.current);
    const size = box.getSize(new THREE.Vector3());
    const dist = Math.max(size.x, size.y, size.z) * 2;
    cameraRef.current.position.set(dist * 0.8, dist * 0.6, dist * 0.8);
    controlsRef.current.target.copy(box.getCenter(new THREE.Vector3()));
    controlsRef.current.update();
    // Clear scene markers
    if (sceneRef.current) {
      const toRemove = sceneRef.current.children.filter((c: any) => c.userData?.isMeasure || c.userData?.isTreatment);
      toRemove.forEach((c: any) => sceneRef.current.remove(c));
    }
    setMeasurements([]);
    setMeasurePoints([]);
    setAnnotations([]);
    setTreatmentAreas([]);
    setCurrentTreatmentPts([]);
    setArchCenter(null);
    setRectCorners([]);
  };

  // ── Capture ──
  const captureView = () => {
    if (!canvasRef.current) return;
    const dataUrl = canvasRef.current.toDataURL('image/png');
    if (onCapture) onCapture(dataUrl);
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = `3d-capture-${Date.now()}.png`;
    a.click();
  };

  // ── Export all data ──
  const exportData = () => {
    if (!canvasRef.current || !onExportData) return;
    const screenshot = canvasRef.current.toDataURL('image/png');
    onExportData({
      measurements: measurements.map(m => ({
        label: m.label,
        value_inches: toInches(m.distRaw) || m.distRaw,
        calibrated: scaleFactor !== null,
      })),
      treatmentAreas: treatmentAreas.map(ta => ({
        label: ta.label,
        width_inches: toInches(ta.widthRaw) || ta.widthRaw,
        height_inches: toInches(ta.heightRaw) || ta.heightRaw,
      })),
      scaleFactor,
      screenshot,
    });
  };

  // ── Delete selected area ──
  const deleteSelectedArea = useCallback(() => {
    if (!selectedAreaId) return;
    deleteTreatmentAreaById(selectedAreaId);
  }, [selectedAreaId, deleteTreatmentAreaById]);

  // ── Undo ──
  const undo = useCallback(() => {
    if (undoStack.length === 0) return;
    const action = undoStack[undoStack.length - 1];
    setUndoStack(prev => prev.slice(0, -1));
    setRedoStack(prev => [...prev, action]);

    switch (action.type) {
      case 'add_area':
        setTreatmentAreas(prev => prev.filter(a => a.id !== action.area.id));
        break;
      case 'delete_area':
        setTreatmentAreas(prev => {
          const next = [...prev];
          next.splice(action.index, 0, action.area);
          return next;
        });
        break;
      case 'edit_area':
        setTreatmentAreas(prev => prev.map(a => a.id === action.id ? action.prev : a));
        break;
      case 'add_measurement':
        setMeasurements(prev => prev.filter(m => m !== action.measurement));
        break;
      case 'delete_measurement':
        setMeasurements(prev => {
          const next = [...prev];
          next.splice(action.index, 0, action.measurement);
          return next;
        });
        break;
    }
  }, [undoStack]);

  // ── Redo ──
  const redo = useCallback(() => {
    if (redoStack.length === 0) return;
    const action = redoStack[redoStack.length - 1];
    setRedoStack(prev => prev.slice(0, -1));
    setUndoStack(prev => [...prev, action]);

    switch (action.type) {
      case 'add_area':
        setTreatmentAreas(prev => [...prev, action.area]);
        break;
      case 'delete_area':
        setTreatmentAreas(prev => prev.filter(a => a.id !== action.area.id));
        break;
      case 'edit_area':
        setTreatmentAreas(prev => prev.map(a => a.id === action.id ? action.next : a));
        break;
      case 'add_measurement':
        setMeasurements(prev => [...prev, action.measurement]);
        break;
      case 'delete_measurement':
        setMeasurements(prev => prev.filter(m => m !== action.measurement));
        break;
    }
  }, [redoStack]);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      // Delete/Backspace: remove selected area
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedAreaId) {
        e.preventDefault();
        deleteSelectedArea();
      }
      // Ctrl+Z: undo
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      // Ctrl+Shift+Z or Ctrl+Y: redo
      if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
        e.preventDefault();
        redo();
      }
      // Escape: deselect
      if (e.key === 'Escape') {
        setSelectedAreaId(null);
        setExpandedAreaId(null);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [selectedAreaId, deleteSelectedArea, undo, redo]);

  // ── Cursor ──
  const cursor = toolMode === 'none' ? 'grab' : 'crosshair';

  // ── Toolbar button helper ──
  const TBtn = ({ active, color, onClick, children }: { active: boolean; color: string; onClick: () => void; children: React.ReactNode }) => (
    <button onClick={onClick}
      className="flex items-center gap-1.5 cursor-pointer transition-all"
      style={{
        padding: '8px 14px', borderRadius: 10, fontSize: 11, fontWeight: 600,
        border: `1.5px solid ${active ? color : '#ece8e0'}`,
        background: active ? `${color}15` : '#faf9f7',
        color: active ? color : '#777',
        minHeight: 44,
      }}>
      {children}
    </button>
  );

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Toolbar row 1 */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 6, flexWrap: 'wrap' }}>
        <TBtn active={toolMode === 'measure'} color="#b8960c" onClick={() => activateTool('measure')}>
          <Ruler size={14} /> {toolMode === 'measure' ? (measurePoints.length === 1 ? 'Click 2nd point...' : 'Measuring') : 'Measure'}
        </TBtn>
        <TBtn active={toolMode === 'calibrate'} color="#2563eb" onClick={() => activateTool('calibrate')}>
          <Crosshair size={14} /> {scaleFactor ? 'Re-calibrate' : 'Calibrate'}
        </TBtn>
        <TBtn active={toolMode === 'treatment'} color="#7c3aed" onClick={() => activateTool('treatment')}>
          <Scissors size={14} /> Treatment Area
        </TBtn>
        <TBtn active={toolMode === 'annotate'} color="#16a34a" onClick={() => activateTool('annotate')}>
          <Tag size={14} /> Annotate
        </TBtn>
      </div>
      {/* Toolbar row 2 */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {undoStack.length > 0 && (
          <TBtn active={false} color="#555" onClick={undo}>
            <Undo2 size={14} /> Undo
          </TBtn>
        )}
        {redoStack.length > 0 && (
          <TBtn active={false} color="#555" onClick={redo}>
            <Redo2 size={14} /> Redo
          </TBtn>
        )}
        <TBtn active={false} color="#777" onClick={resetView}>
          <RotateCcw size={14} /> Reset View
        </TBtn>
        <TBtn active={false} color="#777" onClick={captureView}>
          <Camera size={14} /> Capture
        </TBtn>
        {onExportData && (measurements.length > 0 || treatmentAreas.length > 0) && (
          <TBtn active={false} color="#b8960c" onClick={exportData}>
            <FileText size={14} /> Export to Quote
          </TBtn>
        )}
        {/* Calibration status */}
        {scaleFactor !== null && (
          <span style={{ fontSize: 10, fontWeight: 600, color: '#16a34a', background: '#f0fdf4', padding: '6px 10px', borderRadius: 8, border: '1px solid #bbf7d0', display: 'flex', alignItems: 'center', gap: 4 }}>
            <CheckCircle size={11} /> Scale: 1 unit = {Math.round(scaleFactor * 10) / 10}"
          </span>
        )}
      </div>

      {/* Treatment area controls */}
      {toolMode === 'treatment' && (
        <div style={{ marginBottom: 8 }}>
          {/* Shape mode selector */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
            {([
              { key: 'polygon' as TreatmentShape, label: 'Polygon', icon: <Pentagon size={12} /> },
              { key: 'rectangle' as TreatmentShape, label: 'Rectangle', icon: <Square size={12} /> },
              { key: 'curve' as TreatmentShape, label: 'Curve', icon: <Spline size={12} /> },
              { key: 'arch' as TreatmentShape, label: 'Arch', icon: <Circle size={12} /> },
            ]).map(s => (
              <button key={s.key}
                onClick={() => { setTreatmentShape(s.key); setCurrentTreatmentPts([]); setArchCenter(null); setRectCorners([]); }}
                className="flex items-center gap-1 cursor-pointer transition-all"
                style={{
                  padding: '5px 10px', borderRadius: 8, fontSize: 10, fontWeight: 600,
                  border: `1.5px solid ${treatmentShape === s.key ? '#7c3aed' : '#ece8e0'}`,
                  background: treatmentShape === s.key ? '#7c3aed15' : '#faf9f7',
                  color: treatmentShape === s.key ? '#7c3aed' : '#999',
                }}>
                {s.icon} {s.label}
              </button>
            ))}
          </div>
          {/* Label + finish controls */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              value={treatmentLabel}
              onChange={e => setTreatmentLabel(e.target.value)}
              placeholder={treatmentShape === 'arch' ? 'Label (e.g. Arched Window)' : 'Label (e.g. Living Room Window 1)'}
              style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, background: '#faf9f7' }}
            />
            {(treatmentShape === 'polygon' || treatmentShape === 'curve') && currentTreatmentPts.length >= 3 && (
              <button onClick={handleDoubleClick}
                className="flex items-center gap-1.5 cursor-pointer transition-all hover:brightness-110"
                style={{ padding: '8px 14px', borderRadius: 8, background: '#7c3aed', color: '#fff', fontSize: 11, fontWeight: 700, border: 'none', minHeight: 36 }}>
                <CheckCircle size={12} /> Finish {treatmentShape === 'curve' ? 'Curve' : 'Area'} ({currentTreatmentPts.length} pts)
              </button>
            )}
            <span style={{ fontSize: 10, color: '#999', whiteSpace: 'nowrap' }}>
              {treatmentShape === 'rectangle' ? (rectCorners.length === 0 ? 'Click first corner' : 'Click opposite corner') :
               treatmentShape === 'arch' ? (archCenter ? 'Click edge point for radius' : 'Click center of arch base') :
               treatmentShape === 'curve' ? (currentTreatmentPts.length === 0 ? 'Click points along curve path' : `${currentTreatmentPts.length} pts — double-click to finish`) :
               currentTreatmentPts.length === 0 ? 'Click corners on the model' : `${currentTreatmentPts.length} point${currentTreatmentPts.length !== 1 ? 's' : ''} placed`}
            </span>
          </div>
        </div>
      )}

      {/* Viewer */}
      <div ref={containerRef} style={{ position: 'relative', borderRadius: 14, overflow: 'hidden', border: '2px solid #16a34a', background: '#f5f3ef', width: '100%', height }}>
        <canvas ref={canvasRef} onClick={handleCanvasClick} onDoubleClick={handleDoubleClick}
          style={{ width: '100%', height: '100%', cursor }} />

        {!ready && !loadError && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(245,243,239,0.9)' }}>
            <Loader2 size={28} className="animate-spin" style={{ color: '#16a34a' }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: '#555', marginTop: 10 }}>Loading 3D model...</div>
          </div>
        )}

        {loadError && (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(245,243,239,0.95)' }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#dc2626', marginBottom: 4 }}>Failed to load model</div>
            <div style={{ fontSize: 12, color: '#777', maxWidth: 300, textAlign: 'center' }}>{loadError}</div>
          </div>
        )}

        {/* Annotations */}
        {annotations.map((ann, i) => (
          <div key={i} style={{ position: 'absolute', left: ann.x - 4, top: ann.y - 4, pointerEvents: 'none' }}>
            <div style={{ background: '#b8960c', color: '#fff', fontSize: 10, fontWeight: 700, padding: '3px 8px', borderRadius: 6, whiteSpace: 'nowrap', transform: 'translate(-50%, -120%)', boxShadow: '0 2px 6px rgba(0,0,0,0.2)' }}>
              {ann.label}
            </div>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#b8960c', border: '2px solid #fff', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }} />
          </div>
        ))}

        {/* Status bar */}
        {ready && (
          <div style={{ position: 'absolute', bottom: 8, left: 8, right: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(4px)', fontSize: 10, color: '#777' }}>
            <span>
              {toolMode === 'calibrate' ? 'Click two points on a known measurement to calibrate scale' :
               toolMode === 'treatment' && treatmentShape === 'rectangle' ? 'Click two opposite corners to create rectangle' :
               toolMode === 'treatment' && treatmentShape === 'arch' ? 'Click base center, then edge point for radius' :
               toolMode === 'treatment' && treatmentShape === 'curve' ? 'Click points along curve · Double-click to close smooth shape' :
               toolMode === 'treatment' ? 'Click corners to outline treatment area · Double-click or Finish to close' :
               toolMode === 'measure' ? (measurePoints.length === 1 ? 'Click the second point' : 'Click two points to measure distance') :
               'Drag to rotate · Scroll to zoom · Right-click to pan'}
            </span>
            <span style={{ fontWeight: 700, color: '#b8960c' }}>
              {measurements.length > 0 && `${measurements.length} meas`}
              {measurements.length > 0 && treatmentAreas.length > 0 && ' · '}
              {treatmentAreas.length > 0 && `${treatmentAreas.length} area${treatmentAreas.length !== 1 ? 's' : ''}`}
            </span>
          </div>
        )}
      </div>

      {/* ── Calibration Dialog ── */}
      {showCalibDialog && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setShowCalibDialog(false)}>
          <div onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: 16, padding: 24, width: 380, boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Calibrate Scale</div>
            <div style={{ fontSize: 12, color: '#777', marginBottom: 16 }}>
              You measured {Math.round(calibDistRaw * 1000) / 1000} scene units. What is the real distance?
            </div>

            {/* Presets */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
              {CALIBRATION_PRESETS.filter(p => p.inches > 0).map(preset => (
                <button key={preset.label} onClick={() => setCalibInches(String(preset.inches))}
                  className="cursor-pointer transition-all hover:border-[#2563eb]"
                  style={{
                    padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                    border: `1px solid ${calibInches === String(preset.inches) ? '#2563eb' : '#ece8e0'}`,
                    background: calibInches === String(preset.inches) ? '#eff6ff' : '#faf9f7',
                    color: calibInches === String(preset.inches) ? '#2563eb' : '#555',
                  }}>
                  {preset.label} ({preset.inches}")
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <input
                type="number"
                value={calibInches}
                onChange={e => setCalibInches(e.target.value)}
                placeholder="Distance in inches"
                autoFocus
                style={{ flex: 1, padding: '12px 14px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, background: '#faf9f7', minHeight: 44 }}
              />
              <span style={{ fontSize: 14, fontWeight: 600, color: '#555' }}>inches</span>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={applyCalibration}
                disabled={!calibInches || parseFloat(calibInches) <= 0}
                className="flex-1 flex items-center justify-center gap-2 cursor-pointer transition-all hover:brightness-110 disabled:opacity-50"
                style={{ padding: '12px 20px', borderRadius: 10, background: '#2563eb', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
                <CheckCircle size={16} /> Apply Calibration
              </button>
              <button onClick={() => setShowCalibDialog(false)}
                className="cursor-pointer transition-all hover:bg-[#f0ede8]"
                style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 13, fontWeight: 600, color: '#777', minHeight: 48 }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Measurements list ── */}
      {measurements.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
            Measurements {scaleFactor ? '(calibrated)' : '(uncalibrated — use Calibrate tool)'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {measurements.map((m, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderRadius: 8, background: '#fdf8eb', border: '1px solid #f5ecd0', fontSize: 12 }}>
                <Ruler size={12} style={{ color: '#b8960c', flexShrink: 0 }} />
                <span style={{ fontWeight: 600, color: '#1a1a1a' }}>
                  {formatDist(m.distRaw)}
                </span>
                <span style={{ color: '#999', fontSize: 11, flex: 1 }}>{m.label}</span>
                <button onClick={() => {
                    pushUndo({ type: 'delete_measurement', measurement: m, index: i });
                    setMeasurements(prev => prev.filter((_, idx) => idx !== i));
                  }}
                  className="cursor-pointer hover:text-[#dc2626] transition-colors"
                  style={{ background: 'none', border: 'none', color: '#ccc', padding: 2 }}>
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Treatment Areas list ── */}
      {treatmentAreas.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
            Treatment Areas ({treatmentAreas.length})
            {selectedAreaId && <span style={{ color: '#999', fontWeight: 400, marginLeft: 6 }}>Press Delete to remove selected</span>}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {treatmentAreas.map((ta) => {
              const isSelected = selectedAreaId === ta.id;
              const isExpanded = expandedAreaId === ta.id;
              return (
                <div key={ta.id}>
                  <div
                    onClick={() => {
                      setSelectedAreaId(isSelected ? null : ta.id);
                      if (!isSelected) setExpandedAreaId(null);
                    }}
                    className="cursor-pointer transition-all"
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', borderRadius: isExpanded ? '8px 8px 0 0' : 8, fontSize: 12,
                      background: isSelected ? '#ede9fe' : '#faf5ff',
                      border: `1.5px solid ${isSelected ? '#7c3aed' : '#e9d5ff'}`,
                      boxShadow: isSelected ? '0 0 0 2px #7c3aed30' : 'none',
                    }}
                  >
                    <button
                      onClick={(e) => { e.stopPropagation(); setExpandedAreaId(isExpanded ? null : ta.id); setSelectedAreaId(ta.id); }}
                      style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: '#7c3aed' }}
                    >
                      {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </button>
                    <Scissors size={12} style={{ color: '#7c3aed', flexShrink: 0 }} />
                    <div style={{ flex: 1 }}>
                      <span style={{ fontWeight: 600, color: '#1a1a1a' }}>{ta.label}</span>
                      <span style={{ color: '#777', marginLeft: 8, fontSize: 11 }}>
                        {formatDist(ta.widthRaw)} W × {formatDist(ta.heightRaw)} H
                        {scaleFactor && (
                          <> · {Math.round((toInches(ta.widthRaw)! * toInches(ta.heightRaw)!) / 144 * 10) / 10} sq ft</>
                        )}
                      </span>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteTreatmentAreaById(ta.id); }}
                      className="cursor-pointer hover:text-[#dc2626] transition-colors"
                      title="Delete area"
                      style={{ background: 'none', border: 'none', color: isSelected ? '#dc2626' : '#ccc', padding: 2 }}
                    >
                      <X size={12} />
                    </button>
                  </div>
                  {/* Expanded edit panel */}
                  {isExpanded && (
                    <div style={{ padding: '10px 12px', background: '#f8f5ff', border: '1.5px solid #e9d5ff', borderTop: 'none', borderRadius: '0 0 8px 8px' }}>
                      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                        <div style={{ flex: 1 }}>
                          <label style={{ fontSize: 10, fontWeight: 600, color: '#7c3aed', display: 'block', marginBottom: 3 }}>Label</label>
                          <input
                            value={editingLabel || ta.label}
                            onChange={e => setEditingLabel(e.target.value)}
                            onFocus={() => setEditingLabel(ta.label)}
                            onBlur={() => {
                              if (editingLabel && editingLabel !== ta.label) {
                                const prev = { ...ta };
                                const next = { ...ta, label: editingLabel };
                                pushUndo({ type: 'edit_area', id: ta.id, prev, next });
                                setTreatmentAreas(areas => areas.map(a => a.id === ta.id ? next : a));
                              }
                              setEditingLabel('');
                            }}
                            style={{ width: '100%', padding: '6px 10px', borderRadius: 6, border: '1px solid #e9d5ff', fontSize: 12, background: '#fff' }}
                          />
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#777' }}>
                        <span>Width: <strong style={{ color: '#1a1a1a' }}>{formatDist(ta.widthRaw)}</strong></span>
                        <span>Height: <strong style={{ color: '#1a1a1a' }}>{formatDist(ta.heightRaw)}</strong></span>
                        <span>Points: <strong style={{ color: '#1a1a1a' }}>{ta.points.length}</strong></span>
                        {scaleFactor && (
                          <span>Area: <strong style={{ color: '#1a1a1a' }}>{Math.round((toInches(ta.widthRaw)! * toInches(ta.heightRaw)!) / 144 * 10) / 10} sq ft</strong></span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
