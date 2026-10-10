'use client';

import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface KPICardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend?: string;
  trendUp?: boolean;
  color?: string;
  onClick?: () => void;
  title?: string;
  badge?: string;
}

export default function KPICard({ icon, label, value, trend, trendUp, color = '#b8960c', onClick, title, badge }: KPICardProps) {
  const isClickable = Boolean(onClick);
  return (
    <div
      className={`empire-card ${isClickable ? 'cursor-pointer hover:shadow-md transition-all active:scale-[0.99]' : ''}`}
      style={{
        padding: '12px 14px',
        outline: 'none',
        minHeight: '64px',
      }}
      onClick={onClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      title={title || (isClickable ? `Click to view ${label} details` : undefined)}
      onKeyDown={(e) => {
        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-xl shrink-0"
          style={{ backgroundColor: `${color}12` }}
        >
          <span style={{ color }}>{icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-1">
            <p className="kpi-label" style={{ fontSize: 11 }}>{label}</p>
            {badge && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 4, background: `${color}20`, color, whiteSpace: 'nowrap' }}>
                {badge}
              </span>
            )}
          </div>
          <p
            className="kpi-value"
            style={{
              fontSize: 'clamp(14px, 3.5vw, 20px)',
              fontWeight: 700,
              lineHeight: 1.2,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {value}
          </p>
          {trend && (
            <div className={`flex items-center gap-1 mt-0.5 text-[10px] font-semibold ${trendUp ? 'text-[#22c55e]' : 'text-red-500'}`}>
              {trendUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
              <span className="truncate">{trend} vs last mo</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
