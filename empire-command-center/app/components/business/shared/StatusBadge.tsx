'use client';

import React from 'react';

interface StatusBadgeProps {
  status: string;
  colorMap?: Record<string, { bg: string; text: string }>;
}

const DEFAULT_COLORS: Record<string, { bg: string; text: string }> = {
  draft:       { bg: '#f0ede8', text: '#777' },
  sent:        { bg: '#eff6ff', text: '#2563eb' },
  paid:        { bg: '#f0fdf4', text: '#22c55e' },
  overdue:     { bg: '#fef2f2', text: '#dc2626' },
  partial:     { bg: '#fffbeb', text: '#d97706' },
  cancelled:   { bg: '#f0ede8', text: '#999' },
  active:      { bg: '#f0fdf4', text: '#22c55e' },
  inactive:    { bg: '#f0ede8', text: '#999' },
  open:        { bg: '#eff6ff', text: '#2563eb' },
  closed:      { bg: '#f0ede8', text: '#777' },
  done:        { bg: '#f0fdf4', text: '#22c55e' },
  todo:        { bg: '#fffbeb', text: '#d97706' },
  in_progress: { bg: '#faf5ff', text: '#7c3aed' },
};

export default function StatusBadge({ status, colorMap }: StatusBadgeProps) {
  const key = status.toLowerCase().replace(/\s+/g, '_');
  const merged = { ...DEFAULT_COLORS, ...colorMap };

  // Support both old Tailwind class maps and new inline-color maps
  const entry = merged[key] || { bg: '#f0ede8', text: '#777' };
  const display = status.replace(/_/g, ' ');

  // Check if values are Tailwind classes (start with bg- / text-) or hex colors
  const isTailwind = typeof entry.bg === 'string' && entry.bg.startsWith('bg-');

  if (isTailwind) {
    return (
      <span className={`status-pill ${entry.bg} ${entry.text}`}>
        {display}
      </span>
    );
  }

  return (
    <span
      className="status-pill"
      style={{ backgroundColor: entry.bg, color: entry.text }}
    >
      {display}
    </span>
  );
}
