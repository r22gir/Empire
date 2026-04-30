/**
 * QuotePricingGate — Shared Pricing Approval Gate
 * Phase 1.2 — reusable across QuickQuoteBuilder and QuoteBuilderScreen
 *
 * Shows input assumptions, formula summary, and requires explicit
 * founder approval before quote submission.
 *
 * Does NOT compute final pricing — backend does that via
 * /quotes/quick or /quotes/from-rooms. This panel only displays
 * what the founder has entered and requires sign-off.
 */

'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { Shield, AlertTriangle, Check, RotateCcw, Info } from 'lucide-react';
import { usePricingAudit } from '../../../hooks/usePricingAudit';

export interface QuotePricingInputs {
  // Dimensions
  width?: number | string;
  height?: number | string;
  depth?: number | string;
  windowType?: string;
  // Material
  fabricYards?: number | string;
  fabricRate?: number | string; // $/yd
  fabricName?: string;
  fabricGrade?: string;
  // Labor
  laborAmount?: number | string;
  laborDescription?: string;
  // Business context
  itemDescription?: string;
  quantity?: number | string;
  // Options summary (display only)
  liningType?: string;
  pleatType?: string;
  fabricGradeLabel?: string;
  // Route
  routeTo?: 'workroom' | 'woodcraft';
  // AI measurement data
  aiConfidence?: number | null;
  hasAiMeasurement?: boolean;
}

interface QuotePricingGateProps {
  inputs: QuotePricingInputs;
  /** Called when approvals change — parents use this to gate submit buttons */
  onApprovalChange?: (measurementsApproved: boolean, pricingApproved: boolean) => void;
  /** Called when any override changes — parents can track for their own state */
  onOverridesChange?: (overrides: Record<string, number>) => void;
  /** Override values pre-applied (e.g. from existing room item state) */
  initialOverrides?: Record<string, number>;
  /** Draft ID suffix for usePricingAudit — use flow-specific identifier */
  draftIdSuffix?: string;
  /** Additional copy shown below the panel title */
  subtitle?: string;
  /** Flow identifier for backend pricing warning: 'quick-quote' | 'room-quote' */
  flowType?: 'quick-quote' | 'room-quote';
  /** Disable the panel */
  disabled?: boolean;
}

const HARDCODED_FABRIC_RATE = 25;

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 700, color: '#777',
      textTransform: 'uppercase', letterSpacing: '0.06em',
      marginBottom: 6, marginTop: 12,
      paddingBottom: 4, borderBottom: '1px solid #ece8e0',
    }}>
      {children}
    </div>
  );
}

function FieldRow({ label, value, unit, badge, badgeColor }: {
  label: string; value?: string | number | null; unit?: string;
  badge?: string; badgeColor?: string;
}) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '4px 0', borderBottom: '1px solid #f5f3ef',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 12, color: '#555' }}>{label}</span>
        {badge && (
          <span style={{
            fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
            background: badgeColor === 'green' ? '#dcfce7' : badgeColor === 'yellow' ? '#fef9c3' : '#f5f3ef',
            color: badgeColor === 'green' ? '#16a34a' : badgeColor === 'yellow' ? '#854d0e' : '#555',
          }}>
            {badge}
          </span>
        )}
      </div>
      <span style={{ fontSize: 12, fontWeight: 600, color: '#333' }}>
        {value}{unit ? <span style={{ fontSize: 10, color: '#999', marginLeft: 2 }}>{unit}</span> : null}
      </span>
    </div>
  );
}

function OverrideRow({ label, field, value, unit, onOverride }: {
  label: string; field: string; value?: string | number | null; unit?: string;
  onOverride: (field: string, value: number) => void;
}) {
  const numVal = typeof value === 'string' ? parseFloat(value) : (typeof value === 'number' ? value : 0);
  if (!value && value !== 0) return null;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '4px 0', borderBottom: '1px solid #f5f3ef',
    }}>
      <span style={{ fontSize: 12, color: '#555' }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <input
          type="number"
          defaultValue={numVal}
          onChange={(e) => onOverride(field, parseFloat(e.target.value) || 0)}
          style={{
            width: 70, padding: '3px 6px', fontSize: 12,
            border: '1px solid #ece8e0', borderRadius: 6,
            background: '#fff', color: '#333', textAlign: 'right',
          }}
        />
        <span style={{ fontSize: 10, color: '#999' }}>{unit || ''}</span>
      </div>
    </div>
  );
}

export default function QuotePricingGate({
  inputs,
  onApprovalChange,
  onOverridesChange,
  initialOverrides = {},
  draftIdSuffix = 'generic',
  subtitle,
  flowType,
  disabled = false,
}: QuotePricingGateProps) {
  const {
    currentEntry,
    initAudit,
    recordAiAssumption,
    recordOverride,
    approveMeasurements,
    approvePricing,
    resetApprovals,
    setDimensionsSource,
  } = usePricingAudit();

  const [overrides, setOverrides] = useState<Record<string, number>>(initialOverrides);
  const [measurementsApproved, setMeasurementsApproved] = useState(false);
  const [pricingApproved, setPricingApproved] = useState(false);

  // Normalize inputs to numbers
  const num = (v: string | number | undefined | null) =>
    typeof v === 'number' ? v : typeof v === 'string' ? parseFloat(v) || 0 : 0;

  const displayWidth = overrides['width'] ?? num(inputs.width);
  const displayHeight = overrides['height'] ?? num(inputs.height);
  const displayFabricYards = overrides['fabricYards'] ?? num(inputs.fabricYards);
  const displayFabricRate = overrides['fabricRate'] ?? (num(inputs.fabricRate) || HARDCODED_FABRIC_RATE);
  const displayLaborAmount = overrides['laborAmount'] ?? num(inputs.laborAmount);
  const displayQuantity = num(inputs.quantity) || 1;

  const hasMeasurements = !!(inputs.width || inputs.height || displayWidth || displayHeight);
  const hasLabor = displayLaborAmount > 0;
  const confidence = inputs.aiConfidence ?? null;
  const isLowConfidence = confidence !== null && confidence < 60;
  const hasAiMeasurement = inputs.hasAiMeasurement ?? !!(inputs.aiConfidence);
  const isOverridden = Object.keys(overrides).length > 0;

  // Init audit with a flow-specific draft ID
  useEffect(() => {
    initAudit({
      dimensionsSource: hasAiMeasurement ? 'ai_estimate' : 'unknown',
    });
  }, []);

  // Record AI assumptions
  useEffect(() => {
    if (inputs.width != null) recordAiAssumption('width', inputs.width, inputs.aiConfidence);
    if (inputs.height != null) recordAiAssumption('height', inputs.height, inputs.aiConfidence);
  }, [inputs.width, inputs.height, inputs.aiConfidence, recordAiAssumption]);

  // Notify parent of approval changes
  useEffect(() => {
    onApprovalChange?.(measurementsApproved, pricingApproved);
  }, [measurementsApproved, pricingApproved, onApprovalChange]);

  const handleApproveMeasurements = useCallback(() => {
    const next = !measurementsApproved;
    setMeasurementsApproved(next);
    if (next) setDimensionsSource(overrides['width'] || overrides['height'] ? 'manual' : (hasAiMeasurement ? 'ai_estimate' : 'unknown'));
    else setPricingApproved(false);
  }, [measurementsApproved, overrides, hasAiMeasurement, setDimensionsSource]);

  const handleApprovePricing = useCallback(() => {
    const next = !pricingApproved;
    setPricingApproved(next);
    if (next) approvePricing();
    else resetApprovals();
  }, [pricingApproved, approvePricing, resetApprovals]);

  const handleOverride = useCallback((field: string, value: number) => {
    setOverrides(prev => {
      const next = { ...prev, [field]: value };
      onOverridesChange?.(next);
      return next;
    });
    const originals: Record<string, number> = {
      width: num(inputs.width),
      height: num(inputs.height),
      fabricYards: num(inputs.fabricYards),
      fabricRate: num(inputs.fabricRate) || HARDCODED_FABRIC_RATE,
      laborAmount: num(inputs.laborAmount),
    };
    recordOverride(field, originals[field] ?? null, value);
    // Selective reset: dimension override → both approvals reset
    // other overrides → pricing reset
    if (field === 'width' || field === 'height') {
      setMeasurementsApproved(false);
      setPricingApproved(false);
    } else {
      setPricingApproved(false);
    }
  }, [inputs, recordOverride, onOverridesChange, num]);

  const handleReset = useCallback(() => {
    setOverrides({});
    setMeasurementsApproved(false);
    setPricingApproved(false);
    resetApprovals();
  }, [resetApprovals]);

  const canSubmit = !disabled && (!hasAiMeasurement || measurementsApproved) && pricingApproved;

  return (
    <div style={{
      border: '1px solid #ece8e0', borderRadius: 12,
      background: '#faf9f7', overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid #ece8e0',
        background: '#fff', display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <Shield size={14} style={{ color: '#b8960c', flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 700, color: '#333' }}>
          Pricing Review
        </span>
        {subtitle && (
          <span style={{ fontSize: 10, color: '#999' }}>{subtitle}</span>
        )}
        {isOverridden && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#fef9c3', color: '#854d0e' }}>
            Override Active
          </span>
        )}
        {!measurementsApproved && hasMeasurements && hasAiMeasurement && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#fef9c3', color: '#854d0e' }}>
            Needs Review
          </span>
        )}
        {!pricingApproved && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#dbeafe', color: '#1d4ed8' }}>
            {hasAiMeasurement && !measurementsApproved ? 'Measurements First' : 'Awaiting Approval'}
          </span>
        )}
        {(measurementsApproved || !hasAiMeasurement) && pricingApproved && (
          <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: '#dcfce7', color: '#16a34a' }}>
            Approved
          </span>
        )}
      </div>

      <div style={{ padding: '12px 16px' }}>
        {/* Dimensions */}
        {(hasMeasurements || inputs.itemDescription) && (
          <>
            <SectionLabel>Item / Dimensions</SectionLabel>
            {inputs.itemDescription && (
              <FieldRow label="Item" value={inputs.itemDescription} badge={inputs.routeTo ? inputs.routeTo.toUpperCase() : undefined} />
            )}
            <FieldRow
              label="Width"
              value={displayWidth || undefined}
              unit="in"
              badge={overrides['width'] ? 'Override' : (inputs.width ? 'Entered' : '—')}
              badgeColor={overrides['width'] ? 'yellow' : undefined}
            />
            <FieldRow
              label="Height"
              value={displayHeight || undefined}
              unit="in"
              badge={overrides['height'] ? 'Override' : (inputs.height ? 'Entered' : '—')}
              badgeColor={overrides['height'] ? 'yellow' : undefined}
            />
            {inputs.windowType && <FieldRow label="Type" value={inputs.windowType} />}
            {confidence !== null && (
              <FieldRow
                label="AI Confidence"
                value={confidence}
                unit="%"
                badge={isLowConfidence ? 'Low' : 'OK'}
                badgeColor={isLowConfidence ? 'yellow' : 'green'}
              />
            )}
          </>
        )}

        {/* Material */}
        {(inputs.fabricYards || inputs.fabricRate || inputs.fabricName || inputs.fabricGrade) && (
          <>
            <SectionLabel>Material</SectionLabel>
            {inputs.fabricName && <FieldRow label="Fabric" value={inputs.fabricName} badge={inputs.fabricGrade || undefined} badgeColor={inputs.fabricGrade ? 'blue' : undefined} />}
            <FieldRow
              label="Fabric Yards"
              value={displayFabricYards || undefined}
              unit="yd"
              badge={overrides['fabricYards'] ? 'Override' : 'Entered'}
              badgeColor={overrides['fabricYards'] ? 'yellow' : undefined}
            />
            <FieldRow
              label="Fabric Rate"
              value={displayFabricRate}
              unit="$/yd"
              badge={overrides['fabricRate'] ? 'Override' : `Default $${HARDCODED_FABRIC_RATE}`}
              badgeColor={overrides['fabricRate'] ? 'yellow' : undefined}
            />
            {inputs.liningType && <FieldRow label="Lining" value={inputs.liningType} />}
          </>
        )}

        {/* Labor */}
        <SectionLabel>Labor</SectionLabel>
        {!hasLabor && inputs.laborDescription && (
          <FieldRow label="Description" value={inputs.laborDescription} badge="Missing" badgeColor="yellow" />
        )}
        {!hasLabor && !inputs.laborDescription && (
          <FieldRow label="Labor" value="—" badge="Not Set" badgeColor="yellow" />
        )}
        <FieldRow
          label="Labor Amount"
          value={displayLaborAmount || undefined}
          unit="$"
          badge={displayLaborAmount === 0 ? 'Zero' : overrides['laborAmount'] ? 'Override' : (inputs.laborAmount ? 'Entered' : '—')}
          badgeColor={displayLaborAmount === 0 ? 'yellow' : 'blue'}
        />
        <FieldRow label="Quantity" value={displayQuantity} unit="pcs" />

        {/* Info note — formula not available client-side */}
        <div style={{
          marginTop: 12,
          padding: '8px 10px',
          borderRadius: 6,
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          display: 'flex', alignItems: 'flex-start', gap: 6,
        }}>
          <Info size={12} style={{ color: '#1d4ed8', flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 10, color: '#1d4ed8', lineHeight: 1.5 }}>
            Final pricing is calculated by the backend quote engine. This panel displays your entered inputs so you can verify them before submission.
          </span>
        </div>

        {/* Prototype warning */}
        <div style={{
          marginTop: 10,
          padding: '8px 10px',
          borderRadius: 6,
          background: '#fef9c3',
          border: '1px solid #fde047',
          display: 'flex', alignItems: 'flex-start', gap: 6,
        }}>
          <AlertTriangle size={12} style={{ color: '#854d0e', flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 10, fontWeight: 600, color: '#854d0e', lineHeight: 1.5 }}>
            Pricing review is currently a local v10 prototype. Backend audit persistence will be added in a later phase.
          </span>
        </div>

        {/* Backend pricing engine warning */}
        {flowType === 'quick-quote' && (
          <div style={{
            marginTop: 10,
            padding: '8px 10px',
            borderRadius: 6,
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            display: 'flex', alignItems: 'flex-start', gap: 6,
          }}>
            <AlertTriangle size={12} style={{ color: '#1d4ed8', flexShrink: 0, marginTop: 1 }} />
            <span style={{ fontSize: 10, fontWeight: 600, color: '#1d4ed8', lineHeight: 1.5 }}>
              Quick Quote uses the backend quick-price table. Confirm all inputs are accurate before submitting.
            </span>
          </div>
        )}
        {flowType === 'room-quote' && (
          <div style={{
            marginTop: 10,
            padding: '8px 10px',
            borderRadius: 6,
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            display: 'flex', alignItems: 'flex-start', gap: 6,
          }}>
            <AlertTriangle size={12} style={{ color: '#1d4ed8', flexShrink: 0, marginTop: 1 }} />
            <span style={{ fontSize: 10, fontWeight: 600, color: '#1d4ed8', lineHeight: 1.5 }}>
              Room Quote pricing is generated by the backend quote engine with tier-based margins. Review all items before submitting.
            </span>
          </div>
        )}

        {/* Approval buttons */}
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          {hasAiMeasurement && (
            <button
              onClick={handleApproveMeasurements}
              disabled={disabled || !hasMeasurements}
              style={{
                flex: 1, padding: '8px 10px', borderRadius: 8,
                border: measurementsApproved ? '2px solid #16a34a' : '2px solid #ece8e0',
                background: measurementsApproved ? '#dcfce7' : '#fff',
                color: measurementsApproved ? '#16a34a' : '#555',
                fontSize: 11, fontWeight: 700, cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.5 : 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
              }}
            >
              <Check size={12} />
              {measurementsApproved ? 'Measurements Approved' : 'Approve Measurements'}
            </button>
          )}
          <button
            onClick={handleApprovePricing}
            disabled={disabled}
            style={{
              flex: 1, padding: '8px 10px', borderRadius: 8,
              border: pricingApproved ? '2px solid #16a34a' : '2px solid #ece8e0',
              background: pricingApproved ? '#dcfce7' : '#fff',
              color: pricingApproved ? '#16a34a' : '#555',
              fontSize: 11, fontWeight: 700, cursor: disabled ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.5 : 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
            }}
          >
            <Check size={12} />
            {pricingApproved ? 'Pricing Approved' : 'Approve Pricing'}
          </button>
        </div>
        <button
          onClick={handleReset}
          style={{
            width: '100%', marginTop: 6, padding: '5px 10px', borderRadius: 8,
            border: '1px solid #ece8e0', background: '#fff',
            color: '#777', fontSize: 10, fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
          }}
        >
          <RotateCcw size={10} /> Reset Approvals
        </button>

        {/* Ready state */}
        {hasMeasurements && (
          <div style={{
            marginTop: 10,
            padding: '8px 12px', borderRadius: 8,
            background: canSubmit ? '#dcfce7' : '#fef2f2',
            border: canSubmit ? '1px solid #bbf7d0' : '1px solid #fecaca',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            {canSubmit ? (
              <>
                <Check size={12} style={{ color: '#16a34a' }} />
                <span style={{ fontSize: 10, fontWeight: 700, color: '#16a34a' }}>
                  Ready to submit.
                </span>
              </>
            ) : (
              <>
                <AlertTriangle size={12} style={{ color: '#dc2626', flexShrink: 0 }} />
                <span style={{ fontSize: 10, fontWeight: 600, color: '#dc2626' }}>
                  {hasAiMeasurement && !measurementsApproved
                    ? 'Approve measurements first.'
                    : 'Approve pricing to continue.'}
                </span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
