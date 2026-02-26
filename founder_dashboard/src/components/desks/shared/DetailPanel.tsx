'use client';
import { type ReactNode } from 'react';

interface DetailPanelProps {
  width?: number;
  header: ReactNode;
  children: ReactNode;
}

export default function DetailPanel({ width = 280, header, children }: DetailPanelProps) {
  return (
    <div
      className="rounded-xl overflow-hidden shrink-0 flex flex-col"
      style={{ width, background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <div className="px-4 py-3 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        {header}
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {children}
      </div>
    </div>
  );
}
