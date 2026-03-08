'use client';
import { Ruler, Trash2 } from 'lucide-react';
import { API } from '../lib/api';

const statusColors: Record<string, string> = {
  concept: 'bg-[#f5f3ef] text-[#777]',
  designing: 'bg-[#dbeafe] text-[#2563eb]',
  ready: 'bg-[#fef3c7] text-[#d97706]',
  cutting: 'bg-[#ede9fe] text-[#7c3aed]',
  finishing: 'bg-[#fce7f3] text-[#db2777]',
  complete: 'bg-[#dcfce7] text-[#16a34a]',
};

const categoryLabels: Record<string, string> = {
  cornice: 'Cornice',
  valance: 'Valance',
  headboard: 'Headboard',
  'cabinet-door': 'Cabinet Door',
  sign: 'Sign',
  furniture: 'Furniture',
  custom: 'Custom',
};

export default function DesignsList({
  designs,
  onRefresh,
  full,
}: {
  designs: any[];
  onRefresh: () => void;
  full?: boolean;
}) {
  const handleDelete = async (id: string) => {
    await fetch(`${API}/designs/${id}`, { method: 'DELETE' });
    onRefresh();
  };

  const handleStatusChange = async (id: string, status: string) => {
    await fetch(`${API}/designs/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    onRefresh();
  };

  const shown = full ? designs : designs.slice(0, 6);

  return (
    <div className={`bg-white border border-[#e5e0d8] rounded-xl p-5 ${full ? '' : ''}`}>
      <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
        <Ruler size={15} className="text-[#c9a84c]" />
        {full ? 'All Designs' : 'Recent Designs'}
        <span className="text-[10px] text-[#aaa] font-normal ml-auto">{designs.length} total</span>
      </h3>

      <div className="space-y-2">
        {shown.map(d => (
          <div key={d.id} className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] hover:border-[#c9a84c] hover:bg-[#fdf8eb] transition-all group">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-[#1a1a1a] truncate">{d.design_number}</span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#f5f3ef] text-[#777]">
                  {categoryLabels[d.category] || d.category}
                </span>
              </div>
              <div className="text-[11px] text-[#777] truncate">{d.name} — {d.customer_name}</div>
              {d.width && <div className="text-[9px] text-[#aaa]">{d.width}&quot; × {d.height}&quot; × {d.depth}&quot; · {d.primary_material}</div>}
            </div>
            <div className="flex items-center gap-2 ml-3">
              <select
                value={d.status}
                onChange={e => handleStatusChange(d.id, e.target.value)}
                className={`text-[9px] font-bold px-1.5 py-0.5 rounded border-0 cursor-pointer ${statusColors[d.status] || statusColors.concept}`}
              >
                {Object.keys(statusColors).map(s => (
                  <option key={s} value={s}>{s.toUpperCase()}</option>
                ))}
              </select>
              <div className="text-right">
                <div className="text-sm font-bold text-[#c9a84c]">${(d.total || 0).toLocaleString()}</div>
              </div>
              <button
                onClick={() => handleDelete(d.id)}
                className="opacity-0 group-hover:opacity-100 text-[#ccc] hover:text-[#dc2626] transition-all"
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
        {designs.length === 0 && (
          <div className="text-xs text-[#aaa] text-center py-8">
            No designs yet. Click &quot;New Design&quot; to create one.
          </div>
        )}
      </div>
    </div>
  );
}
