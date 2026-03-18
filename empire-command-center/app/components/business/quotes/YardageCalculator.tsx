'use client';

import React, { useState, useMemo } from 'react';
import { Calculator, Ruler, X, Copy, Check } from 'lucide-react';

interface YardageResult {
  totalYards: number;
  widths: number;
  fabricCost: number;
  breakdown: string;
}

interface Props {
  onClose?: () => void;
  onApply?: (result: YardageResult) => void;
  compact?: boolean;
}

/**
 * Drapery Yardage Calculator — the $199/mo feature.
 * Calculates fabric yardage for drapery panels based on:
 * - Window width, desired fullness, finished length
 * - Fabric width (54" or 118" standard)
 * - Pattern repeat (if applicable)
 * - Hem and header allowances
 */
export default function YardageCalculator({ onClose, onApply, compact }: Props) {
  const [windowWidth, setWindowWidth] = useState('');
  const [finishedLength, setFinishedLength] = useState('');
  const [fullness, setFullness] = useState('2.5');
  const [fabricWidth, setFabricWidth] = useState('54');
  const [patternRepeat, setPatternRepeat] = useState('');
  const [headerAllowance, setHeaderAllowance] = useState('4');
  const [hemAllowance, setHemAllowance] = useState('8');
  const [fabricPricePerYard, setFabricPricePerYard] = useState('');
  const [panels, setPanels] = useState('2');
  const [copied, setCopied] = useState(false);

  // Service type presets
  const [serviceType, setServiceType] = useState<'drapery' | 'roman' | 'cushion' | 'pillow'>('drapery');

  const result = useMemo<YardageResult | null>(() => {
    const ww = parseFloat(windowWidth);
    const fl = parseFloat(finishedLength);
    const fw = parseFloat(fabricWidth);
    const full = parseFloat(fullness);
    const pr = parseFloat(patternRepeat) || 0;
    const ha = parseFloat(headerAllowance) || 4;
    const hem = parseFloat(hemAllowance) || 8;
    const numPanels = parseInt(panels) || 2;

    if (!ww || !fl || !fw) return null;

    if (serviceType === 'drapery') {
      // Total fabric width needed (including fullness)
      const totalWidth = ww * full;

      // Number of fabric widths needed
      const widths = Math.ceil(totalWidth / fw);

      // Cut length per width (finished length + header + hem)
      let cutLength = fl + ha + hem;

      // Adjust for pattern repeat
      if (pr > 0) {
        cutLength = Math.ceil(cutLength / pr) * pr;
      }

      // Total yardage (widths × cut length, convert inches to yards)
      const totalInches = widths * cutLength;
      const totalYards = Math.ceil((totalInches / 36) * 10) / 10; // round up to 0.1 yard

      const pricePerYard = parseFloat(fabricPricePerYard) || 0;
      const fabricCost = totalYards * pricePerYard;

      const breakdown = [
        `Window: ${ww}" wide × ${fl}" long`,
        `Fullness: ${full}x → ${totalWidth}" total width needed`,
        `Fabric: ${fw}" wide → ${widths} width${widths > 1 ? 's' : ''} needed`,
        `Cut length: ${fl}" + ${ha}" header + ${hem}" hem = ${fl + ha + hem}"`,
        pr > 0 ? `Pattern repeat: ${pr}" → adjusted cut: ${cutLength}"` : null,
        `Total: ${widths} widths × ${cutLength}" = ${totalInches}" → ${totalYards} yards`,
        pricePerYard > 0 ? `Fabric cost: ${totalYards} yd × $${pricePerYard}/yd = $${fabricCost.toFixed(2)}` : null,
      ].filter(Boolean).join('\n');

      return { totalYards, widths, fabricCost, breakdown };
    }

    if (serviceType === 'roman') {
      // Roman shade: width + 6" seam allowance, length + 12"
      const cutWidth = ww + 6;
      const cutLength = fl + 12;
      const totalSqIn = cutWidth * cutLength;
      const totalYards = Math.ceil((cutLength / 36) * 10) / 10;

      // If wider than fabric, need multiple cuts
      const widths = Math.ceil(cutWidth / fw);
      const adjustedYards = totalYards * widths;

      const pricePerYard = parseFloat(fabricPricePerYard) || 0;
      const fabricCost = adjustedYards * pricePerYard;

      const breakdown = [
        `Window: ${ww}" wide × ${fl}" long`,
        `Cut size: ${cutWidth}" × ${cutLength}" (includes seam allowances)`,
        widths > 1 ? `Need ${widths} fabric widths (fabric is ${fw}" wide)` : `Fits in one fabric width (${fw}")`,
        `Total: ${adjustedYards} yards`,
        pricePerYard > 0 ? `Fabric cost: ${adjustedYards} yd × $${pricePerYard}/yd = $${fabricCost.toFixed(2)}` : null,
      ].filter(Boolean).join('\n');

      return { totalYards: adjustedYards, widths, fabricCost, breakdown };
    }

    if (serviceType === 'cushion') {
      // Cushion: top + bottom + boxing strip
      const depth = parseFloat(hemAllowance) || 4; // reuse hem field for depth
      const topBottom = 2 * (ww + 2) * (fl + 2); // 1" seam allowance each side
      const boxing = 2 * ((ww + 2) + (fl + 2)) * (depth + 1);
      const totalSqIn = topBottom + boxing;
      const totalYards = Math.ceil((totalSqIn / (fw * 36)) * 10) / 10;

      const pricePerYard = parseFloat(fabricPricePerYard) || 0;
      const fabricCost = totalYards * pricePerYard;

      const breakdown = [
        `Cushion: ${ww}" × ${fl}" × ${depth}" deep`,
        `Top + Bottom: ${topBottom} sq.in`,
        `Boxing: ${boxing} sq.in`,
        `Total area: ${totalSqIn} sq.in → ${totalYards} yards (${fw}" fabric)`,
        pricePerYard > 0 ? `Fabric cost: $${fabricCost.toFixed(2)}` : null,
      ].filter(Boolean).join('\n');

      return { totalYards, widths: 1, fabricCost, breakdown };
    }

    if (serviceType === 'pillow') {
      // Pillow: front + back + welt
      const numP = numPanels;
      const sizeWithSeam = ww + 1; // 0.5" seam each side
      const perPillow = 2 * sizeWithSeam * sizeWithSeam;
      const totalSqIn = perPillow * numP;
      const weltYards = numP * (4 * ww + 4) / 36; // perimeter × qty
      const totalYards = Math.ceil(((totalSqIn / (fw * 36)) + weltYards) * 10) / 10;

      const pricePerYard = parseFloat(fabricPricePerYard) || 0;
      const fabricCost = totalYards * pricePerYard;

      const breakdown = [
        `${numP} pillow${numP > 1 ? 's' : ''}: ${ww}" × ${ww}"`,
        `Per pillow: ${perPillow} sq.in (front + back + seam)`,
        `Welt cord cover: ${weltYards.toFixed(1)} yards`,
        `Total: ${totalYards} yards (${fw}" fabric)`,
        pricePerYard > 0 ? `Fabric cost: $${fabricCost.toFixed(2)}` : null,
      ].filter(Boolean).join('\n');

      return { totalYards, widths: 1, fabricCost, breakdown };
    }

    return null;
  }, [windowWidth, finishedLength, fullness, fabricWidth, patternRepeat, headerAllowance, hemAllowance, fabricPricePerYard, panels, serviceType]);

  const copyBreakdown = () => {
    if (result) {
      navigator.clipboard.writeText(result.breakdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const serviceTypes = [
    { key: 'drapery' as const, label: 'Drapery', color: '#b8960c' },
    { key: 'roman' as const, label: 'Roman Shade', color: '#2563eb' },
    { key: 'cushion' as const, label: 'Cushion', color: '#16a34a' },
    { key: 'pillow' as const, label: 'Pillows', color: '#7c3aed' },
  ];

  return (
    <div style={{
      background: '#fff',
      borderRadius: 16,
      border: '1px solid #ece8e0',
      overflow: 'hidden',
      boxShadow: '0 2px 10px rgba(0,0,0,0.04)',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #ece8e0',
        background: '#fdf8eb',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Calculator size={18} style={{ color: '#b8960c' }} />
          <span style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>Yardage Calculator</span>
        </div>
        {onClose && (
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#999', padding: 4 }}>
            <X size={18} />
          </button>
        )}
      </div>

      <div style={{ padding: '20px' }}>
        {/* Service Type Selector */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {serviceTypes.map(st => (
            <button key={st.key}
              onClick={() => setServiceType(st.key)}
              style={{
                flex: 1,
                padding: '10px 8px',
                borderRadius: 10,
                border: serviceType === st.key ? `2px solid ${st.color}` : '1px solid #ece8e0',
                background: serviceType === st.key ? st.color + '10' : '#faf9f7',
                color: serviceType === st.key ? st.color : '#777',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.15s',
              }}
            >
              {st.label}
            </button>
          ))}
        </div>

        {/* Input Fields */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
          <CalcField
            label={serviceType === 'pillow' ? 'Pillow Size (inches)' : 'Width (inches)'}
            value={windowWidth}
            onChange={setWindowWidth}
            placeholder={serviceType === 'drapery' ? '120' : '36'}
          />
          <CalcField
            label={serviceType === 'pillow' ? 'Quantity' : serviceType === 'cushion' ? 'Depth (inches)' : 'Length (inches)'}
            value={serviceType === 'pillow' ? panels : finishedLength}
            onChange={serviceType === 'pillow' ? setPanels : setFinishedLength}
            placeholder={serviceType === 'drapery' ? '96' : serviceType === 'pillow' ? '4' : '48'}
          />
          {serviceType === 'drapery' && (
            <>
              <CalcField label="Fullness" value={fullness} onChange={setFullness} placeholder="2.5">
                <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                  {['2', '2.5', '3'].map(f => (
                    <button key={f} onClick={() => setFullness(f)}
                      style={{
                        padding: '4px 10px', borderRadius: 6, fontSize: 10, fontWeight: 700,
                        border: fullness === f ? '1.5px solid #b8960c' : '1px solid #ece8e0',
                        background: fullness === f ? '#fdf8eb' : '#faf9f7',
                        color: fullness === f ? '#b8960c' : '#999',
                        cursor: 'pointer',
                      }}>{f}x</button>
                  ))}
                </div>
              </CalcField>
              <CalcField label="Pattern Repeat (inches)" value={patternRepeat} onChange={setPatternRepeat} placeholder="0 (no repeat)" />
            </>
          )}
          <CalcField label="Fabric Width (inches)" value={fabricWidth} onChange={setFabricWidth} placeholder="54">
            <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
              {['48', '54', '60', '118'].map(f => (
                <button key={f} onClick={() => setFabricWidth(f)}
                  style={{
                    padding: '4px 8px', borderRadius: 6, fontSize: 10, fontWeight: 700,
                    border: fabricWidth === f ? '1.5px solid #b8960c' : '1px solid #ece8e0',
                    background: fabricWidth === f ? '#fdf8eb' : '#faf9f7',
                    color: fabricWidth === f ? '#b8960c' : '#999',
                    cursor: 'pointer',
                  }}>{f}"</button>
              ))}
            </div>
          </CalcField>
          <CalcField label="Fabric Price ($/yard)" value={fabricPricePerYard} onChange={setFabricPricePerYard} placeholder="Optional" />
          {serviceType === 'drapery' && (
            <>
              <CalcField label="Header (inches)" value={headerAllowance} onChange={setHeaderAllowance} placeholder="4" />
              <CalcField label="Hem (inches)" value={hemAllowance} onChange={setHemAllowance} placeholder="8" />
            </>
          )}
        </div>

        {/* Result */}
        {result && (
          <div style={{
            padding: 20,
            borderRadius: 12,
            background: '#f0fdf4',
            border: '1.5px solid #bbf7d0',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total Yardage</div>
                <div style={{ fontSize: 32, fontWeight: 800, color: '#16a34a', lineHeight: 1.1 }}>
                  {result.totalYards} <span style={{ fontSize: 16, fontWeight: 600 }}>yards</span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                {result.widths > 1 && (
                  <div style={{ fontSize: 12, color: '#16a34a', fontWeight: 600 }}>{result.widths} widths</div>
                )}
                {result.fabricCost > 0 && (
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#b8960c', marginTop: 4 }}>${result.fabricCost.toFixed(2)}</div>
                )}
              </div>
            </div>

            {/* Breakdown */}
            <div style={{
              padding: 12,
              borderRadius: 8,
              background: '#fff',
              border: '1px solid #dcfce7',
              fontSize: 12,
              color: '#555',
              lineHeight: 1.6,
              whiteSpace: 'pre-line',
              fontFamily: 'monospace',
            }}>
              {result.breakdown}
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <button onClick={copyBreakdown}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '8px 16px', borderRadius: 8,
                  background: '#fff', border: '1px solid #bbf7d0',
                  color: '#16a34a', fontSize: 12, fontWeight: 600,
                  cursor: 'pointer',
                }}>
                {copied ? <Check size={14} /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
              {onApply && (
                <button onClick={() => onApply(result)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '8px 20px', borderRadius: 8,
                    background: '#b8960c', border: 'none',
                    color: '#fff', fontSize: 12, fontWeight: 700,
                    cursor: 'pointer',
                  }}>
                  Apply to Quote
                </button>
              )}
            </div>
          </div>
        )}

        {!result && windowWidth && finishedLength && (
          <div style={{ padding: 16, borderRadius: 12, background: '#faf9f7', border: '1px solid #ece8e0', textAlign: 'center', color: '#999', fontSize: 13 }}>
            Enter dimensions to calculate yardage
          </div>
        )}
      </div>
    </div>
  );
}

function CalcField({ label, value, onChange, placeholder, children }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; children?: React.ReactNode;
}) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#777', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
        {label}
      </label>
      <input
        type="number"
        step="any"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: '100%',
          height: 40,
          padding: '0 12px',
          borderRadius: 8,
          border: '1px solid #ece8e0',
          background: '#faf9f7',
          fontSize: 14,
          color: '#1a1a1a',
          outline: 'none',
          boxSizing: 'border-box',
        }}
      />
      {children}
    </div>
  );
}
