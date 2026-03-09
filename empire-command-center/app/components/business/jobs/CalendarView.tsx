'use client';
import { useState, useEffect, useMemo } from 'react';
import { API } from '../../../lib/api';
import { ChevronLeft, ChevronRight, Loader2, Calendar } from 'lucide-react';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  pending:     { bg: '#f0ede8', text: '#777' },
  scheduled:   { bg: '#dbeafe', text: '#2563eb' },
  in_progress: { bg: '#fef3c7', text: '#d97706' },
  completed:   { bg: '#dcfce7', text: '#22c55e' },
};

export default function CalendarView() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(() => new Date());

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/jobs/calendar`)
      .then(r => r.json())
      .then(data => {
        setJobs(Array.isArray(data) ? data : data.jobs || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));

  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  // Build calendar grid
  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const days: { day: number | null; dateStr: string }[] = [];

    for (let i = 0; i < firstDay; i++) {
      days.push({ day: null, dateStr: '' });
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({ day: d, dateStr });
    }
    return days;
  }, [year, month]);

  // Map jobs to dates
  const jobsByDate = useMemo(() => {
    const map: Record<string, any[]> = {};
    for (const job of jobs) {
      const date = job.scheduled_date || job.due_date || job.date;
      if (!date) continue;
      const key = date.substring(0, 10);
      if (!map[key]) map[key] = [];
      map[key].push(job);
    }
    return map;
  }, [jobs]);

  const monthLabel = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto flex items-center justify-center min-h-[400px]" style={{ padding: '24px 36px' }}>
        <Loader2 size={24} className="text-[#22c55e] animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto" style={{ padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-bold text-[#1a1a1a] flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-[#f0fdf4] flex items-center justify-center">
            <Calendar size={18} className="text-[#22c55e]" />
          </div>
          Job Calendar
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="p-2 rounded-xl border border-[#ece8e0] bg-[#faf9f7] hover:bg-white transition-colors cursor-pointer">
            <ChevronLeft size={16} className="text-[#999]" />
          </button>
          <span className="text-sm font-bold text-[#1a1a1a] min-w-[160px] text-center" suppressHydrationWarning>{monthLabel}</span>
          <button onClick={nextMonth} className="p-2 rounded-xl border border-[#ece8e0] bg-[#faf9f7] hover:bg-white transition-colors cursor-pointer">
            <ChevronRight size={16} className="text-[#999]" />
          </button>
        </div>
      </div>

      <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
        {/* Day headers */}
        <div className="grid grid-cols-7" style={{ borderBottom: '1px solid #ece8e0' }}>
          {DAYS.map(day => (
            <div key={day} className="px-2 py-2.5 text-center text-[10px] font-bold text-[#999] uppercase bg-[#faf9f7]">
              {day}
            </div>
          ))}
        </div>

        {/* Calendar grid */}
        <div className="grid grid-cols-7">
          {calendarDays.map(({ day, dateStr }, i) => {
            const isToday = dateStr === todayStr;
            const dayJobs = jobsByDate[dateStr] || [];
            const hasJobs = dayJobs.length > 0;

            return (
              <div
                key={i}
                className="min-h-[90px] p-1.5"
                style={{
                  borderBottom: '1px solid #ece8e0',
                  borderRight: '1px solid #ece8e0',
                  background: day === null ? '#faf9f7' : '#fff',
                  ...(isToday ? { boxShadow: 'inset 0 0 0 2px #b8960c', borderRadius: 0 } : {}),
                }}
              >
                {day !== null && (
                  <>
                    <div className={`text-xs font-bold mb-1 ${isToday ? 'text-[#b8960c]' : 'text-[#555]'}`}>
                      {day}
                    </div>
                    {hasJobs && (
                      <div className="space-y-0.5">
                        <div className="text-[9px] font-bold text-[#999]">{dayJobs.length} job{dayJobs.length !== 1 ? 's' : ''}</div>
                        {dayJobs.slice(0, 2).map((job, ji) => {
                          const status = (job.status || 'pending').toLowerCase();
                          const colors = STATUS_COLORS[status] || STATUS_COLORS.pending;
                          return (
                            <div key={ji} className="text-[8px] font-medium px-1.5 py-0.5 rounded-md truncate" style={{ backgroundColor: colors.bg, color: colors.text }}>
                              {job.title || 'Untitled'}
                            </div>
                          );
                        })}
                        {dayJobs.length > 2 && (
                          <div className="text-[8px] text-[#999]">+{dayJobs.length - 2} more</div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
