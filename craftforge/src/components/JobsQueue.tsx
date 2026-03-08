'use client';
import { ListTodo, Play, CheckCircle } from 'lucide-react';
import { API } from '../lib/api';

const jobStatusColors: Record<string, string> = {
  queued: 'bg-[#f5f3ef] text-[#777]',
  cutting: 'bg-[#fef3c7] text-[#d97706]',
  printing: 'bg-[#ede9fe] text-[#7c3aed]',
  sanding: 'bg-[#fce7f3] text-[#db2777]',
  finishing: 'bg-[#dbeafe] text-[#2563eb]',
  assembly: 'bg-[#fdf8eb] text-[#c9a84c]',
  complete: 'bg-[#dcfce7] text-[#16a34a]',
  shipped: 'bg-[#dcfce7] text-[#16a34a]',
};

const machineIcons: Record<string, string> = {
  'x-carve': '🪚',
  'elegoo-saturn': '🖨️',
  'manual': '🔨',
};

export default function JobsQueue({
  jobs,
  onRefresh,
  full,
}: {
  jobs: any[];
  onRefresh: () => void;
  full?: boolean;
}) {
  const handleStatus = async (id: string, status: string) => {
    await fetch(`${API}/jobs/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    onRefresh();
  };

  const shown = full ? jobs : jobs.slice(0, 6);

  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
      <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
        <ListTodo size={15} className="text-[#16a34a]" />
        {full ? 'All Production Jobs' : 'Production Queue'}
        <span className="text-[10px] text-[#aaa] font-normal ml-auto">{jobs.length} jobs</span>
      </h3>

      <div className="space-y-2">
        {shown.map(j => (
          <div key={j.id} className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] hover:border-[#c9a84c] hover:bg-[#fdf8eb] transition-all">
            <div className="flex items-center gap-2.5">
              <span className="text-lg">{machineIcons[j.machine] || '⚙️'}</span>
              <div>
                <div className="text-xs font-semibold text-[#1a1a1a]">{j.job_number}</div>
                <div className="text-[10px] text-[#777]">{j.customer_name}</div>
                {j.estimated_time_min > 0 && (
                  <div className="text-[9px] text-[#aaa]">~{j.estimated_time_min} min</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${jobStatusColors[j.status] || jobStatusColors.queued}`}>
                {(j.status || 'queued').toUpperCase()}
              </span>
              {j.status === 'queued' && (
                <button
                  onClick={() => handleStatus(j.id, 'cutting')}
                  className="w-6 h-6 rounded bg-[#dcfce7] text-[#16a34a] flex items-center justify-center hover:bg-[#16a34a] hover:text-white transition-colors"
                  title="Start cutting"
                >
                  <Play size={12} />
                </button>
              )}
              {j.status !== 'queued' && j.status !== 'complete' && j.status !== 'shipped' && (
                <button
                  onClick={() => handleStatus(j.id, 'complete')}
                  className="w-6 h-6 rounded bg-[#dcfce7] text-[#16a34a] flex items-center justify-center hover:bg-[#16a34a] hover:text-white transition-colors"
                  title="Mark complete"
                >
                  <CheckCircle size={12} />
                </button>
              )}
            </div>
          </div>
        ))}
        {jobs.length === 0 && (
          <div className="text-xs text-[#aaa] text-center py-8">
            No production jobs yet. Create a design and send it to production.
          </div>
        )}
      </div>
    </div>
  );
}
