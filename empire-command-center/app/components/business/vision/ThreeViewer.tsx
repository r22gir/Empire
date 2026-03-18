'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Ruler, RotateCcw, Camera, Tag, Loader2 } from 'lucide-react';
import type * as THREE_NS from 'three';

interface ThreeViewerProps {
  modelUrl: string;
  width?: number;
  height?: number;
  onCapture?: (dataUrl: string) => void;
}

export default function ThreeViewer({ modelUrl, width = 500, height = 400, onCapture }: ThreeViewerProps) {
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
  const [measuring, setMeasuring] = useState(false);
  const [annotations, setAnnotations] = useState<{ x: number; y: number; label: string }[]>([]);
  const [measurePoints, setMeasurePoints] = useState<any[]>([]);
  const [measurements, setMeasurements] = useState<{ p1: any; p2: any; dist: number }[]>([]);
  const [annotating, setAnnotating] = useState(false);

  // Initialize Three.js scene
  useEffect(() => {
    let disposed = false;

    const init = async () => {
      if (!canvasRef.current) return;

      const THREE = await import('three');
      const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js');
      threeRef.current = THREE;

      // Scene
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xf5f3ef);
      sceneRef.current = scene;

      // Camera
      const camera = new THREE.PerspectiveCamera(50, width / height, 0.01, 1000);
      camera.position.set(3, 2.5, 3);
      cameraRef.current = camera;

      // Renderer
      const renderer = new THREE.WebGLRenderer({
        canvas: canvasRef.current,
        antialias: true,
        preserveDrawingBuffer: true,
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.2;
      rendererRef.current = renderer;

      // Controls
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.minDistance = 0.5;
      controls.maxDistance = 50;
      controlsRef.current = controls;

      // Lighting
      const ambient = new THREE.AmbientLight(0xffffff, 0.6);
      scene.add(ambient);
      const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
      dirLight.position.set(5, 8, 5);
      dirLight.castShadow = true;
      scene.add(dirLight);
      const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
      fillLight.position.set(-3, 2, -3);
      scene.add(fillLight);

      // Grid floor
      const grid = new THREE.GridHelper(10, 20, 0xcccccc, 0xe5e5e5);
      scene.add(grid);

      // Load model
      try {
        // Parse extension: check hash first (e.g. blob:...#.glb), then URL path
        const hashExt = modelUrl.includes('#.') ? modelUrl.split('#.').pop()?.toLowerCase() : null;
        const ext = hashExt || modelUrl.split('.').pop()?.toLowerCase() || 'glb';
        // Strip hash from URL for loaders
        const cleanUrl = modelUrl.split('#')[0];

        let loadedObj: THREE_NS.Object3D | null = null;

        if (ext === 'obj') {
          const { OBJLoader } = await import('three/examples/jsm/loaders/OBJLoader.js');
          const loader = new OBJLoader();
          loadedObj = await new Promise<THREE_NS.Object3D>((resolve, reject) => {
            loader.load(cleanUrl, resolve, undefined, reject);
          });
        } else if (ext === 'ply') {
          const { PLYLoader } = await import('three/examples/jsm/loaders/PLYLoader.js');
          const loader = new PLYLoader();
          const geometry = await new Promise<THREE_NS.BufferGeometry>((resolve, reject) => {
            loader.load(cleanUrl, resolve, undefined, reject);
          });
          geometry.computeVertexNormals();
          const material = new THREE.MeshStandardMaterial({ color: 0xcccccc, flatShading: true });
          loadedObj = new THREE.Mesh(geometry, material);
        } else {
          // Default: try GLTF/GLB
          const { GLTFLoader } = await import('three/examples/jsm/loaders/GLTFLoader.js');
          const loader = new GLTFLoader();
          const gltf = await new Promise<any>((resolve, reject) => {
            loader.load(cleanUrl, resolve, undefined, reject);
          });
          loadedObj = gltf.scene;
        }

        if (disposed || !loadedObj) return;

        // Auto-center and scale
        const box = new THREE.Box3().setFromObject(loadedObj);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = maxDim > 0 ? 3 / maxDim : 1;

        loadedObj.position.sub(center);
        loadedObj.scale.multiplyScalar(scale);
        // Move model so it sits on the grid
        const scaledBox = new THREE.Box3().setFromObject(loadedObj);
        loadedObj.position.y -= scaledBox.min.y;

        scene.add(loadedObj);
        modelRef.current = loadedObj;

        // Fit camera
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

      // Animation loop
      const animate = () => {
        if (disposed) return;
        animFrameRef.current = requestAnimationFrame(animate);
        controls.update();

        // Draw measurement lines
        renderer.render(scene, camera);
      };
      animate();
    };

    init();

    return () => {
      disposed = true;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (rendererRef.current) rendererRef.current.dispose();
      if (controlsRef.current) controlsRef.current.dispose();
    };
  }, [modelUrl, width, height]);

  // Handle clicks for measuring
  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!measuring && !annotating) return;
    if (!canvasRef.current || !cameraRef.current || !sceneRef.current || !threeRef.current) return;

    const THREE = threeRef.current;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(x, y), cameraRef.current);

    const intersects = raycaster.intersectObjects(sceneRef.current.children, true);
    const hit = intersects.find((i: any) => i.object !== modelRef.current?.parent && i.object.type !== 'GridHelper');

    if (!hit) return;

    if (annotating) {
      const label = prompt('Enter dimension label (e.g. "36 in"):');
      if (label) {
        setAnnotations(prev => [...prev, {
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
          label,
        }]);
      }
      return;
    }

    // Measuring mode
    if (measurePoints.length === 0) {
      setMeasurePoints([hit.point.clone()]);
      // Add sphere marker
      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.03, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0xb8960c })
      );
      sphere.position.copy(hit.point);
      sphere.userData.isMeasure = true;
      sceneRef.current.add(sphere);
    } else {
      const p1 = measurePoints[0];
      const p2 = hit.point.clone();
      const dist = p1.distanceTo(p2);

      // Add second sphere
      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.03, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0xb8960c })
      );
      sphere.position.copy(p2);
      sphere.userData.isMeasure = true;
      sceneRef.current.add(sphere);

      // Add line between points
      const lineGeom = new THREE.BufferGeometry().setFromPoints([p1, p2]);
      const lineMat = new THREE.LineBasicMaterial({ color: 0xb8960c, linewidth: 2 });
      const line = new THREE.Line(lineGeom, lineMat);
      line.userData.isMeasure = true;
      sceneRef.current.add(line);

      // The distance in scene units — since we auto-scaled, convert back
      // For now show relative units; real calibration needs a reference object
      setMeasurements(prev => [...prev, { p1, p2, dist: Math.round(dist * 100) / 100 }]);
      setMeasurePoints([]);
    }
  }, [measuring, annotating, measurePoints]);

  const resetView = () => {
    if (!cameraRef.current || !controlsRef.current || !modelRef.current || !threeRef.current) return;
    const THREE = threeRef.current;
    const box = new THREE.Box3().setFromObject(modelRef.current);
    const size = box.getSize(new THREE.Vector3());
    const dist = Math.max(size.x, size.y, size.z) * 2;
    cameraRef.current.position.set(dist * 0.8, dist * 0.6, dist * 0.8);
    controlsRef.current.target.copy(box.getCenter(new THREE.Vector3()));
    controlsRef.current.update();

    // Clear measurement markers
    if (sceneRef.current) {
      const toRemove = sceneRef.current.children.filter((c: any) => c.userData?.isMeasure);
      toRemove.forEach((c: any) => sceneRef.current.remove(c));
    }
    setMeasurements([]);
    setMeasurePoints([]);
    setAnnotations([]);
  };

  const captureView = () => {
    if (!canvasRef.current) return;
    const dataUrl = canvasRef.current.toDataURL('image/png');
    if (onCapture) onCapture(dataUrl);
    // Also trigger download
    const a = document.createElement('a');
    a.href = dataUrl;
    a.download = `3d-capture-${Date.now()}.png`;
    a.click();
  };

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
        <button
          onClick={() => { setMeasuring(!measuring); setAnnotating(false); setMeasurePoints([]); }}
          className="flex items-center gap-1.5 cursor-pointer transition-all"
          style={{
            padding: '8px 14px', borderRadius: 10, fontSize: 11, fontWeight: 600,
            border: `1.5px solid ${measuring ? '#b8960c' : '#ece8e0'}`,
            background: measuring ? '#fdf8eb' : '#faf9f7',
            color: measuring ? '#b8960c' : '#777',
            minHeight: 44,
          }}>
          <Ruler size={14} /> {measuring ? (measurePoints.length === 1 ? 'Click 2nd point...' : 'Measuring...') : 'Measure'}
        </button>
        <button
          onClick={() => { setAnnotating(!annotating); setMeasuring(false); setMeasurePoints([]); }}
          className="flex items-center gap-1.5 cursor-pointer transition-all"
          style={{
            padding: '8px 14px', borderRadius: 10, fontSize: 11, fontWeight: 600,
            border: `1.5px solid ${annotating ? '#2563eb' : '#ece8e0'}`,
            background: annotating ? '#eff6ff' : '#faf9f7',
            color: annotating ? '#2563eb' : '#777',
            minHeight: 44,
          }}>
          <Tag size={14} /> Annotate
        </button>
        <button
          onClick={resetView}
          className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#f0ede8]"
          style={{ padding: '8px 14px', borderRadius: 10, fontSize: 11, fontWeight: 600, border: '1.5px solid #ece8e0', background: '#faf9f7', color: '#777', minHeight: 44 }}>
          <RotateCcw size={14} /> Reset View
        </button>
        <button
          onClick={captureView}
          className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#f0ede8]"
          style={{ padding: '8px 14px', borderRadius: 10, fontSize: 11, fontWeight: 600, border: '1.5px solid #ece8e0', background: '#faf9f7', color: '#777', minHeight: 44 }}>
          <Camera size={14} /> Capture
        </button>
      </div>

      {/* Viewer */}
      <div
        ref={containerRef}
        style={{
          position: 'relative',
          borderRadius: 14,
          overflow: 'hidden',
          border: '2px solid #16a34a',
          background: '#f5f3ef',
          width: '100%',
          height,
        }}>
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          style={{
            width: '100%',
            height: '100%',
            cursor: measuring ? 'crosshair' : annotating ? 'cell' : 'grab',
          }}
        />

        {/* Loading overlay */}
        {!ready && !loadError && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(245,243,239,0.9)',
          }}>
            <Loader2 size={28} className="animate-spin" style={{ color: '#16a34a' }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: '#555', marginTop: 10 }}>Loading 3D model...</div>
          </div>
        )}

        {/* Error overlay */}
        {loadError && (
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(245,243,239,0.95)',
          }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#dc2626', marginBottom: 4 }}>Failed to load model</div>
            <div style={{ fontSize: 12, color: '#777', maxWidth: 300, textAlign: 'center' }}>{loadError}</div>
          </div>
        )}

        {/* Annotation overlays */}
        {annotations.map((ann, i) => (
          <div key={i} style={{
            position: 'absolute', left: ann.x - 4, top: ann.y - 4,
            pointerEvents: 'none',
          }}>
            <div style={{
              background: '#b8960c', color: '#fff', fontSize: 10, fontWeight: 700,
              padding: '3px 8px', borderRadius: 6, whiteSpace: 'nowrap',
              transform: 'translate(-50%, -120%)',
              boxShadow: '0 2px 6px rgba(0,0,0,0.2)',
            }}>
              {ann.label}
            </div>
            <div style={{
              width: 8, height: 8, borderRadius: '50%', background: '#b8960c',
              border: '2px solid #fff', boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
            }} />
          </div>
        ))}

        {/* Status bar */}
        {ready && (
          <div style={{
            position: 'absolute', bottom: 8, left: 8, right: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 12px', borderRadius: 8,
            background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(4px)',
            fontSize: 10, color: '#777',
          }}>
            <span>Drag to rotate · Scroll to zoom · Right-click to pan</span>
            {measurements.length > 0 && (
              <span style={{ fontWeight: 700, color: '#b8960c' }}>
                {measurements.length} measurement{measurements.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Measurement results */}
      {measurements.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
            Measurements
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {measurements.map((m, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px', borderRadius: 8,
                background: '#fdf8eb', border: '1px solid #f5ecd0',
                fontSize: 12,
              }}>
                <Ruler size={12} style={{ color: '#b8960c', flexShrink: 0 }} />
                <span style={{ fontWeight: 600, color: '#1a1a1a' }}>
                  {m.dist} units
                </span>
                <span style={{ color: '#999', fontSize: 11 }}>
                  (point-to-point #{i + 1})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
