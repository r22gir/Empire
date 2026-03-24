'use client';
import { useState } from 'react';
import { API } from '../lib/api';
import { ChevronDown, ChevronUp, X, Loader2 } from 'lucide-react';
import type { Fabric } from './FabricSelector';

interface YardageCalculatorProps {
  fabric: Fabric;
  itemWidth: string;
  itemHeight: string;
  itemDepth: string;
  quantity: number;
  yardsOverride: number | null;
  onYardsCalculated: (yards: number) => void;
  onYardsOverride: (yards: number | null) => void;
}

export default function YardageCalculator({
  fabric, itemWidth, itemHeight, itemDepth, quantity,
  yardsOverride, onYardsCalculated, onYardsOverride,
}: YardageCalculatorProps) {
  const [expanded, setExpanded] = useState(false);
  const [pieceW, setPieceW] = useState(itemWidth || '');
  const [pieceL, setPieceL] = useState(itemHeight || '');
  const [qty, setQty] = useState(String(quantity || 1));
  const [seamAllowance, setSeamAllowance] = useState('1');
  const [wastePct, setWastePct] = useState('10');
  const [fabricWidth, setFabricWidth] = useState(String(fabric.width_inches || 54));
  const [patternRepeat, setPatternRepeat] = useState(String(fabric.pattern_repeat_v || 0));
  const [calculating, setCalculating] = useState(false);
  const [result, setResult] = useState<{ yards: number; breakdown: string } | null>(null);
  const [manualYards, setManualYards] = useState(yardsOverride ? String(yardsOverride) : '');

  const calculate = async () => {
    const w = parseFloat(pieceW);
    const l = parseFloat(pieceL);
    if (!w || !l) return;
    setCalculating(true);
    try {
      const params = new URLSearchParams({
        width_inches: String(w),
        length_inches: String(l),
        quantity: qty || '1',
        fabric_width: fabricWidth || '54',
        pattern_repeat_v: patternRepeat || '0',
        seam_allowance: seamAllowance || '0',
        waste_percent: wastePct || '0',
      });
      const res = await fetch(`${API}/fabrics/calculate-yards?${params}`);
      if (res.ok) {
        const data = await res.json();
        setResult({ yards: data.yards_with_waste, breakdown: data.breakdown });
        onYardsCalculated(data.yards_with_waste);
      }
    } catch {}
    setCalculating(false);
  };

  const handleOverride = (val: string) => {
    setManualYards(val);
    const n = parseFloat(val);
    onYardsOverride(n > 0 ? n : null);
  };

  const clearOverride = () => {
    setManualYards('');
    onYardsOverride(null);
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '7px 8px', borderRadius: 7,
    border: '1.5px solid #ece8e0', fontSize: 11, outline: 'none',
  };
  const labelStyle: React.CSSProperties = {
    fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2,
  };

  return (
    <div style={{ marginTop: 4 }}>
      <button onClick={() => setExpanded(!expanded)}
        className="cursor-pointer transition-all hover:bg-[#faf9f7] w-full"
        style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px',
          borderRadius: 6, border: 'none', background: 'transparent',
          fontSize: 11, fontWeight: 600, color: '#b8960c',
        }}>
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        Yardage Calculator
        {(yardsOverride || result) && (
          <span style={{ color: '#16a34a', fontWeight: 700, marginLeft: 4 }}>
            {yardsOverride ? `${yardsOverride} yd (manual)` : result ? `${result.yards} yd` : ''}
          </span>
        )}
      </button>

      {expanded && (
        <div style={{
          padding: '10px 12px', marginTop: 4,
          border: '1px solid #ece8e0', borderRadius: 10,
          background: '#faf9f7',
        }}>
          <div className="grid grid-cols-4 gap-2">
            <div>
              <label style={labelStyle}>PIECE W&quot;</label>
              <input value={pieceW} onChange={e => setPieceW(e.target.value)}
                placeholder="24" type="number" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>PIECE L&quot;</label>
              <input value={pieceL} onChange={e => setPieceL(e.target.value)}
                placeholder="36" type="number" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>QTY</label>
              <input value={qty} onChange={e => setQty(e.target.value)}
                type="number" min="1" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>SEAM&quot;</label>
              <input value={seamAllowance} onChange={e => setSeamAllowance(e.target.value)}
                type="number" step="0.5" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>FABRIC W&quot;</label>
              <input value={fabricWidth} onChange={e => setFabricWidth(e.target.value)}
                type="number" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>REPEAT V&quot;</label>
              <input value={patternRepeat} onChange={e => setPatternRepeat(e.target.value)}
                type="number" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>WASTE %</label>
              <input value={wastePct} onChange={e => setWastePct(e.target.value)}
                type="number" style={inputStyle} />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button onClick={calculate} disabled={calculating}
                className="cursor-pointer transition-all hover:bg-[#a88508] disabled:opacity-50"
                style={{
                  width: '100%', padding: '7px', borderRadius: 7,
                  border: 'none', background: '#b8960c', color: '#fff',
                  fontSize: 11, fontWeight: 700,
                }}>
                {calculating ? <Loader2 size={12} className="animate-spin mx-auto" /> : 'Calculate'}
              </button>
            </div>
          </div>

          {/* Result */}
          {result && (
            <div style={{
              marginTop: 8, padding: '8px 10px', borderRadius: 8,
              background: '#f0fdf4', border: '1px solid #bbf7d0',
              fontSize: 11, color: '#16a34a',
            }}>
              <span style={{ fontWeight: 700 }}>Calculated: {result.yards} yd</span>
              <div style={{ fontSize: 10, color: '#666', marginTop: 2 }}>{result.breakdown}</div>
            </div>
          )}

          {/* Manual override */}
          <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: '#999', whiteSpace: 'nowrap' }}>Or enter yards:</label>
            <input value={manualYards} onChange={e => handleOverride(e.target.value)}
              type="number" step="0.25" placeholder="0"
              style={{ ...inputStyle, width: 80 }} />
            {yardsOverride && (
              <>
                <span style={{ fontSize: 10, color: '#b8960c', fontWeight: 600 }}>
                  Using: {yardsOverride} yd (manual)
                </span>
                <button onClick={clearOverride}
                  className="cursor-pointer transition-all hover:bg-[#fef2f2]"
                  style={{ width: 20, height: 20, borderRadius: 4, border: '1px solid #fca5a5', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <X size={10} className="text-[#dc2626]" />
                </button>
              </>
            )}
          </div>

          {/* Cost preview (display only) */}
          {fabric.cost_per_yard > 0 && (yardsOverride || result) && (
            <div style={{
              marginTop: 8, padding: '6px 10px', borderRadius: 8,
              background: '#fdf8eb', border: '1px solid #f5ecd0',
              fontSize: 11, color: '#b8960c',
            }}>
              {(() => {
                const yds = yardsOverride || result?.yards || 0;
                const baseCost = yds * fabric.cost_per_yard;
                const withMargin = baseCost * (1 + fabric.margin_percent / 100);
                return (
                  <span>
                    {yds} yd x ${fabric.cost_per_yard.toFixed(2)}/yd = ${baseCost.toFixed(2)}
                    {fabric.margin_percent > 0 && ` + ${fabric.margin_percent}% = $${withMargin.toFixed(2)}`}
                    <span style={{ color: '#999', marginLeft: 6, fontSize: 10 }}>(display only)</span>
                  </span>
                );
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
