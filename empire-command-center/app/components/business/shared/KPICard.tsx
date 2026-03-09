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
}

export default function KPICard({ icon, label, value, trend, trendUp, color = '#b8960c' }: KPICardProps) {
  return (
    <div className="empire-card" style={{ padding: 20 }}>
      <div className="flex items-center gap-3">
        <div
          className="flex items-center justify-center w-10 h-10 rounded-xl shrink-0"
          style={{ backgroundColor: `${color}12` }}
        >
          <span style={{ color }}>{icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="kpi-label">{label}</p>
          <p className="kpi-value truncate">{value}</p>
          {trend && (
            <div className={`flex items-center gap-1 mt-1 text-[11px] font-semibold ${trendUp ? 'text-[#22c55e]' : 'text-red-500'}`}>
              {trendUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              <span>{trend} vs last month</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
