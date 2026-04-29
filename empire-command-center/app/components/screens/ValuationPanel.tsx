/**
 * ValuationPanel
 * Phase 1 Prototype — displays mock valuation range with sparkline
 */

'use client';

import { useValuationData, useComparableSales } from '../../hooks/useArchiveForgePrototype';
import ComparableSalesSparkline from './ComparableSalesSparkline';
import { ARCHIVEFORGE_PROTOTYPE_DISCLAIMER } from '../../config/archiveforge-mock';

function EmpireStatusPill({ children, variant = 'default' }: { children: React.ReactNode; variant?: 'success' | 'warning' | 'error' | 'default' }) {
  const colors: Record<string, string> = {
    success: 'bg-green-900/60 text-green-300 border-green-700',
    warning: 'bg-yellow-900/60 text-yellow-300 border-yellow-700',
    error: 'bg-red-900/60 text-red-300 border-red-700',
    default: 'bg-gray-800/60 text-gray-300 border-gray-700',
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${colors[variant]}`}>
      {children}
    </span>
  );
}

function ValuationLoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-4 bg-gray-700 rounded w-1/3" />
      <div className="h-20 bg-gray-700 rounded" />
      <div className="h-32 bg-gray-700 rounded" />
    </div>
  );
}

export default function ValuationPanel() {
  const { data: valuation, loading: valuationLoading } = useValuationData();
  const { data: comparables, loading: compLoading } = useComparableSales();

  return (
    <div className="space-y-4" data-max-task="valuation-backend-integration">
      {/* Prototype disclaimer */}
      <div className="border border-yellow-600/40 bg-yellow-900/20 rounded-lg p-3 flex items-start gap-2">
        <span className="text-yellow-400 mt-0.5">⚠</span>
        <div>
          <p className="text-yellow-300 text-sm font-medium">{ARCHIVEFORGE_PROTOTYPE_DISCLAIMER}</p>
          <p className="text-yellow-400/70 text-xs mt-0.5">Backend POST /api/v1/valuation/estimate not yet implemented</p>
        </div>
      </div>

      {valuationLoading ? (
        <ValuationLoadingSkeleton />
      ) : valuation ? (
        <>
          {/* Valuation Range */}
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-gray-300 text-sm font-medium">Estimated Value Range</h3>
              <EmpireStatusPill variant="success">
                {valuation.confidence}% confidence
              </EmpireStatusPill>
            </div>

            <div className="flex items-end gap-4 mb-4">
              <div>
                <div className="text-gray-500 text-xs uppercase tracking-wide">Low</div>
                <div className="text-xl font-bold text-gray-200">${valuation.valuationRange.low}</div>
              </div>
              <div className="flex-1 flex flex-col items-center">
                <div className="text-gray-500 text-xs uppercase tracking-wide">Median</div>
                <div className="text-3xl font-extrabold text-indigo-400">${valuation.valuationRange.median}</div>
              </div>
              <div>
                <div className="text-gray-500 text-xs uppercase tracking-wide">High</div>
                <div className="text-xl font-bold text-gray-200">${valuation.valuationRange.high}</div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span className="text-gray-400 font-medium">{valuation.itemTitle}</span>
              <span>•</span>
              <span>Updated {valuation.lastUpdated}</span>
              <span>•</span>
              <span className="text-gray-600">Source: {valuation.dataSource}</span>
            </div>
          </div>

          {/* Comparable Sales Sparkline */}
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <h3 className="text-gray-300 text-sm font-medium mb-3">Comparable Sales</h3>
            {comparables && comparables.length > 0 ? (
              <ComparableSalesSparkline sales={comparables} height={100} showTooltip />
            ) : (
              <div className="h-24 flex items-center justify-center text-gray-500 text-sm italic">
                No comparable sales data
              </div>
            )}
          </div>

          {/* Action */}
          <div className="flex gap-3">
            <button
              className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
              onClick={() => alert('Would trigger listing flow with this valuation')}
            >
              List at ${valuation.valuationRange.median}
            </button>
            <button
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm font-medium transition-colors"
              onClick={() => alert('Would save valuation to item record')}
            >
              Save Valuation
            </button>
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500 py-8">No valuation data available</div>
      )}
    </div>
  );
}
