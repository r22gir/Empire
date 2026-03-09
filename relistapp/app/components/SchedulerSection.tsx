'use client';

import { useState } from 'react';
import { Clock, Plus, Calendar, ToggleLeft, ToggleRight, Check, X, AlertCircle } from 'lucide-react';
import { mockSchedules, mockListings, PLATFORM_COLORS } from '../lib/mock-data';
import { Platform } from '../lib/types';

export default function SchedulerSection() {
  const [schedules, setSchedules] = useState(mockSchedules);
  const [showCreate, setShowCreate] = useState(false);

  const toggleSchedule = (id: string) => {
    setSchedules(prev => prev.map(s => s.id === id ? { ...s, enabled: !s.enabled } : s));
  };

  const scheduleHistory = [
    { time: '2026-03-09 09:00', listing: 'Vintage Levi\'s 501 Jeans', platforms: ['ebay', 'etsy'], status: 'success' },
    { time: '2026-03-08 09:00', listing: 'Dyson V11 Torque Drive', platforms: ['ebay'], status: 'success' },
    { time: '2026-03-07 09:00', listing: 'Vintage Levi\'s 501 Jeans', platforms: ['ebay', 'etsy'], status: 'success' },
    { time: '2026-03-06 09:00', listing: 'Dyson V11 Torque Drive', platforms: ['ebay'], status: 'failed' },
    { time: '2026-03-05 09:00', listing: 'Vintage Pyrex Primary Colors Set', platforms: ['ebay', 'etsy'], status: 'success' },
    { time: '2026-03-04 09:00', listing: 'The North Face Nuptse 700 Puffer', platforms: ['ebay', 'poshmark'], status: 'success' },
  ];

  const calendarDays = Array.from({ length: 28 }, (_, i) => {
    const d = new Date('2026-03-09');
    d.setDate(d.getDate() + i);
    return d;
  });

  const getScheduledForDate = (date: Date) => {
    return schedules.filter(s => {
      if (!s.enabled || !s.next_run) return false;
      const next = new Date(s.next_run);
      if (date.toDateString() === next.toDateString()) return true;
      if (s.frequency === 'daily') return true;
      if (s.frequency === 'weekly') {
        const diff = Math.abs(date.getTime() - next.getTime());
        return diff % (7 * 86400000) < 86400000;
      }
      return false;
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Scheduler</h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Manage auto-relist schedules</p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={15} /> New Schedule
        </button>
      </div>

      {/* Create Schedule Form */}
      {showCreate && (
        <div className="empire-card" style={{ borderColor: '#06b6d4' }}>
          <h3 className="font-semibold mb-3">Create New Schedule</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="section-label">Listing</label>
              <select className="form-input text-sm">
                <option value="">Select listing...</option>
                {mockListings.filter(l => l.status === 'active').map(l => (
                  <option key={l.id} value={l.id}>{l.title}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="section-label">Frequency</label>
              <select className="form-input text-sm">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="biweekly">Biweekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            <div>
              <label className="section-label">Platforms</label>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {['ebay', 'etsy', 'shopify', 'facebook'].map(p => (
                  <label key={p} className="flex items-center gap-1 text-xs px-2 py-1 rounded border cursor-pointer hover:bg-gray-50" style={{ borderColor: 'var(--border)' }}>
                    <input type="checkbox" className="accent-cyan-500" />
                    <span className="capitalize">{p}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="btn-primary text-sm">Create Schedule</button>
            <button className="btn-secondary text-sm" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      {/* Active Schedules */}
      <div className="empire-card">
        <div className="section-label mb-3">Active Schedules ({schedules.filter(s => s.enabled).length})</div>
        <div className="space-y-2">
          {schedules.map(schedule => (
            <div
              key={schedule.id}
              className="flex items-center gap-4 p-3 rounded-lg border"
              style={{
                borderColor: schedule.enabled ? 'var(--border)' : '#f3f4f6',
                opacity: schedule.enabled ? 1 : 0.6,
              }}
            >
              <button onClick={() => toggleSchedule(schedule.id)} className="flex-shrink-0">
                {schedule.enabled ? (
                  <ToggleRight size={28} style={{ color: '#06b6d4' }} />
                ) : (
                  <ToggleLeft size={28} style={{ color: 'var(--muted)' }} />
                )}
              </button>

              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{schedule.listing_title}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: '#f3f4f6', color: 'var(--text-secondary)' }}>
                    {schedule.frequency}
                  </span>
                  <div className="flex gap-0.5">
                    {schedule.platforms.map(p => (
                      <div key={p} className={`platform-dot ${p}`} />
                    ))}
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-xs" style={{ color: 'var(--muted)' }}>Next run</div>
                <div className="text-sm font-medium">
                  {schedule.next_run ? new Date(schedule.next_run).toLocaleDateString() : '—'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Calendar View */}
      <div className="empire-card">
        <div className="section-label mb-3">Upcoming Relists (Next 4 Weeks)</div>
        <div className="grid grid-cols-7 gap-1">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
            <div key={d} className="text-center text-xs font-medium py-1" style={{ color: 'var(--muted)' }}>{d}</div>
          ))}
          {/* Pad start */}
          {Array.from({ length: calendarDays[0].getDay() }, (_, i) => (
            <div key={`pad-${i}`} />
          ))}
          {calendarDays.map(date => {
            const scheduled = getScheduledForDate(date);
            const isToday = date.toDateString() === new Date('2026-03-09').toDateString();
            return (
              <div
                key={date.toISOString()}
                className="p-1 rounded-lg text-center min-h-[48px]"
                style={{
                  background: isToday ? '#ecfeff' : scheduled.length > 0 ? '#fdf8eb' : '#f9fafb',
                  border: isToday ? '1px solid #06b6d4' : '1px solid transparent',
                }}
              >
                <div className="text-xs font-medium">{date.getDate()}</div>
                {scheduled.length > 0 && (
                  <div className="flex justify-center gap-0.5 mt-0.5">
                    {scheduled.slice(0, 3).map((s, i) => (
                      <div key={i} className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--gold)' }} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Schedule History */}
      <div className="empire-card">
        <div className="section-label mb-3">Recent Auto-Relists</div>
        <table className="empire-table text-sm">
          <thead><tr><th>Time</th><th>Listing</th><th>Platforms</th><th>Status</th></tr></thead>
          <tbody>
            {scheduleHistory.map((h, i) => (
              <tr key={i}>
                <td style={{ color: 'var(--muted)' }}>{h.time}</td>
                <td className="font-medium">{h.listing}</td>
                <td>
                  <div className="flex gap-1">
                    {h.platforms.map(p => (
                      <span key={p} className="text-xs capitalize" style={{ color: PLATFORM_COLORS[p] }}>{p}</span>
                    ))}
                  </div>
                </td>
                <td>
                  {h.status === 'success' ? (
                    <span className="status-pill active"><Check size={11} /> Success</span>
                  ) : (
                    <span className="status-pill error"><AlertCircle size={11} /> Failed</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
