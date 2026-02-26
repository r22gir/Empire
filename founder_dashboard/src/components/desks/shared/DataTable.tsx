'use client';
import { type ReactNode } from 'react';

export interface Column<T> {
  key: string;
  label: string;
  render?: (item: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  getRowId: (item: T) => string;
  onRowClick?: (item: T) => void;
  selectedId?: string | null;
  emptyMessage?: string;
}

export default function DataTable<T>({
  columns, data, getRowId, onRowClick, selectedId, emptyMessage = 'No data',
}: DataTableProps<T>) {
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
      <table className="w-full text-xs">
        <thead>
          <tr style={{ background: 'var(--elevated)' }}>
            {columns.map(col => (
              <th
                key={col.key}
                className={`text-left px-3 py-2.5 font-semibold ${col.className || ''}`}
                style={{ color: 'var(--gold)', borderBottom: '1px solid var(--border)' }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map(item => {
              const id = getRowId(item);
              return (
                <tr
                  key={id}
                  className="transition cursor-pointer"
                  style={{
                    borderBottom: '1px solid var(--border)',
                    background: selectedId === id ? 'var(--gold-pale)' : 'transparent',
                  }}
                  onClick={() => onRowClick?.(item)}
                  onMouseEnter={e => { if (selectedId !== id) e.currentTarget.style.background = 'var(--hover)'; }}
                  onMouseLeave={e => { if (selectedId !== id) e.currentTarget.style.background = 'transparent'; }}
                >
                  {columns.map(col => (
                    <td key={col.key} className={`px-3 py-2.5 ${col.className || ''}`} style={{ color: 'var(--text-primary)' }}>
                      {col.render ? col.render(item) : String((item as Record<string, unknown>)[col.key] ?? '')}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
