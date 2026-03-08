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
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="text-gray-300 mb-4">{icon}</div>
      <h3 className="text-sm font-semibold text-gray-500 mb-1">{title}</h3>
      {description && <p className="text-xs text-gray-400 mb-4 text-center max-w-xs">{description}</p>}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 text-xs font-medium text-white bg-[#b8960c] rounded-lg hover:bg-[#a68500] transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
