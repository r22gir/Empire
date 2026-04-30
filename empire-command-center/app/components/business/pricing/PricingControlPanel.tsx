/**
 * PricingControlPanel — v10 Pricing Transparency + Approval Gate
 * Phase 1.5 Frontend-only prototype
 *
 * Shows measurement/material/labor assumptions, formula breakdown,
 * and requires explicit founder approval before quote creation.
 */

'use client';

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Shield, AlertTriangle, Check, Edit3, RotateCcw, Info, DollarSign } from 'lucide-react';
import { usePricingAudit } from '../../../hooks/usePricingAudit';

interface OverrideValues {
  width?: number;
  height?: number;
  fabricYards?: number;
  fabricRate?: number;
  laborAmount?: number;
  taxRate?: number;
  depositPercent?: number;
  discountAmount?: number;
  lineItemAmount?: number;
}

interface PricingControlPanelProps {
  // Measurement data from AI
  measureData?: {
    width_inches: number;
    height_inches: number;
    confidence: number;
    window_type: string;
  } | null;
  // Upholstery data from AI
  upholsteryData?: {
    furniture_type: string;
    style: string;
    fabric_yards_plain: number;
    estimated_labor_cost_low: number;
    estimated_labor_cost_high: number;
    confidence: number;
  } | null;
  // Proposal data
  mockupData?: {
    proposals: { tier: string; treatment_type: string; style: string; price_range_low: number; price_range_high: number }[];
    generated_images: { tier: string; url: string }[];
  } | null;
  // Callback when approvals change (to disable/enable Create Quote)
  onApprovalChange?: (measurementsApproved: boolean, pricingApproved: boolean) => void;
  // Callback when overrides change (to update line item payload)
  onOverridesChange?: (overrides: OverrideValues) => void;
  // Current line items being assembled (before POST)
  lineItems?: any[];
  // Disabled state — panel reads this to show disabled styling
  disabled?: boolean;
}

const HARDCODED_FABRIC_RATE = 25; // $25/yd hardcoded in PhotoAnalysisPanel
const DEFAULT_TAX_RATE = 0.06;
const DEFAULT_DEPOSIT_PERCENT = 50;

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 10,
      fontWeight: 700,
      color: '#777',
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
      marginBottom: 6,
      marginTop: 14,
      paddingBottom: 4,
      borderBottom: '1px solid #ece8e0',
    }}>
      {children}
    </div>
  );
}

function FieldRow({ label, value, unit, badge, badgeColor, override, onOverride, isOverridden }: {
  label: string;
  value: string | number | undefined;
  unit?: string;
  badge?: string;
  badgeColor?: string;
  override?: number | string;
  onOverride?: (val: number) => void;
  isOverridden?: boolean;
}) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '5px 0',
      borderBottom: '1px solid #f5f3ef',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 12, color: '#555' }}>{label}</span>
        {badge && (
          <span style={{
            fontSize: 9,
            fontWeight: 700,
            padding: '2px 6px',
            borderRadius: 4,
            background: badgeColor === 'green' ? '#dcfce7' : badgeColor === 'yellow' ? '#fef9c3' : badgeColor === 'blue' ? '#dbeafe' : '#f5f3ef',
            color: badgeColor === 'green' ? '#16a34a' : badgeColor === 'yellow' ? '#854d0e' : badgeColor === 'blue' ? '#1d4ed8' : '#555',
          }}>
            {badge}
          </span>
        )}
        {isOverridden && (
          <span style={{
            fontSize: 9,
            fontWeight: 700,
            padding: '2px 6px',
            borderRadius: 4,
            background: '#fef9c3',
            color: '#854d0e',
          }}>
            Override
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        {override !== undefined && onOverride ? (
          <input
            type="number"
            defaultValue={override}
            onChange={(e) => onOverride(parseFloat(e.target.value) || 0)}
            style={{
              width: 70,
              padding: '3px 6px',
              fontSize: 12,
              border: '1px solid #ece8e0',
              borderRadius: 6,
              background: '#fff',
              color: '#333',
              textAlign: 'right',
            }}
          />
        ) : null}
        <span style={{ fontSize: 12, fontWeight: 600, color: '#333', minWidth: 60, textAlign: 'right' }}>
          {value !== undefined ? (typeof value === 'number' ? (Number.isInteger(value) ? value : value.toFixed(2)) : value) : '—'}
          {unit ? <span style={{ fontSize: 10, color: '#999', marginLeft: 2 }}>{unit}</span> : null}
        </span>
      </div>
    </div>
  );
}

export default function PricingControlPanel({
  measureData,
  upholsteryData,
  mockupData,
  onApprovalChange,
  onOverridesChange,
  lineItems = [],
  disabled = false,
}: PricingControlPanelProps) {
  const {
    currentEntry,
    initAudit,
    recordAiAssumption,
    recordOverride,
    approveMeasurements,
    approvePricing,
    resetApprovals,
    setDimensionsSource,
    recordOverride: _recordOverride,
  } = usePricingAudit();

  // Override state — mirrors what's passed to quote payload
  const [overrides, setOverrides] = useState<OverrideValues>({});

  // Derive display values from AI data or override
  const displayWidth = overrides.width ?? measureData?.width_inches;
  const displayHeight = overrides.height ?? measureData?.height_inches;
  const displayFabricYards = overrides.fabricYards ?? upholsteryData?.fabric_yards_plain;
  const displayFabricRate = overrides.fabricRate ?? HARDCODED_FABRIC_RATE;
  const displayLaborAmount = overrides.laborAmount ?? upholsteryData?.estimated_labor_cost_low ?? 0;

  // Calculate derived values
  const fabricAmount = (displayFabricYards ?? 0) * displayFabricRate;
  const subtotal = useMemo(() => {
    const itemsSubtotal = lineItems.reduce((s: number, i: any) => s + (i.amount || 0), 0);
    return itemsSubtotal + fabricAmount + (displayLaborAmount || 0);
  }, [lineItems, fabricAmount, displayLaborAmount]);

  const taxRate = overrides.taxRate ?? DEFAULT_TAX_RATE;
  const discountAmount = overrides.discountAmount ?? 0;
  const taxAmount = subtotal * taxRate;
  const total = subtotal + taxAmount - discountAmount;
  const depositPercent = overrides.depositPercent ?? DEFAULT_DEPOSIT_PERCENT;
  const depositAmount = total * (depositPercent / 100);
  const balanceDue = total - depositAmount;

  // Approval state
  const [measurementsApproved, setMeasurementsApproved] = useState(false);
  const [pricingApproved, setPricingApproved] = useState(false);

  // Derived flags
  const hasMeasurements = !!(measureData || overrides.width || overrides.height);
  const hasLabor = displayLaborAmount > 0;
  const hasFabric = (displayFabricYards ?? 0) > 0;
  const confidence = measureData?.confidence ?? upholsteryData?.confidence ?? null;
  const isLowConfidence = confidence !== null && confidence < 60;
  const isOverridden = Object.keys(overrides).length > 0;

  // Init audit entry on mount
  useEffect(() => {
    initAudit({
      dimensionsSource: measureData ? 'ai_estimate' : 'unknown',
    });
  }, []);

  // Notify parent of approval state changes
  useEffect(() => {
    onApprovalChange?.(measurementsApproved, pricingApproved);
  }, [measurementsApproved, pricingApproved, onApprovalChange]);

  // Record AI assumptions when data arrives
  useEffect(() => {
    if (measureData) {
      recordAiAssumption('width_inches', measureData.width_inches, measureData.confidence);
      recordAiAssumption('height_inches', measureData.height_inches, measureData.confidence);
    }
  }, [measureData]);

  useEffect(() => {
    if (upholsteryData) {
      recordAiAssumption('fabric_yards_plain', upholsteryData.fabric_yards_plain, upholsteryData.confidence);
      recordAiAssumption('estimated_labor_cost_low', upholsteryData.estimated_labor_cost_low, upholsteryData.confidence);
    }
  }, [upholsteryData]);

  const handleApproveMeasurements = useCallback(() => {
    const next = !measurementsApproved;
    setMeasurementsApproved(next);
    if (next) {
      setDimensionsSource(overrides.width || overrides.height ? 'manual' : 'ai_estimate');
    } else {
      setPricingApproved(false);
    }
  }, [measurementsApproved, overrides, setDimensionsSource]);

  const handleApprovePricing = useCallback(() => {
    const next = !pricingApproved;
    setPricingApproved(next);
    if (next) {
      approvePricing();
    } else {
      resetApprovals();
    }
  }, [pricingApproved, approvePricing, resetApprovals]);

  const handleOverride = useCallback((field: keyof OverrideValues, value: number) => {
    setOverrides(prev => ({ ...prev, [field]: value }));
    const originals: OverrideValues = {
      width: measureData?.width_inches,
      height: measureData?.height_inches,
      fabricYards: upholsteryData?.fabric_yards_plain,
      fabricRate: HARDCODED_FABRIC_RATE,
      laborAmount: upholsteryData?.estimated_labor_cost_low,
      taxRate: DEFAULT_TAX_RATE,
      depositPercent: DEFAULT_DEPOSIT_PERCENT,
      discountAmount: 0,
    };
    recordOverride(field, originals[field] ?? null, value);
    // Invalidate approvals on any change
    setMeasurementsApproved(false);
    setPricingApproved(false);
    onOverridesChange?.({ ...overrides, [field]: value });
  }, [measureData, upholsteryData, recordOverride, onOverridesChange, overrides]);

  const handleReset = useCallback(() => {
    setOverrides({});
    setMeasurementsApproved(false);
    setPricingApproved(false);
    resetApprovals();
  }, [resetApprovals]);

  const canCreateQuote = !disabled && measurementsApproved && pricingApproved && hasMeasurements && subtotal > 0;

  return (
    <div style={{
      border: '1px solid #ece8e0',
      borderRadius: 12,
      background: '#faf9f7',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid #ece8e0',
        background: '#fff',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <Shield size={14} style={{ color: '#b8960c', flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 700, color: '#333' }}>Pricing Review</span>
        {isOverridden && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
            background: '#fef9c3', color: '#854d0e',
          }}>
            Pricing Modified
          </span>
        )}
        {!measurementsApproved && hasMeasurements && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
            background: '#fef9c3', color: '#854d0e',
          }}>
            Needs Review
          </span>
        )}
        {measurementsApproved && !pricingApproved && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
            background: '#dbeafe', color: '#1d4ed8',
          }}>
            Measurements Approved
          </span>
        )}
        {pricingApproved && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
            background: '#dcfce7', color: '#16a34a',
          }}>
            Pricing Approved
          </span>
        )}
      </div>

      <div style={{ padding: '12px 16px' }}>
        {/* ── A. Measurement Assumptions ─────────────────────────── */}
        <SectionHeader>Measurements Used</SectionHeader>
        <FieldRow
          label="Width"
          value={displayWidth}
          unit="in"
          badge={overrides.width ? 'Manual Override' : (measureData ? 'AI Estimate' : '—')}
          badgeColor={overrides.width ? 'yellow' : 'blue'}
          override={overrides.width}
          onOverride={(v) => handleOverride('width', v)}
          isOverridden={!!overrides.width}
        />
        <FieldRow
          label="Height"
          value={displayHeight}
          unit="in"
          badge={overrides.height ? 'Manual Override' : (measureData ? 'AI Estimate' : '—')}
          badgeColor={overrides.height ? 'yellow' : 'blue'}
          override={overrides.height}
          onOverride={(v) => handleOverride('height', v)}
          isOverridden={!!overrides.height}
        />
        {confidence !== null && (
          <FieldRow
            label="AI Confidence"
            value={confidence}
            unit="%"
            badge={isLowConfidence ? 'Low Confidence' : 'OK'}
            badgeColor={isLowConfidence ? 'yellow' : 'green'}
          />
        )}
        {isLowConfidence && (
          <div style={{
            marginTop: 6,
            padding: '6px 10px',
            borderRadius: 6,
            background: '#fef9c3',
            border: '1px solid #fde047',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <AlertTriangle size={12} style={{ color: '#854d0e', flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontWeight: 600, color: '#854d0e' }}>
              AI confidence below 60% — verify measurements with a tape measure before approving.
            </span>
          </div>
        )}

        {/* ── B. Material Assumptions ───────────────────────────── */}
        <SectionHeader>Material + Fabric</SectionHeader>
        <FieldRow
          label="Fabric Yards"
          value={displayFabricYards}
          unit="yd"
          badge={overrides.fabricYards ? 'Manual Override' : 'AI Estimate'}
          badgeColor={overrides.fabricYards ? 'yellow' : undefined}
          override={overrides.fabricYards}
          onOverride={(v) => handleOverride('fabricYards', v)}
          isOverridden={!!overrides.fabricYards}
        />
        <FieldRow
          label="Fabric Rate"
          value={displayFabricRate}
          unit="$/yd"
          badge={overrides.fabricRate ? 'Manual Override' : `Hardcoded $${HARDCODED_FABRIC_RATE}`}
          badgeColor={overrides.fabricRate ? 'yellow' : undefined}
          override={overrides.fabricRate}
          onOverride={(v) => handleOverride('fabricRate', v)}
          isOverridden={!!overrides.fabricRate}
        />
        <FieldRow
          label="Fabric Amount"
          value={fabricAmount}
          unit="$"
        />
        <div style={{ marginTop: 4, padding: '5px 8px', borderRadius: 6, background: '#f5f3ef', fontSize: 10, color: '#777' }}>
          <span style={{ fontFamily: 'monospace' }}>fabric_amount = yards × rate = {displayFabricYards ?? 0} × ${displayFabricRate} = ${fabricAmount.toFixed(2)}</span>
        </div>

        {/* ── C. Labor Assumptions ───────────────────────────────── */}
        <SectionHeader>Labor</SectionHeader>
        {!hasLabor ? (
          <div style={{
            marginTop: 4,
            padding: '6px 10px',
            borderRadius: 6,
            background: '#fef2f2',
            border: '1px solid #fecaca',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <AlertTriangle size={12} style={{ color: '#dc2626', flexShrink: 0 }} />
            <span style={{ fontSize: 10, fontWeight: 600, color: '#dc2626' }}>
              Missing labor — no AI upholstery estimate available. Labor amount is zero.
              Override or explicitly approve to continue.
            </span>
          </div>
        ) : null}
        <FieldRow
          label="Labor Description"
          value={upholsteryData ? `${upholsteryData.furniture_type} — ${upholsteryData.style}` : '—'}
        />
        <FieldRow
          label="Labor Amount"
          value={displayLaborAmount}
          unit="$"
          badge={displayLaborAmount === 0 ? 'Zero/Missing' : (overrides.laborAmount !== undefined ? 'Manual Override' : 'AI Estimate')}
          badgeColor={displayLaborAmount === 0 ? 'yellow' : 'blue'}
          override={overrides.laborAmount}
          onOverride={(v) => handleOverride('laborAmount', v)}
          isOverridden={overrides.laborAmount !== undefined}
        />

        {/* ── D. Tax / Deposit ─────────────────────────────────── */}
        <SectionHeader>Tax + Deposit</SectionHeader>
        <FieldRow
          label="Tax Rate"
          value={(taxRate * 100).toFixed(1)}
          unit="%"
          badge="Hardcoded"
          override={overrides.taxRate !== undefined ? overrides.taxRate * 100 : undefined}
          onOverride={overrides.taxRate !== undefined ? (v) => handleOverride('taxRate', v / 100) : undefined}
        />
        <FieldRow
          label="Discount"
          value={discountAmount}
          unit="$"
          override={overrides.discountAmount}
          onOverride={(v) => handleOverride('discountAmount', v)}
          isOverridden={overrides.discountAmount !== undefined}
        />
        <FieldRow
          label="Deposit %"
          value={depositPercent}
          unit="%"
          override={overrides.depositPercent}
          onOverride={(v) => handleOverride('depositPercent', v)}
          isOverridden={overrides.depositPercent !== undefined}
        />

        {/* ── E. Formula Breakdown ──────────────────────────────── */}
        <SectionHeader>Formula Breakdown</SectionHeader>
        <div style={{
          padding: '8px 10px',
          borderRadius: 8,
          background: '#f5f3ef',
          fontSize: 10,
          fontFamily: 'monospace',
          color: '#555',
          lineHeight: 1.8,
        }}>
          <div>subtotal = Σ(line_items) + fabric_amount + labor</div>
          <div>&nbsp;&nbsp;= {lineItems.reduce((s: number, i: any) => s + (i.amount || 0), 0).toFixed(2)} + {fabricAmount.toFixed(2)} + {displayLaborAmount.toFixed(2)}</div>
          <div>&nbsp;&nbsp;= <strong>${subtotal.toFixed(2)}</strong></div>
          <div>tax = subtotal × tax_rate = {subtotal.toFixed(2)} × {taxRate}</div>
          <div>&nbsp;&nbsp;= <strong>${taxAmount.toFixed(2)}</strong></div>
          <div>total = subtotal + tax - discount</div>
          <div>&nbsp;&nbsp;= <strong>${total.toFixed(2)}</strong></div>
          <div>deposit = total × deposit_% = {total.toFixed(2)} × {depositPercent}%</div>
          <div>&nbsp;&nbsp;= <strong>${depositAmount.toFixed(2)}</strong></div>
          <div>balance_due = total - deposit = <strong>${balanceDue.toFixed(2)}</strong></div>
        </div>

        {/* ── F. Final Numbers ──────────────────────────────────── */}
        <SectionHeader>Quote Summary</SectionHeader>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          marginTop: 4,
        }}>
          {[
            { label: 'Subtotal', value: subtotal, color: '#333' },
            { label: 'Tax', value: taxAmount, color: '#555' },
            { label: 'Total', value: total, color: '#16a34a' },
            { label: 'Deposit', value: depositAmount, color: '#b8960c' },
          ].map(item => (
            <div key={item.label} style={{
              padding: '8px 10px',
              borderRadius: 8,
              background: '#fff',
              border: '1px solid #ece8e0',
            }}>
              <div style={{ fontSize: 10, color: '#777', marginBottom: 2 }}>{item.label}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: item.color }}>
                ${item.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
          ))}
        </div>
        {balanceDue > 0 && (
          <div style={{ marginTop: 6, textAlign: 'right' }}>
            <span style={{ fontSize: 11, color: '#777' }}>Balance due: </span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#555' }}>
              ${balanceDue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}

        {/* ── G. Approval Controls ──────────────────────────────── */}
        <SectionHeader>Approval Controls</SectionHeader>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button
            onClick={handleApproveMeasurements}
            disabled={disabled || !hasMeasurements}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: 8,
              border: measurementsApproved ? '2px solid #16a34a' : '2px solid #ece8e0',
              background: measurementsApproved ? '#dcfce7' : '#fff',
              color: measurementsApproved ? '#16a34a' : '#555',
              fontSize: 11,
              fontWeight: 700,
              cursor: disabled || !hasMeasurements ? 'not-allowed' : 'pointer',
              opacity: disabled || !hasMeasurements ? 0.5 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 4,
            }}
          >
            <Check size={12} />
            {measurementsApproved ? 'Measurements Approved' : 'Approve Measurements'}
          </button>
          <button
            onClick={handleApprovePricing}
            disabled={disabled || !hasMeasurements}
            style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: 8,
              border: pricingApproved ? '2px solid #16a34a' : '2px solid #ece8e0',
              background: pricingApproved ? '#dcfce7' : '#fff',
              color: pricingApproved ? '#16a34a' : '#555',
              fontSize: 11,
              fontWeight: 700,
              cursor: disabled || !hasMeasurements ? 'not-allowed' : 'pointer',
              opacity: disabled || !hasMeasurements ? 0.5 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 4,
            }}
          >
            <Check size={12} />
            {pricingApproved ? 'Pricing Approved' : 'Approve Pricing'}
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
          <button
            onClick={handleReset}
            style={{
              flex: 1,
              padding: '6px 10px',
              borderRadius: 8,
              border: '1px solid #ece8e0',
              background: '#fff',
              color: '#777',
              fontSize: 10,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 4,
            }}
          >
            <RotateCcw size={10} /> Reset Approvals
          </button>
        </div>

        {/* ── H. Render Tier Note ─────────────────────────────────── */}
        {(mockupData?.proposals?.length ?? 0) > 0 && (
          <div style={{
            marginTop: 12,
            padding: '8px 10px',
            borderRadius: 6,
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            fontSize: 10,
            color: '#1d4ed8',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 6,
          }}>
            <Info size={12} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>
              Render option tier (A/B/C) is <strong>visual only</strong>. It does not automatically select pricing tier unless founder confirms pricing.
            </span>
          </div>
        )}

        {/* ── I. Prototype Warning ─────────────────────────────── */}
        <div style={{
          marginTop: 12,
          padding: '8px 10px',
          borderRadius: 6,
          background: '#fef9c3',
          border: '1px solid #fde047',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 6,
        }}>
          <AlertTriangle size={12} style={{ color: '#854d0e', flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 10, fontWeight: 600, color: '#854d0e', lineHeight: 1.5 }}>
            Pricing review is currently a local v10 prototype. Backend audit persistence will be added in a later phase.
          </span>
        </div>

        {/* ── J. Can Create Quote indicator ─────────────────────── */}
        {hasMeasurements && (
          <div style={{
            marginTop: 10,
            padding: '8px 12px',
            borderRadius: 8,
            background: canCreateQuote ? '#dcfce7' : '#fef2f2',
            border: canCreateQuote ? '1px solid #bbf7d0' : '1px solid #fecaca',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            {canCreateQuote ? (
              <>
                <Check size={12} style={{ color: '#16a34a' }} />
                <span style={{ fontSize: 10, fontWeight: 700, color: '#16a34a' }}>
                  Ready to create quote — all approvals complete.
                </span>
              </>
            ) : (
              <>
                <AlertTriangle size={12} style={{ color: '#dc2626', flexShrink: 0 }} />
                <span style={{ fontSize: 10, fontWeight: 600, color: '#dc2626' }}>
                  {!measurementsApproved ? 'Awaiting measurement approval.' : !pricingApproved ? 'Awaiting pricing approval.' : !hasMeasurements ? 'No measurements available.' : 'Quote total is zero.'}
                </span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
