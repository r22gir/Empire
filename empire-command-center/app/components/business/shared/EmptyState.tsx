'use client';

import React from 'react';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="empire-card" style={{ padding: '48px 20px', textAlign: 'center' }}>
      <div className="text-[#d8d3cb] mb-4 flex justify-center">{icon}</div>
      <h3 className="text-sm font-semibold text-[#777] mb-1">{title}</h3>
      {description && <p className="text-[11px] text-[#999] mb-5 max-w-xs mx-auto">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2.5 text-xs font-bold text-white bg-[#b8960c] rounded-[10px] hover:bg-[#a68500] transition-colors cursor-pointer"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
