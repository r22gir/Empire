/**
 * MarketIntelligencePanel
 * Phase 1 Prototype — displays mock market trends with recharts
 */

'use client';

import { useState, useEffect } from 'react';
import { useMarketTrends } from '../../hooks/useArchiveForgePrototype';
import { ARCHIVEFORGE_PROTOTYPE_DISCLAIMER } from '../../config/archiveforge-mock';

function MarketTemperatureBadge({ temp }: { temp: string }) {
  const config: Record<string, { label: string; variant: 'success' | 'warning' | 'error' | 'default'; icon: string }> = {
    hot: { label: 'HOT', variant: 'success', icon: '🔥' },
    warm: { label: 'WARM', variant: 'warning', icon: '☀️' },
    cool: { label: 'COOL', variant: 'default', icon: '❄️' },
    cold: { label: 'COLD', variant: 'error', icon: '🥶' },
  };
  const c = config[temp] || config.cool;
  const variantColors: Record<string, string> = {
    success: 'bg-green-900/60 text-green-300 border-green-700',
    warning: 'bg-yellow-900/60 text-yellow-300 border-yellow-700',
    error: 'bg-red-900/60 text-red-300 border-red-700',
    default: 'bg-gray-800/60 text-gray-300 border-gray-700',
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs border ${variantColors[c.variant]}`}>
      <span>{c.icon}</span>
      <span>{c.label}</span>
    </span>
  );
}

// Lazy-loaded recharts chart
function TrendChart({ trends }: { trends: { date: string; avgPrice: number; volume: number }[] }) {
  const [chartData, setChartData] = useState<{
    LineChart: React.ComponentType<any>;
    Line: React.ComponentType<any>;
    XAxis: React.ComponentType<any>;
    YAxis: React.ComponentType<any>;
    Tooltip: React.ComponentType<any>;
    ResponsiveContainer: React.ComponentType<any>;
    AreaChart: React.ComponentType<any>;
    Area: React.ComponentType<any>;
  } | null>(null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    import('recharts')
      .then((mod) => {
        setChartData({
          LineChart: mod.LineChart,
          Line: mod.Line,
          XAxis: mod.XAxis,
          YAxis: mod.YAxis,
          Tooltip: mod.Tooltip,
          ResponsiveContainer: mod.ResponsiveContainer,
          AreaChart: mod.AreaChart,
          Area: mod.Area,
        });
      })
      .catch(() => setHasError(true));
  }, []);

  if (hasError || !chartData) {
    return <div className="h-48 flex items-center justify-center text-gray-500 text-sm">Chart unavailable</div>;
  }

  const { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } = chartData;

  const formatted = trends.map((t) => ({
    ...t,
    dateLabel: new Date(t.date).toLocaleString('en-US', { month: 'short', year: '2-digit' }),
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={formatted}>
        <XAxis
          dataKey="dateLabel"
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `$${v}`}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
          width={45}
        />
        <Tooltip
          formatter={(value: number) => [`$${value}`, 'Avg Price']}
          contentStyle={{
            backgroundColor: '#1f2937',
            border: '1px solid #374151',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#f3f4f6',
          }}
        />
        <Line
          type="monotone"
          dataKey="avgPrice"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function TrendRow({ trend }: { trend: { date: string; avgPrice: number; volume: number; trend: string } }) {
  const trendIcon = trend.trend === 'up' ? '↑' : trend.trend === 'down' ? '↓' : '→';
  const trendColor = trend.trend === 'up' ? 'text-green-400' : trend.trend === 'down' ? 'text-red-400' : 'text-gray-400';
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
      <div className="flex items-center gap-3">
        <span className={`text-sm font-medium ${trendColor}`}>{trendIcon}</span>
        <span className="text-gray-300 text-sm">
          {new Date(trend.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
        </span>
      </div>
      <div className="flex items-center gap-4 text-sm">
        <span className="text-gray-300 font-medium">${trend.avgPrice}</span>
        <span className="text-gray-500">{trend.volume} sales</span>
      </div>
    </div>
  );
}

export default function MarketIntelligencePanel() {
  const { data, loading } = useMarketTrends();

  return (
    <div className="space-y-4" data-max-task="market-intelligence-backend-integration">
      {/* Prototype disclaimer */}
      <div className="border border-yellow-600/40 bg-yellow-900/20 rounded-lg p-3 flex items-start gap-2">
        <span className="text-yellow-400 mt-0.5">⚠</span>
        <div>
          <p className="text-yellow-300 text-sm font-medium">Mock market signal — backend integration pending</p>
          <p className="text-yellow-400/70 text-xs mt-0.5">GET /api/v1/market/trends not yet implemented</p>
        </div>
      </div>

      {loading ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-12 bg-gray-700 rounded" />
          <div className="h-48 bg-gray-700 rounded" />
        </div>
      ) : data ? (
        <>
          {/* Market Temperature */}
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700 flex items-center justify-between">
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wide">Market Temperature</p>
              <p className="text-2xl font-bold text-gray-100 mt-1 capitalize">{data.marketTemperature}</p>
            </div>
            <MarketTemperatureBadge temp={data.marketTemperature} />
          </div>

          {/* Trend Chart */}
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-gray-300 text-sm font-medium">Price Trend (12 Months)</h3>
              <span className="text-xs text-gray-500">Updated {data.lastUpdated}</span>
            </div>
            <TrendChart trends={data.trends} />
          </div>

          {/* Monthly Breakdown */}
          <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
            <h3 className="text-gray-300 text-sm font-medium mb-2">Monthly Breakdown</h3>
            <div>
              {data.trends.slice(-6).map((t) => (
                <TrendRow key={t.date} trend={t} />
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="text-center text-gray-500 py-8">No market data available</div>
      )}
    </div>
  );
}
