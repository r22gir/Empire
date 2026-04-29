/**
 * BundleIntelligencePanel
 * Phase 1 Prototype — mock bundle suggestions with value comparison
 */

'use client';

import { useBundleSuggestions } from '../../hooks/useArchiveForgePrototype';
import { ARCHIVEFORGE_PROTOTYPE_DISCLAIMER } from '../../config/archiveforge-mock';

function ActionBadge({ action }: { action: string }) {
  const config: Record<string, { label: string; color: string; icon: string }> = {
    recommend: { label: 'RECOMMEND', color: 'bg-green-900/60 text-green-300 border-green-700', icon: '✓' },
    consider: { label: 'CONSIDER', color: 'bg-yellow-900/60 text-yellow-300 border-yellow-700', icon: '?' },
    caution: { label: 'CAUTION', color: 'bg-orange-900/60 text-orange-300 border-orange-700', icon: '!' },
  };
  const c = config[action] || config.caution;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border capitalize ${c.color}`}>
      {c.icon} {c.label}
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-700 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-orange-500'}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-sm font-medium text-gray-300 w-8 text-right">{score}</span>
    </div>
  );
}

function BundleCard({ bundle }: { bundle: {
  bundleName: string;
  items: string[];
  individualTotal: number;
  bundleValue: number;
  savings: number;
  score: number;
  reasoning: string;
  action: string;
}}) {
  const savingsPct = ((bundle.savings / bundle.individualTotal) * 100).toFixed(0);

  return (
    <div className={`bg-gray-800/50 rounded-xl p-4 border ${
      bundle.action === 'recommend' ? 'border-green-700/50' :
      bundle.action === 'consider' ? 'border-yellow-700/50' :
      'border-orange-700/50'
    }`}>
      <div className="flex items-start justify-between mb-3">
        <h4 className="text-gray-100 font-semibold">{bundle.bundleName}</h4>
        <ActionBadge action={bundle.action} />
      </div>

      <ScoreBar score={bundle.score} />

      {/* Value Comparison */}
      <div className="grid grid-cols-3 gap-2 mt-4 mb-3">
        <div className="text-center bg-gray-700/50 rounded-lg p-2">
          <div className="text-gray-500 text-xs">Individual</div>
          <div className="text-gray-200 font-semibold text-sm">${bundle.individualTotal}</div>
        </div>
        <div className="text-center bg-indigo-900/30 rounded-lg p-2 border border-indigo-700/50">
          <div className="text-indigo-400 text-xs">Bundle</div>
          <div className="text-indigo-300 font-bold text-sm">${bundle.bundleValue}</div>
        </div>
        <div className="text-center bg-green-900/30 rounded-lg p-2 border border-green-700/50">
          <div className="text-green-400 text-xs">Savings</div>
          <div className="text-green-300 font-semibold text-sm">-${bundle.savings}</div>
        </div>
      </div>

      <p className="text-gray-400 text-xs italic mt-2">"{bundle.reasoning}"</p>

      <div className="flex flex-wrap gap-1 mt-3">
        {bundle.items.map((item) => (
          <span key={item} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full border border-gray-600">
            {item}
          </span>
        ))}
      </div>

      <button
        className={`w-full mt-4 px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
          bundle.action === 'recommend'
            ? 'bg-green-700/50 hover:bg-green-600/50 text-green-300 border-green-600/50'
            : bundle.action === 'consider'
            ? 'bg-yellow-700/50 hover:bg-yellow-600/50 text-yellow-300 border-yellow-600/50'
            : 'bg-gray-700/50 hover:bg-gray-600/50 text-gray-300 border-gray-600/50'
        }`}
        onClick={() => alert(`Would create bundle listing: ${bundle.bundleName}`)}
      >
        Create Bundle Listing
      </button>
    </div>
  );
}

export default function BundleIntelligencePanel() {
  const { data, loading } = useBundleSuggestions();

  return (
    <div className="space-y-4" data-max-task="bundle-intelligence-backend-integration">
      {/* Prototype disclaimer */}
      <div className="border border-yellow-600/40 bg-yellow-900/20 rounded-lg p-3 flex items-start gap-2">
        <span className="text-yellow-400 mt-0.5">⚠</span>
        <div>
          <p className="text-yellow-300 text-sm font-medium">Prototype bundle intelligence — backend integration pending</p>
          <p className="text-yellow-400/70 text-xs mt-0.5">POST /api/v1/bundle/suggest not yet implemented</p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4 animate-pulse">
          {[1, 2].map((i) => (
            <div key={i} className="h-56 bg-gray-700 rounded-xl" />
          ))}
        </div>
      ) : data.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          <div className="text-3xl mb-2">📦</div>
          <p className="text-sm">No bundle suggestions available</p>
          <p className="text-xs text-gray-600 mt-1">Add more items to your inventory to receive suggestions</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.map((bundle) => (
            <BundleCard key={bundle.id} bundle={bundle} />
          ))}
        </div>
      )}
    </div>
  );
}
