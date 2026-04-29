/**
 * FounderReviewQueue
 * Phase 1 Prototype — mock queue with localStorage flagging
 */

'use client';

import { useFounderQueue } from '../../hooks/useArchiveForgePrototype';
import { ARCHIVEFORGE_PROTOTYPE_DISCLAIMER } from '../../config/archiveforge-mock';

function PriorityBadge({ priority }: { priority: string }) {
  const config: Record<string, { label: string; color: string }> = {
    high: { label: 'HIGH', color: 'bg-red-900/60 text-red-300 border-red-700' },
    medium: { label: 'MEDIUM', color: 'bg-yellow-900/60 text-yellow-300 border-yellow-700' },
    low: { label: 'LOW', color: 'bg-gray-800/60 text-gray-400 border-gray-700' },
  };
  const c = config[priority] || config.low;
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs border capitalize ${c.color}`}>
      {c.label}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string }> = {
    pending: { color: 'text-gray-400' },
    flagged: { color: 'text-orange-400' },
    approved: { color: 'text-green-400' },
    rejected: { color: 'text-red-400' },
  };
  const c = config[status] || config.pending;
  const icon = status === 'pending' ? '⏳' : status === 'flagged' ? '🚩' : status === 'approved' ? '✅' : '❌';
  return (
    <span className={`text-sm ${c.color}`}>
      {icon}
    </span>
  );
}

function ReviewItemCard({ item }: { item: {
  id: string; itemTitle: string; estimatedValue: number; condition: string;
  priority: string; status: string; submittedAt: string; notes?: string;
}}) {
  const { flagItem, approveItem } = useFounderQueue();
  const isFlagged = item.status === 'flagged';

  return (
    <div className={`bg-gray-800/50 rounded-xl p-4 border ${isFlagged ? 'border-orange-600/50' : 'border-gray-700'}`}>
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <StatusBadge status={item.status} />
            <h4 className="text-gray-100 font-medium text-sm">{item.itemTitle}</h4>
          </div>
          <p className="text-gray-500 text-xs mt-1">{item.condition}</p>
        </div>
        <PriorityBadge priority={item.priority} />
      </div>

      <div className="flex items-center gap-4 text-sm mt-2">
        <div>
          <span className="text-gray-500 text-xs">Est. Value</span>
          <p className="text-gray-200 font-semibold">${item.estimatedValue}</p>
        </div>
        <div>
          <span className="text-gray-500 text-xs">Submitted</span>
          <p className="text-gray-400 text-xs mt-0.5">
            {new Date(item.submittedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
          </p>
        </div>
      </div>

      {item.notes && (
        <p className="text-gray-400 text-xs italic mt-2 border-l-2 border-gray-600 pl-2">{item.notes}</p>
      )}

      <div className="flex gap-2 mt-3">
        <button
          className="flex-1 px-3 py-1.5 bg-orange-700/50 hover:bg-orange-600/50 text-orange-300 rounded-lg text-xs font-medium border border-orange-600/50 transition-colors"
          onClick={() => flagItem(item.id)}
        >
          🚩 Flag
        </button>
        <button
          className="flex-1 px-3 py-1.5 bg-green-700/50 hover:bg-green-600/50 text-green-300 rounded-lg text-xs font-medium border border-green-600/50 transition-colors"
          onClick={() => approveItem(item.id)}
        >
          ✓ Approve
        </button>
      </div>
    </div>
  );
}

export default function FounderReviewQueue() {
  const { items, loading } = useFounderQueue();

  return (
    <div className="space-y-4" data-max-task="founder-queue-backend-integration">
      {/* Prototype disclaimer */}
      <div className="border border-yellow-600/40 bg-yellow-900/20 rounded-lg p-3 flex items-start gap-2">
        <span className="text-yellow-400 mt-0.5">⚠</span>
        <div>
          <p className="text-yellow-300 text-sm font-medium">Prototype queue — flagging writes to localStorage only</p>
          <p className="text-yellow-400/70 text-xs mt-0.5">POST /api/v1/founder-queue/flag not yet implemented</p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4 animate-pulse">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-36 bg-gray-700 rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center text-gray-500 py-12">
          <div className="text-3xl mb-2">📭</div>
          <p className="text-sm">No items in founder review queue</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {items.map((item) => (
            <ReviewItemCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
