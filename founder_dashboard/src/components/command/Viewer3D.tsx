'use client';
import { useState, useEffect, useCallback, Suspense, useRef } from 'react';
import { X, Ruler, Trash2, Loader2 } from 'lucide-react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, useGLTF, Html, GizmoHelper, GizmoViewport } from '@react-three/drei';
import * as THREE from 'three';

interface Props {
  fileUrl: string;
  fileName: string;
  onClose: () => void;
  onMeasurement?: (meters: number, feet: number) => void;
}

interface MeasurePoint {
  position: THREE.Vector3;
}

/* ── GLB Model ──────────────────────────────────────────────── */
function GLBModel({ url, measuring, onPointClick }: {
  url: string;
  measuring: boolean;
  onPointClick: (point: THREE.Vector3) => void;
}) {
  const { scene } = useGLTF(url);
  const ref = useRef<THREE.Group>(null);

  /* Center and scale the model on load */
  useEffect(() => {
    if (!ref.current) return;
    const box = new THREE.Box3().setFromObject(ref.current);
    const center = box.getCenter(new THREE.Vector3());
    ref.current.position.sub(center);
  }, [scene]);

  return (
    <group ref={ref}>
      <primitive
        object={scene}
        onClick={(e: any) => {
          if (!measuring) return;
          e.stopPropagation();
          onPointClick(e.point.clone());
        }}
        style={{ cursor: measuring ? 'crosshair' : 'grab' }}
      />
    </group>
  );
}

/* ── Measurement markers + line ─────────────────────────────── */
function MeasureOverlay({ points, unit }: { points: MeasurePoint[]; unit: 'm' | 'ft' }) {
  if (points.length === 0) return null;

  const distance = points.length === 2
    ? points[0].position.distanceTo(points[1].position)
    : null;

  const displayDist = distance !== null
    ? unit === 'ft' ? (distance * 3.28084).toFixed(2) + ' ft' : distance.toFixed(2) + ' m'
    : null;

  const midpoint = points.length === 2
    ? new THREE.Vector3().addVectors(points[0].position, points[1].position).multiplyScalar(0.5)
    : null;

  return (
    <>
      {/* Point markers */}
      {points.map((p, i) => (
        <mesh key={i} position={p.position}>
          <sphereGeometry args={[0.02, 16, 16]} />
          <meshStandardMaterial color="#D4AF37" emissive="#D4AF37" emissiveIntensity={0.5} />
          <Html center distanceFactor={3}>
            <div style={{
              background: 'rgba(5,5,13,0.85)',
              border: '1px solid rgba(212,175,55,0.4)',
              borderRadius: 6,
              padding: '2px 6px',
              fontSize: 10,
              color: '#D4AF37',
              whiteSpace: 'nowrap',
              pointerEvents: 'none',
            }}>
              {i === 0 ? 'A' : 'B'}
            </div>
          </Html>
        </mesh>
      ))}

      {/* Line between points */}
      {points.length === 2 && (
        <line>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              count={2}
              array={new Float32Array([
                points[0].position.x, points[0].position.y, points[0].position.z,
                points[1].position.x, points[1].position.y, points[1].position.z,
              ])}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#D4AF37" linewidth={2} />
        </line>
      )}

      {/* Distance label at midpoint */}
      {midpoint && displayDist && (
        <Html position={midpoint} center>
          <div style={{
            background: 'rgba(5,5,13,0.9)',
            border: '1px solid rgba(212,175,55,0.5)',
            borderRadius: 8,
            padding: '4px 10px',
            fontSize: 13,
            fontWeight: 700,
            color: '#D4AF37',
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            fontFamily: "'JetBrains Mono', monospace",
          }}>
            {displayDist}
          </div>
        </Html>
      )}
    </>
  );
}

/* ── Auto-fit camera to model ───────────────────────────────── */
function CameraFit({ url }: { url: string }) {
  const { scene: gltfScene } = useGLTF(url);
  const { camera } = useThree();

  useEffect(() => {
    const box = new THREE.Box3().setFromObject(gltfScene);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const dist = maxDim * 2;
    camera.position.set(dist * 0.7, dist * 0.5, dist * 0.7);
    camera.lookAt(0, 0, 0);
  }, [gltfScene, camera]);

  return null;
}

/* ── Loading fallback ───────────────────────────────────────── */
function LoadingFallback() {
  return (
    <Html center>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#D4AF37' }}>
        <Loader2 className="w-5 h-5 animate-spin" />
        <span style={{ fontSize: 13 }}>Loading 3D scan...</span>
      </div>
    </Html>
  );
}

/* ── Main Component ─────────────────────────────────────────── */
export default function Viewer3D({ fileUrl, fileName, onClose, onMeasurement }: Props) {
  const [measuring, setMeasuring] = useState(false);
  const [points, setPoints] = useState<MeasurePoint[]>([]);
  const [unit, setUnit] = useState<'m' | 'ft'>('ft');
  const [error, setError] = useState<string | null>(null);

  /* Escape key closes */
  useEffect(() => {
    const handle = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [onClose]);

  /* Notify parent when measurement completes */
  useEffect(() => {
    if (points.length === 2 && onMeasurement) {
      const m = points[0].position.distanceTo(points[1].position);
      onMeasurement(m, m * 3.28084);
    }
  }, [points, onMeasurement]);

  const handlePointClick = useCallback((point: THREE.Vector3) => {
    setPoints(prev => {
      if (prev.length >= 2) return [{ position: point }]; // Reset and start new
      return [...prev, { position: point }];
    });
  }, []);

  const clearMeasurement = () => setPoints([]);

  const distance = points.length === 2
    ? points[0].position.distanceTo(points[1].position)
    : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(5,5,13,0.95)' }}>
      <div
        className="w-full h-full max-w-6xl max-h-[95vh] mx-4 my-2 flex flex-col rounded-2xl overflow-hidden"
        style={{ background: 'var(--glass-bg-solid, #0a0a1a)', border: '1px solid var(--glass-border)' }}
      >
        {/* Header */}
        <div
          className="shrink-0 px-6 py-3 flex items-center justify-between"
          style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(212,175,55,0.12) 100%)',
            borderBottom: '1px solid var(--glass-border)',
          }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <Ruler className="w-4 h-4 shrink-0" style={{ color: 'var(--purple, #8B5CF6)' }} />
            <div className="min-w-0">
              <h1 className="text-sm font-bold truncate" style={{ color: 'var(--purple, #8B5CF6)' }}>3D Scan Viewer</h1>
              <p className="text-[10px] truncate" style={{ color: 'var(--text-muted)' }}>{fileName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {measuring && (
              <span className="text-[9px] px-2 py-0.5 rounded-full font-medium"
                style={{ background: 'rgba(212,175,55,0.15)', color: '#D4AF37' }}>
                MEASURE MODE — Click two points
              </span>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition"
              style={{ color: 'var(--text-muted)', border: '1px solid var(--glass-border)' }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.15)'; e.currentTarget.style.color = '#ef4444'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 3D Canvas */}
        <div className="flex-1 relative" style={{ cursor: measuring ? 'crosshair' : 'grab' }}>
          {error ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm" style={{ color: '#ef4444' }}>Failed to load 3D model: {error}</p>
            </div>
          ) : (
            <Canvas
              camera={{ position: [3, 2, 3], fov: 50 }}
              onCreated={({ gl }) => { gl.toneMapping = THREE.ACESFilmicToneMapping; gl.toneMappingExposure = 1.2; }}
              style={{ background: '#0a0a14' }}
            >
              <ambientLight intensity={0.6} />
              <directionalLight position={[5, 8, 5]} intensity={1} castShadow />
              <directionalLight position={[-3, 4, -3]} intensity={0.3} />

              <Suspense fallback={<LoadingFallback />}>
                <GLBModel url={fileUrl} measuring={measuring} onPointClick={handlePointClick} />
                <CameraFit url={fileUrl} />
                <MeasureOverlay points={points} unit={unit} />
              </Suspense>

              <gridHelper args={[20, 20, '#222233', '#161622']} position={[0, -0.01, 0]} />
              <OrbitControls enableDamping dampingFactor={0.1} />
              <GizmoHelper alignment="bottom-right" margin={[60, 60]}>
                <GizmoViewport labelColor="white" axisHeadScale={0.8} />
              </GizmoHelper>
            </Canvas>
          )}
        </div>

        {/* Footer */}
        <div
          className="shrink-0 px-6 py-3 flex items-center justify-between"
          style={{ borderTop: '1px solid var(--glass-border)', background: 'var(--raised)' }}
        >
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMeasuring(!measuring)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
              style={{
                background: measuring ? 'rgba(212,175,55,0.2)' : 'var(--elevated)',
                color: measuring ? '#D4AF37' : 'var(--text-primary)',
                border: `1px solid ${measuring ? 'rgba(212,175,55,0.4)' : 'var(--glass-border)'}`,
              }}
            >
              <Ruler className="w-3.5 h-3.5" />
              {measuring ? 'Measuring...' : 'Measure'}
            </button>

            {points.length > 0 && (
              <button
                onClick={clearMeasurement}
                className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
                style={{ background: 'var(--elevated)', color: 'var(--text-primary)', border: '1px solid var(--glass-border)' }}
              >
                <Trash2 className="w-3.5 h-3.5" /> Clear
              </button>
            )}

            <button
              onClick={() => setUnit(u => u === 'm' ? 'ft' : 'm')}
              className="px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition"
              style={{ background: 'var(--elevated)', color: 'var(--cyan, #22D3EE)', border: '1px solid var(--glass-border)' }}
            >
              {unit === 'm' ? 'm → ft' : 'ft → m'}
            </button>
          </div>

          <div className="flex items-center gap-4">
            {distance !== null && (
              <span className="text-sm font-mono font-bold" style={{ color: '#D4AF37' }}>
                {unit === 'ft'
                  ? (distance * 3.28084).toFixed(2) + ' ft'
                  : distance.toFixed(2) + ' m'}
              </span>
            )}
            <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
              3D Viewer
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
