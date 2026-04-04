'use client';

import { useEffect, useState, useCallback } from 'react';

const API = 'http://localhost:8000';

const STAGES = [
  'pending',
  'fabric_ordered',
  'fabric_received',
  'cutting',
  'sewing',
  'finishing',
  'qc',
  'complete',
];

const STAGE_LABELS: Record<string, string> = {
  pending: 'Pending',
  fabric_ordered: 'Fabric Ordered',
  fabric_received: 'Fabric Received',
  cutting: 'Cutting',
  sewing: 'Sewing',
  finishing: 'Finishing',
  qc: 'QC',
  complete: 'Complete',
};

interface BoardItem {
  id: number;
  work_order_id: number;
  description: string;
  item_type: string;
  room: string;
  production_status: string;
  work_order_number: string;
  customer_name: string;
  due_date: string | null;
  urgency: 'overdue' | 'due_soon' | 'on_track' | 'no_date';
  urgency_color: 'red' | 'yellow' | 'green' | 'gray';
}

interface BoardData {
  board: Record<string, BoardItem[]>;
  total_items: number;
  overdue: number;
  due_soon: number;
  stages: string[];
  stage_counts: Record<string, number>;
}

const URGENCY_BORDER: Record<string, string> = {
  red: 'border-l-red-500',
  yellow: 'border-l-yellow-400',
  green: 'border-l-green-500',
  gray: 'border-l-gray-400',
};

const URGENCY_DOT: Record<string, string> = {
  red: 'bg-red-500',
  yellow: 'bg-yellow-400',
  green: 'bg-green-500',
  gray: 'bg-gray-400',
};

export default function ProductionBoardPage() {
  const [data, setData] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [advancing, setAdvancing] = useState<number | null>(null);

  const fetchBoard = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/work-orders/production-board`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load board');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBoard();
    const interval = setInterval(fetchBoard, 30000);
    return () => clearInterval(interval);
  }, [fetchBoard]);

  const advanceItem = async (workOrderId: number, itemId: number) => {
    setAdvancing(itemId);
    try {
      const res = await fetch(
        `${API}/api/v1/work-orders/${workOrderId}/items/${itemId}/advance`,
        { method: 'POST' }
      );
      if (!res.ok) throw new Error(`Advance failed: ${res.status}`);
      await fetchBoard();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to advance item');
    } finally {
      setAdvancing(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#f5f3ef' }}>
        <div className="text-lg font-semibold" style={{ color: '#1a1a2e' }}>
          Loading production board...
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#f5f3ef' }}>
        <div className="text-center">
          <p className="text-lg font-semibold text-red-600 mb-4">{error}</p>
          <button
            onClick={() => { setLoading(true); fetchBoard(); }}
            className="px-6 py-2 rounded-lg text-white font-semibold"
            style={{ backgroundColor: '#b8960c' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const board = data?.board ?? {};
  const totalItems = data?.total_items ?? 0;
  const overdueCount = data?.overdue ?? 0;
  const dueSoonCount = data?.due_soon ?? 0;
  const stageCounts = data?.stage_counts ?? {};

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#f5f3ef' }}>
      {/* Header */}
      <header className="px-6 py-5 flex flex-wrap items-center justify-between gap-4" style={{ backgroundColor: '#1a1a2e' }}>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight" style={{ color: '#d4af37' }}>
          PRODUCTION BOARD
        </h1>
        <div className="flex items-center gap-3">
          <select
            className="rounded-lg px-3 py-2 text-sm font-medium border-0 outline-none"
            style={{ backgroundColor: '#2d2d44', color: '#ccc' }}
            defaultValue="workroom"
          >
            <option value="workroom">Empire Workroom</option>
            <option value="all">All Units</option>
          </select>
          <button
            onClick={() => fetchBoard()}
            className="rounded-lg px-4 py-2 text-sm font-semibold transition-opacity hover:opacity-80"
            style={{ backgroundColor: '#b8960c', color: '#1a1a2e' }}
          >
            Refresh
          </button>
        </div>
      </header>

      {/* Summary Bar */}
      <div className="px-6 py-3 flex flex-wrap items-center gap-6 border-b" style={{ borderColor: '#e0dcd4' }}>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium" style={{ color: '#555' }}>Total Items:</span>
          <span className="text-lg font-bold" style={{ color: '#1a1a2e' }}>{totalItems}</span>
        </div>
        {overdueCount > 0 && (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-white bg-red-500">
              {overdueCount}
            </span>
            <span className="text-sm font-medium text-red-600">Overdue</span>
          </div>
        )}
        {dueSoonCount > 0 && (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-gray-800 bg-yellow-400">
              {dueSoonCount}
            </span>
            <span className="text-sm font-medium text-yellow-600">Due Soon</span>
          </div>
        )}
        {error && (
          <span className="text-sm text-red-500 ml-auto">Update failed — showing cached data</span>
        )}
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto p-4 md:p-6">
        <div className="flex gap-4 min-w-max">
          {STAGES.map((stage) => {
            const items = board[stage] ?? [];
            const count = stageCounts[stage] ?? items.length;

            return (
              <div
                key={stage}
                className="flex flex-col w-72 md:w-80 shrink-0 rounded-xl overflow-hidden shadow-sm"
                style={{ backgroundColor: '#fff', border: '1px solid #e0dcd4' }}
              >
                {/* Column Header */}
                <div
                  className="px-4 py-3 flex items-center justify-between"
                  style={{ backgroundColor: '#1a1a2e' }}
                >
                  <span className="text-sm font-bold tracking-wide" style={{ color: '#d4af37' }}>
                    {STAGE_LABELS[stage] ?? stage}
                  </span>
                  <span
                    className="inline-flex items-center justify-center min-w-[24px] h-6 rounded-full px-2 text-xs font-bold"
                    style={{ backgroundColor: '#b8960c', color: '#1a1a2e' }}
                  >
                    {count}
                  </span>
                </div>

                {/* Cards */}
                <div className="flex-1 p-3 space-y-3 overflow-y-auto max-h-[calc(100vh-240px)]">
                  {items.length === 0 && (
                    <p className="text-center text-xs py-8" style={{ color: '#aaa' }}>
                      No items
                    </p>
                  )}
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className={`rounded-lg p-3 shadow-sm border-l-4 ${URGENCY_BORDER[item.urgency_color] ?? 'border-l-gray-400'}`}
                      style={{ backgroundColor: '#fff', border: '1px solid #ece8e0', borderLeftWidth: 4 }}
                    >
                      {/* Customer */}
                      <p className="text-sm font-bold truncate" style={{ color: '#1a1a2e' }}>
                        {item.customer_name}
                      </p>

                      {/* WO Number */}
                      <p className="text-xs mt-0.5" style={{ color: '#888' }}>
                        {item.work_order_number}
                      </p>

                      {/* Description / Item Type */}
                      <p className="text-xs mt-1.5 line-clamp-2" style={{ color: '#555' }}>
                        {item.description || item.item_type}
                        {item.room && (
                          <span style={{ color: '#999' }}> — {item.room}</span>
                        )}
                      </p>

                      {/* Due date + urgency dot */}
                      <div className="flex items-center justify-between mt-2">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`inline-block w-2.5 h-2.5 rounded-full ${URGENCY_DOT[item.urgency_color] ?? 'bg-gray-400'}`}
                          />
                          <span className="text-xs" style={{ color: '#777' }}>
                            {item.due_date
                              ? new Date(item.due_date).toLocaleDateString('en-US', {
                                  month: 'short',
                                  day: 'numeric',
                                })
                              : 'No date'}
                          </span>
                        </div>

                        {/* Advance Button — hide on complete */}
                        {stage !== 'complete' && (
                          <button
                            onClick={() => advanceItem(item.work_order_id, item.id)}
                            disabled={advancing === item.id}
                            className="text-xs font-semibold px-2.5 py-1 rounded-md transition-opacity hover:opacity-80 disabled:opacity-50"
                            style={{ backgroundColor: '#b8960c', color: '#fff' }}
                          >
                            {advancing === item.id ? '...' : 'Advance \u2192'}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
