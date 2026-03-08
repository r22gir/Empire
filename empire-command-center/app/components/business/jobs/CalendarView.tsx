'use client';
import { useState, useEffect, useMemo } from 'react';
import { API } from '../../../lib/api';
import { ChevronLeft, ChevronRight, Loader2, Calendar } from 'lucide-react';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

const STATUS_COLORS: Record<string, string> = {
  pending:     'bg-gray-200 text-gray-700',
  scheduled:   'bg-blue-100 text-blue-700',
  in_progress: 'bg-amber-100 text-amber-700',
  completed:   'bg-green-100 text-green-700',
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

    // Leading blanks
    for (let i = 0; i < firstDay; i++) {
      days.push({ day: null, dateStr: '' });
    }
    // Days of month
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
      const key = date.substring(0, 10); // YYYY-MM-DD
      if (!map[key]) map[key] = [];
      map[key].push(job);
    }
    return map;
  }, [jobs]);

  const monthLabel = currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-8 py-6 flex items-center justify-center min-h-[400px]">
        <Loader2 size={24} className="text-[#16a34a] animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-8 py-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-bold text-[#1a1a1a] flex items-center gap-2">
          <Calendar size={20} className="text-[#16a34a]" /> Job Calendar
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="p-1.5 rounded-lg border border-[#ece8e1] hover:bg-[#f5f3ef] transition-colors cursor-pointer">
            <ChevronLeft size={16} className="text-[#777]" />
          </button>
          <span className="text-sm font-bold text-[#1a1a1a] min-w-[160px] text-center" suppressHydrationWarning>{monthLabel}</span>
          <button onClick={nextMonth} className="p-1.5 rounded-lg border border-[#ece8e1] hover:bg-[#f5f3ef] transition-colors cursor-pointer">
            <ChevronRight size={16} className="text-[#777]" />
          </button>
        </div>
      </div>

      <div className="bg-white border border-[#e5e0d8] rounded-xl overflow-hidden">
        {/* Day headers */}
        <div className="grid grid-cols-7 border-b border-[#ece8e1]">
          {DAYS.map(day => (
            <div key={day} className="px-2 py-2.5 text-center text-[10px] font-bold text-[#999] uppercase bg-[#f5f3ef]">
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
                className={`min-h-[90px] p-1.5 border-b border-r border-[#ece8e1] ${
                  day === null ? 'bg-[#faf9f7]' : 'bg-white'
                } ${isToday ? 'ring-2 ring-inset ring-[#b8960c]' : ''}`}
              >
                {day !== null && (
                  <>
                    <div className={`text-xs font-bold mb-1 ${isToday ? 'text-[#b8960c]' : 'text-[#555]'}`}>
                      {day}
                    </div>
                    {hasJobs && (
                      <div className="space-y-0.5">
                        <div className="text-[9px] font-bold text-[#777]">{dayJobs.length} job{dayJobs.length !== 1 ? 's' : ''}</div>
                        {dayJobs.slice(0, 2).map((job, ji) => {
                          const status = (job.status || 'pending').toLowerCase();
                          const colorClass = STATUS_COLORS[status] || STATUS_COLORS.pending;
                          return (
                            <div key={ji} className={`text-[8px] font-medium px-1 py-0.5 rounded truncate ${colorClass}`}>
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
