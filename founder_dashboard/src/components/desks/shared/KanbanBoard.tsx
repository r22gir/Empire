'use client';
import { type ReactNode } from 'react';
import { ChevronRight } from 'lucide-react';

export interface KanbanColumn {
  key: string;
  label: string;
  color: string;
}

interface KanbanBoardProps<T> {
  columns: KanbanColumn[];
  items: T[];
  getColumnKey: (item: T) => string;
  getItemId: (item: T) => string;
  renderCard: (item: T) => ReactNode;
  onMoveItem?: (itemId: string, toColumn: string) => void;
  columnWidth?: number;
}

export default function KanbanBoard<T>({
  columns, items, getColumnKey, getItemId, renderCard,
  onMoveItem, columnWidth = 220,
}: KanbanBoardProps<T>) {
  return (
    <div className="flex gap-3 h-full min-w-max">
      {columns.map((col, colIdx) => {
        const colItems = items.filter(item => getColumnKey(item) === col.key);
        const nextCol = columns[colIdx + 1];
        return (
          <div
            key={col.key}
            className="flex flex-col rounded-xl shrink-0"
            style={{ width: columnWidth, background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            {/* Column header */}
            <div className="px-3 py-2.5 flex items-center gap-2 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: col.color }} />
              <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{col.label}</span>
              <span
                className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full font-mono"
                style={{ background: 'var(--raised)', color: 'var(--text-muted)' }}
              >
                {colItems.length}
              </span>
            </div>

            {/* Cards */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {colItems.map(item => (
                <div key={getItemId(item)} className="group">
                  {renderCard(item)}
                  {onMoveItem && nextCol && (
                    <button
                      onClick={() => onMoveItem(getItemId(item), nextCol.key)}
                      className="w-full mt-1.5 flex items-center justify-center gap-1 py-1 rounded text-[10px] font-medium opacity-0 group-hover:opacity-100 transition"
                      style={{ background: 'var(--raised)', color: nextCol.color, border: '1px solid var(--border)' }}
                    >
                      Move to {nextCol.label} <ChevronRight className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
              {colItems.length === 0 && (
                <p className="text-[10px] text-center py-4" style={{ color: 'var(--text-muted)' }}>Empty</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
