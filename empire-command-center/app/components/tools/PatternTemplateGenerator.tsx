'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import {
  Ruler, Download, RefreshCw, Scissors, Info, Plus, FileText,
} from 'lucide-react';

/* ── Types ───────────────────────────────────────────────────── */
interface ShapeField {
  key: string;
  label: string;
  default: number | boolean | string;
  unit?: string;
  step?: number;
  optional?: boolean;
  type?: 'checkbox';
  options?: (string | number)[];
  showWhen?: string;
}

interface ShapeConfig {
  id: string;
  name: string;
  desc: string;
  icon: string;
  fields: ShapeField[];
}

interface PatternPiece {
  name: string;
  width: number;
  height: number;
  quantity: number;
  notes?: string;
  svg?: string;
}

interface PatternResult {
  pieces: PatternPiece[];
  construction_notes: string[];
  fabric_yardage_54: number;
  summary?: string;
}

/* ── Shape Configs ───────────────────────────────────────────── */
const SHAPES: ShapeConfig[] = [
  {
    id: 'sphere', name: 'Sphere', desc: 'Ball/sphere from gore panels', icon: '⚽',
    fields: [
      { key: 'diameter', label: 'Diameter', default: 9.39, unit: '"', step: 0.25 },
      { key: 'circumference', label: 'OR Circumference', default: 0, unit: '"', step: 0.25, optional: true },
      { key: 'num_gores', label: 'Number of Gores', default: 8, options: [4, 6, 8, 10, 12] },
      { key: 'seam_allowance', label: 'Seam Allowance', default: 0.5, unit: '"', step: 0.125 },
      { key: 'pillow_cover', label: 'Pillow Cover Mode', default: false, type: 'checkbox' },
      { key: 'pillow_reduction', label: 'Reduction for Snug Fit', default: 0.5, unit: '"', step: 0.125, showWhen: 'pillow_cover' },
    ],
  },
  {
    id: 'cylinder', name: 'Bolster', desc: 'Bolster pillows, neckrolls', icon: '🫧',
    fields: [
      { key: 'diameter', label: 'Diameter', default: 6, unit: '"', step: 0.25 },
      { key: 'length', label: 'Length', default: 18, unit: '"', step: 0.5 },
      { key: 'seam_allowance', label: 'Seam Allowance', default: 0.5, unit: '"', step: 0.125 },
      { key: 'end_cap_style', label: 'End Cap Style', default: 'flat', options: ['flat', 'gathered', 'piped'] },
      { key: 'zipper', label: 'Zipper', default: true, type: 'checkbox' },
      { key: 'piping', label: 'Piping', default: false, type: 'checkbox' },
    ],
  },
  {
    id: 'box_cushion', name: 'Box Cushion', desc: 'Seat & bench cushions', icon: '🟫',
    fields: [
      { key: 'width', label: 'Width', default: 20, unit: '"', step: 0.5 },
      { key: 'depth', label: 'Depth', default: 20, unit: '"', step: 0.5 },
      { key: 'thickness', label: 'Thickness (Boxing)', default: 4, unit: '"', step: 0.25 },
      { key: 'seam_allowance', label: 'Seam Allowance', default: 0.5, unit: '"', step: 0.125 },
      { key: 'corner_radius', label: 'Corner Radius', default: 0, unit: '"', step: 0.25 },
      { key: 'zipper_in_back', label: 'Zipper in Back', default: true, type: 'checkbox' },
      { key: 'welt', label: 'Welt/Piping', default: false, type: 'checkbox' },
      { key: 't_cushion', label: 'T-Cushion', default: false, type: 'checkbox' },
      { key: 't_arm_width', label: 'T-Arm Width', default: 6, unit: '"', step: 0.5, showWhen: 't_cushion' },
      { key: 't_arm_depth', label: 'T-Arm Depth', default: 4, unit: '"', step: 0.5, showWhen: 't_cushion' },
    ],
  },
  {
    id: 'knife_edge', name: 'Knife Edge', desc: 'Throw pillows, flat cushions', icon: '💠',
    fields: [
      { key: 'width', label: 'Width', default: 18, unit: '"', step: 0.5 },
      { key: 'height', label: 'Height', default: 18, unit: '"', step: 0.5 },
      { key: 'shape', label: 'Shape', default: 'square', options: ['square', 'rectangle', 'round', 'oval'] },
      { key: 'seam_allowance', label: 'Seam Allowance', default: 0.5, unit: '"', step: 0.125 },
      { key: 'zipper', label: 'Zipper', default: true, type: 'checkbox' },
    ],
  },
];

/* ── Helpers ──────────────────────────────────────────────────── */
function shapeIdToUrl(id: string): string {
  return id.replace(/_/g, '-');
}

function defaultsForShape(shape: ShapeConfig): Record<string, any> {
  const vals: Record<string, any> = {};
  shape.fields.forEach((f) => { vals[f.key] = f.default; });
  return vals;
}

/* ── Component ───────────────────────────────────────────────── */
interface PatternTemplateGeneratorProps {
  onSave?: (shape: string, params: Record<string, any>, result: PatternResult, projectName: string) => void;
}

export default function PatternTemplateGenerator({ onSave }: PatternTemplateGeneratorProps = {}) {
  const [selectedShape, setSelectedShape] = useState<string>('sphere');
  const [formValues, setFormValues] = useState<Record<string, any>>(() =>
    defaultsForShape(SHAPES[0])
  );
  const [projectName, setProjectName] = useState<string>('');
  const [result, setResult] = useState<PatternResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeShape = SHAPES.find((s) => s.id === selectedShape)!;

  /* Reset form when shape changes */
  useEffect(() => {
    const shape = SHAPES.find((s) => s.id === selectedShape);
    if (shape) {
      setFormValues(defaultsForShape(shape));
      setResult(null);
      setError(null);
    }
  }, [selectedShape]);

  /* Field change handler */
  const handleField = useCallback((key: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  /* Generate pattern */
  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API}/patterns/${shapeIdToUrl(selectedShape)}`;
      const body: Record<string, any> = { ...formValues };
      if (projectName.trim()) body.project_name = projectName.trim();

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`API ${res.status}: ${msg}`);
      }
      const data: PatternResult = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'Generation failed');
    } finally {
      setLoading(false);
    }
  }, [selectedShape, formValues, projectName]);

  /* Download PDF */
  const downloadPdf = useCallback(async () => {
    try {
      const url = `${API}/patterns/${shapeIdToUrl(selectedShape)}/pdf`;
      const body: Record<string, any> = { ...formValues };
      if (projectName.trim()) body.project_name = projectName.trim();

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`PDF download failed (${res.status})`);
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `pattern-${shapeIdToUrl(selectedShape)}-${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
    } catch (e: any) {
      setError(e.message || 'PDF download failed');
    }
  }, [selectedShape, formValues, projectName]);

  /* Visible fields (respects showWhen) */
  const visibleFields = activeShape.fields.filter((f) => {
    if (!f.showWhen) return true;
    return !!formValues[f.showWhen];
  });

  return (
    <div className="min-h-screen p-6" style={{ background: '#faf9f7' }}>
      {/* ── Header ────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Scissors className="w-6 h-6" style={{ color: '#b8960c' }} />
          <h1 className="text-2xl font-bold text-gray-900">Pattern Template Generator</h1>
        </div>
        <button
          onClick={() => {
            setResult(null);
            setError(null);
            setFormValues(defaultsForShape(activeShape));
          }}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-[#ece8e0] bg-white
                     hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Reset
        </button>
      </div>

      {/* ── Shape Selector ────────────────────────────────── */}
      <div className="mb-6">
        <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
          Select Shape
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {SHAPES.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedShape(s.id)}
              className={`empire-card p-4 rounded-xl border-2 text-left transition-all ${
                selectedShape === s.id
                  ? 'border-[#b8960c] bg-[#fdf9ef] shadow-md'
                  : 'border-[#ece8e0] bg-white hover:border-[#d4cfc5] hover:shadow-sm'
              }`}
            >
              <div className="text-2xl mb-1">{s.icon}</div>
              <div className="font-semibold text-gray-900 text-sm">{s.name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{s.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Grid: Form + Preview ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Left: Input Form */}
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
            <Ruler className="w-4 h-4" style={{ color: '#b8960c' }} />
            Dimensions &amp; Options
          </div>

          {/* Project Name */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Project Name</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Optional project name..."
              className="w-full px-3 py-2 rounded-xl border border-[#ece8e0] focus:border-[#b8960c]
                         focus:ring-1 focus:ring-[#b8960c] outline-none text-sm transition-colors"
            />
          </div>

          {/* Dynamic Fields */}
          <div className="space-y-3">
            {visibleFields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {field.label}
                  {field.optional && <span className="text-gray-400 ml-1">(optional)</span>}
                  {field.unit && <span className="text-gray-400 ml-1">{field.unit}</span>}
                </label>

                {field.type === 'checkbox' ? (
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!formValues[field.key]}
                      onChange={(e) => handleField(field.key, e.target.checked)}
                      className="w-4 h-4 rounded border-[#ece8e0] text-[#b8960c] focus:ring-[#b8960c]"
                    />
                    <span className="text-sm text-gray-600">Enable</span>
                  </label>
                ) : field.options ? (
                  <select
                    value={formValues[field.key]}
                    onChange={(e) => {
                      const val = field.options!.every((o) => typeof o === 'number')
                        ? Number(e.target.value)
                        : e.target.value;
                      handleField(field.key, val);
                    }}
                    className="w-full px-3 py-2 rounded-xl border border-[#ece8e0] focus:border-[#b8960c]
                               focus:ring-1 focus:ring-[#b8960c] outline-none text-sm bg-white transition-colors"
                  >
                    {field.options.map((opt) => (
                      <option key={String(opt)} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    value={formValues[field.key]}
                    onChange={(e) => handleField(field.key, Number(e.target.value))}
                    step={field.step || 0.25}
                    min={0}
                    className="w-full px-3 py-2 rounded-xl border border-[#ece8e0] focus:border-[#b8960c]
                               focus:ring-1 focus:ring-[#b8960c] outline-none text-sm transition-colors"
                  />
                )}
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={generate}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                         text-white font-medium text-sm transition-all disabled:opacity-50"
              style={{ background: '#b8960c' }}
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Scissors className="w-4 h-4" />
              )}
              {loading ? 'Generating...' : 'Generate Pattern'}
            </button>
            {result && (
              <button
                onClick={downloadPdf}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-[#b8960c]
                           text-[#b8960c] font-medium text-sm hover:bg-[#fdf9ef] transition-colors"
              >
                <Download className="w-4 h-4" />
                PDF
              </button>
            )}
          </div>

          {/* Add to Quote (placeholder) */}
          {result && (
            <button
              className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2 rounded-xl
                         border border-[#ece8e0] text-gray-600 font-medium text-sm
                         hover:bg-gray-50 transition-colors"
              onClick={() => alert('Add to Quote coming soon')}
            >
              <Plus className="w-4 h-4" />
              Add to Quote
            </button>
          )}

          {/* Save Template (when embedded in TemplateModule) */}
          {result && onSave && (
            <button
              className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                         bg-[#16a34a] text-white font-medium text-sm
                         hover:bg-[#15803d] transition-colors"
              onClick={() => onSave(selectedShape, formValues, result, projectName)}
            >
              <FileText className="w-4 h-4" />
              Save as Template
            </button>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start gap-2">
              <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Right: SVG Preview */}
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4" style={{ color: '#b8960c' }} />
            Preview
          </div>

          {result ? (
            <div className="grid grid-cols-2 gap-4">
              {result.pieces.map((piece, i) => (
                <div key={i} className="border border-[#ece8e0] rounded-xl p-3">
                  <div className="text-xs font-semibold text-gray-700 mb-2 text-center">
                    {piece.name} (Cut {piece.quantity})
                  </div>
                  {piece.svg ? (
                    <div
                      className="flex items-center justify-center min-h-[120px]"
                      dangerouslySetInnerHTML={{ __html: piece.svg }}
                    />
                  ) : (
                    <div className="flex items-center justify-center min-h-[120px] text-gray-400 text-xs">
                      No preview
                    </div>
                  )}
                  <div className="text-xs text-gray-500 text-center mt-2">
                    {piece.width}&quot; x {piece.height}&quot;
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center min-h-[300px] text-gray-400">
              <Ruler className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">Select a shape and click Generate</p>
              <p className="text-xs mt-1">SVG pattern previews will appear here</p>
            </div>
          )}
        </div>
      </div>

      {/* ── Construction Notes & Fabric ────────────────────── */}
      {result && (
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5 mb-6">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3 flex items-center gap-2">
            <Info className="w-4 h-4" style={{ color: '#b8960c' }} />
            Construction Notes
          </div>
          <ul className="space-y-1.5 mb-4">
            {result.construction_notes.map((note, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-[#b8960c] mt-0.5">&#8226;</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
          <div className="pt-3 border-t border-[#ece8e0]">
            <span className="text-sm font-semibold text-gray-900">Fabric: </span>
            <span className="kpi-value text-lg font-bold" style={{ color: '#b8960c' }}>
              {result.fabric_yardage_54.toFixed(2)} yards
            </span>
            <span className="text-sm text-gray-500 ml-1">(54&quot; wide)</span>
          </div>
        </div>
      )}

      {/* ── Pieces List ───────────────────────────────────── */}
      {result && (
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
            <Scissors className="w-4 h-4" style={{ color: '#b8960c' }} />
            Pieces
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {result.pieces.map((piece, i) => (
              <div
                key={i}
                className="border border-[#ece8e0] rounded-xl p-3 text-center hover:shadow-sm transition-shadow"
              >
                <div className="font-semibold text-sm text-gray-900">{piece.name}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {piece.width}&quot; x {piece.height}&quot;
                </div>
                <div className="text-xs font-medium mt-1" style={{ color: '#b8960c' }}>
                  Cut {piece.quantity}
                </div>
                {piece.notes && (
                  <div className="text-xs text-gray-400 mt-1 italic">{piece.notes}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
