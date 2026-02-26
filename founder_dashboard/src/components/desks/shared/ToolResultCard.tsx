'use client';
import { ToolResult } from '@/lib/types';
import { CheckCircle2, XCircle } from 'lucide-react';

export default function ToolResultCard({ result }: { result: ToolResult }) {
  if (result.tool === 'create_task' && result.success && result.result) {
    const r = result.result;
    return (
      <div
        className="rounded-lg px-3 py-2.5 my-2 text-xs"
        style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.25)' }}
      >
        <div className="flex items-center gap-1.5 mb-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
          <span className="font-semibold text-green-400">Task Created</span>
        </div>
        <p className="font-medium" style={{ color: 'var(--text-primary)' }}>{String(r.title)}</p>
        {r.due_date ? (
          <p style={{ color: 'var(--text-secondary)' }}>Due: {String(r.due_date)}</p>
        ) : null}
        <p style={{ color: 'var(--text-muted)' }}>
          {String(r.priority)} &middot; {String(r.desk)} desk
        </p>
      </div>
    );
  }

  // Generic fallback
  return (
    <div
      className="rounded-lg px-3 py-2.5 my-2 text-xs"
      style={{
        background: result.success ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
        border: `1px solid ${result.success ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)'}`,
      }}
    >
      <div className="flex items-center gap-1.5">
        {result.success
          ? <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
          : <XCircle className="w-3.5 h-3.5 text-red-400" />}
        <span className={result.success ? 'text-green-400 font-semibold' : 'text-red-400 font-semibold'}>
          {result.tool}: {result.success ? 'Success' : 'Failed'}
        </span>
      </div>
      {result.error && <p className="mt-1 text-red-300">{result.error}</p>}
    </div>
  );
}
