'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { BusinessTab } from '../../lib/types';
import { Zap, DollarSign, ClipboardList, Package, Truck, Megaphone, Headphones, TrendingUp, Users, Shield, AlertTriangle, CheckCircle, Activity } from 'lucide-react';

export default function DashboardScreen({ activeTab }: { activeTab: BusinessTab }) {
  const [quotes, setQuotes] = useState<any[]>([]);
  const [accuracy, setAccuracy] = useState<any>(null);
  const [accuracyLoading, setAccuracyLoading] = useState(true);

  useEffect(() => {
    fetch(API + '/quotes?limit=10').then(r => r.json()).then(data => {
      setQuotes(data.quotes || data || []);
    }).catch(() => {});

    fetch(API + '/max/accuracy/stats?days=7')
      .then(r => r.json())
      .then(data => { setAccuracy(data); setAccuracyLoading(false); })
      .catch(() => { setAccuracyLoading(false); });
  }, []);

  const openQuotes = quotes.filter(q => q.status !== 'accepted').length;
  const pipeline = quotes.reduce((sum: number, q: any) => sum + (q.total || 0), 0);

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-9 py-6" style={{ background: '#f5f2ed' }}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
          <Zap size={20} className="text-[#b8960c]" />
        </div>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Empire Command Center</h1>
          <p style={{ fontSize: 13, color: '#aaa', margin: 0 }} suppressHydrationWarning>All Businesses Overview · {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
        </div>
      </div>

      {/* KPI Cards - Row 1 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 mb-4">
        <KPI icon={<DollarSign size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Pipeline" value={`$${pipeline.toLocaleString()}`} sub={`${quotes.length} quotes total`} />
        <KPI icon={<ClipboardList size={18} />} iconBg="#fef3c7" iconColor="#d97706" label="Open Quotes" value={String(openQuotes)} sub="Active proposals" />
        <KPI icon={<Package size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Inventory" value="--" sub="Fabrics · Hardware · Motors" />
        <KPI icon={<Truck size={18} />} iconBg="#dbeafe" iconColor="#2563eb" label="Shipments" value="--" sub="Check shipping status" />
      </div>

      {/* KPI Cards - Row 2 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <KPI icon={<Megaphone size={18} />} iconBg="#fce7f3" iconColor="#ec4899" label="Social" value="--" sub="SocialForge status" />
        <KPI icon={<Headphones size={18} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Support" value="0" sub="No open tickets" />
        <KPI icon={<TrendingUp size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Revenue MTD" value="--" sub="Month to date" />
        <KPI icon={<Users size={18} />} iconBg="#dbeafe" iconColor="#2563eb" label="Leads" value="--" sub="New inquiries" />
      </div>

      {/* Business Summary Cards */}
      <div className="section-label" style={{ marginBottom: 8 }}>Businesses</div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <BizCard name="Empire Workroom" icon="🏗" color="#16a34a"
          stats={[`${quotes.length} quotes`, `$${pipeline.toLocaleString()} pipeline`]} />
        <BizCard name="WoodCraft" icon="🪵" color="#ca8a04"
          stats={['AI design engine ready', 'Store integration pending']} />
        <BizCard name="Platform" icon="🌐" color="#2563eb"
          stats={['All services monitored', 'AI routing active']} />
      </div>

      {/* MAX Accuracy */}
      <div className="section-label flex items-center gap-2" style={{ marginBottom: 8 }}>
        <Shield size={14} className="text-[#b8960c]" />
        MAX Accuracy
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <KPI
          icon={<CheckCircle size={18} />}
          iconBg={accuracy && accuracy.accuracy_rate >= 90 ? '#dcfce7' : accuracy && accuracy.accuracy_rate >= 70 ? '#fef3c7' : '#fee2e2'}
          iconColor={accuracy && accuracy.accuracy_rate >= 90 ? '#16a34a' : accuracy && accuracy.accuracy_rate >= 70 ? '#d97706' : '#dc2626'}
          label="Accuracy"
          value={accuracyLoading ? '...' : accuracy ? `${accuracy.accuracy_rate.toFixed(1)}%` : '--'}
          sub="Last 7 days"
        />
        <KPI
          icon={<Activity size={18} />}
          iconBg="#fdf8eb"
          iconColor="#b8960c"
          label="Total Queries"
          value={accuracyLoading ? '...' : accuracy ? String(accuracy.total_queries) : '--'}
          sub="Queries processed"
        />
        <KPI
          icon={<AlertTriangle size={18} />}
          iconBg="#fee2e2"
          iconColor="#dc2626"
          label="Flagged"
          value={accuracyLoading ? '...' : accuracy ? String(accuracy.fail_count) : '--'}
          sub="Failed checks"
        />
        <KPI
          icon={<Shield size={18} />}
          iconBg="#ede9fe"
          iconColor="#7c3aed"
          label="Avg Confidence"
          value={accuracyLoading ? '...' : accuracy ? `${(accuracy.avg_confidence * 100).toFixed(0)}%` : '--'}
          sub="Model confidence"
        />
      </div>
      {accuracy?.trend && accuracy.trend.length > 0 && (
        <div className="empire-card mb-6" style={{ padding: '16px 20px' }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#aaa', marginBottom: 12 }}>Daily Accuracy Trend</div>
          <div className="flex items-end gap-2" style={{ height: 60 }}>
            {accuracy.trend.slice().reverse().map((day: any, i: number) => {
              const barColor = day.accuracy >= 90 ? '#16a34a' : day.accuracy >= 70 ? '#d97706' : '#dc2626';
              return (
                <div key={i} className="flex flex-col items-center flex-1" style={{ gap: 4 }}>
                  <div style={{ fontSize: 9, color: '#aaa', fontWeight: 600 }}>{day.accuracy.toFixed(0)}%</div>
                  <div
                    style={{
                      width: '100%',
                      maxWidth: 32,
                      height: `${Math.max(day.accuracy * 0.55, 4)}px`,
                      background: barColor,
                      borderRadius: 3,
                      transition: 'height 0.3s ease',
                    }}
                  />
                  <div style={{ fontSize: 8, color: '#bbb' }}>
                    {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {!accuracy?.trend && !accuracyLoading && (
        <div className="empire-card mb-6" style={{ minHeight: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ fontSize: 12, color: '#aaa' }}>No trend data available</div>
        </div>
      )}

      {/* Revenue chart placeholder */}
      <div className="empire-card" style={{ minHeight: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="text-center">
          <TrendingUp size={36} className="text-[#d8d3cb] mx-auto mb-2" />
          <div style={{ fontSize: 13, fontWeight: 600, color: '#aaa' }}>Revenue Chart · Monthly Trend</div>
          <div style={{ fontSize: 11, color: '#ccc', marginTop: 4 }}>Click to expand · All businesses combined</div>
        </div>
      </div>
    </div>
  );
}

function KPI({ icon, iconBg, iconColor, label, value, sub }: { icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string }) {
  return (
    <div className="empire-card" style={{ cursor: 'pointer' }}>
      <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: iconBg, color: iconColor }}>{icon}</div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

function BizCard({ name, icon, color, stats }: { name: string; icon: string; color: string; stats: string[] }) {
  return (
    <div className="empire-card" style={{ cursor: 'pointer' }}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color }}>{name}</span>
      </div>
      {stats.map((s, i) => (
        <div key={i} className="flex items-center gap-1.5 mb-1" style={{ fontSize: 12, color: '#555' }}>
          <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
          {s}
        </div>
      ))}
    </div>
  );
}
