'use client';

interface StatusBadgeProps {
  label: string;
  color: string;
}

export default function StatusBadge({ label, color }: StatusBadgeProps) {
  return (
    <span
      className="px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize"
      style={{ background: color + '18', color }}
    >
      {label.replace(/_/g, ' ')}
    </span>
  );
}
