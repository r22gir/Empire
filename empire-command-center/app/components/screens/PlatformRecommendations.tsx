/**
 * PlatformRecommendations
 * Phase 1 Prototype — mock platform scoring table
 */

'use client';

import { usePlatformRecommendations } from '../../hooks/useArchiveForgePrototype';
import { ARCHIVEFORGE_PROTOTYPE_DISCLAIMER } from '../../config/archiveforge-mock';

function ScoreBar({ score }: { score: number }) {
  const color = score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-700 rounded-full h-2">
        <div className={`h-2 rounded-full ${color} transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-sm font-medium text-gray-300 w-8 text-right">{score}</span>
    </div>
  );
}

function ReachBadge({ reach }: { reach: string }) {
  const colors: Record<string, string> = {
    high: 'bg-green-900/60 text-green-300 border-green-700',
    medium: 'bg-yellow-900/60 text-yellow-300 border-yellow-700',
    low: 'bg-gray-800/60 text-gray-400 border-gray-700',
  };
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs border capitalize ${colors[reach] || colors.low}`}>
      {reach}
    </span>
  );
}

function PlatformCard({ platform, score, fees, reach, bestFor }: {
  platform: string;
  score: number;
  fees: number;
  reach: string;
  bestFor: string[];
}) {
  const isRecommended = score >= 80;
  return (
    <div className={`bg-gray-800/50 rounded-xl p-4 border ${isRecommended ? 'border-indigo-600/50' : 'border-gray-700'}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h4 className="text-gray-100 font-semibold">{platform}</h4>
          <p className="text-gray-500 text-xs mt-0.5">{fees}% fees</p>
        </div>
        {isRecommended && (
          <span className="text-indigo-400 text-xs font-medium bg-indigo-900/30 px-2 py-0.5 rounded-full border border-indigo-700">
            Top Pick
          </span>
        )}
      </div>
      <ScoreBar score={score} />
      <div className="flex items-center gap-2 mt-3">
        <ReachBadge reach={reach} />
        {score >= 80 && (
          <span className="text-xs text-indigo-400">Recommended</span>
        )}
      </div>
      <div className="mt-3 flex flex-wrap gap-1">
        {bestFor.map((tag) => (
          <span key={tag} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full border border-gray-600">
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function PlatformRecommendations() {
  const { data, loading } = usePlatformRecommendations();

  return (
    <div className="space-y-4" data-max-task="platform-recommendation-backend-integration">
      {/* Prototype disclaimer */}
      <div className="border border-yellow-600/40 bg-yellow-900/20 rounded-lg p-3 flex items-start gap-2">
        <span className="text-yellow-400 mt-0.5">⚠</span>
        <div>
          <p className="text-yellow-300 text-sm font-medium">Prototype recommendation — not connected to live marketplace data yet</p>
          <p className="text-yellow-400/70 text-xs mt-0.5">POST /api/v1/market/recommend not yet implemented</p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-24 bg-gray-700 rounded" />
          <div className="h-24 bg-gray-700 rounded" />
        </div>
      ) : data ? (
        <>
          {/* Reasoning */}
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <p className="text-gray-300 text-sm italic">"{data.reasoning}"</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.recommended.map((p) => (
                <span key={p} className="text-xs bg-indigo-900/40 text-indigo-300 border border-indigo-700 px-3 py-1 rounded-full">
                  ✓ {p}
                </span>
              ))}
            </div>
          </div>

          {/* Platform Cards */}
          <div className="grid grid-cols-1 gap-3">
            {data.scores.map((p) => (
              <PlatformCard key={p.platform} {...p} />
            ))}
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500 py-8">No recommendations available</div>
      )}
    </div>
  );
}
