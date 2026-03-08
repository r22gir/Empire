'use client';

import React from 'react';

interface StatusBadgeProps {
  status: string;
  colorMap?: Record<string, { bg: string; text: string }>;
}

const DEFAULT_COLORS: Record<string, { bg: string; text: string }> = {
  draft:       { bg: 'bg-gray-100',    text: 'text-gray-600' },
  sent:        { bg: 'bg-blue-50',     text: 'text-blue-700' },
  paid:        { bg: 'bg-green-50',    text: 'text-green-700' },
  overdue:     { bg: 'bg-red-50',      text: 'text-red-700' },
  partial:     { bg: 'bg-amber-50',    text: 'text-amber-700' },
  cancelled:   { bg: 'bg-gray-100',    text: 'text-gray-500' },
  active:      { bg: 'bg-green-50',    text: 'text-green-700' },
  inactive:    { bg: 'bg-gray-100',    text: 'text-gray-500' },
  open:        { bg: 'bg-blue-50',     text: 'text-blue-700' },
  closed:      { bg: 'bg-gray-100',    text: 'text-gray-600' },
  done:        { bg: 'bg-green-50',    text: 'text-green-700' },
  todo:        { bg: 'bg-yellow-50',   text: 'text-yellow-700' },
  in_progress: { bg: 'bg-purple-50',   text: 'text-purple-700' },
};

export default function StatusBadge({ status, colorMap }: StatusBadgeProps) {
  const key = status.toLowerCase().replace(/\s+/g, '_');
  const merged = { ...DEFAULT_COLORS, ...colorMap };
  const colors = merged[key] || { bg: 'bg-gray-100', text: 'text-gray-600' };
  const display = status.replace(/_/g, ' ');

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${colors.bg} ${colors.text}`}>
      {display}
    </span>
  );
}
