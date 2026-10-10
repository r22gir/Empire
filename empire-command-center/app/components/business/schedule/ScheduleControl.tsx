'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  Calendar as CalendarIcon,
  Clock,
  MapPin,
  CheckCircle,
  Circle,
  Plus,
  Truck,
  PackageCheck,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Loader2,
  AlertCircle,
  Sparkles,
  ClipboardList,
  Wrench,
  Search,
  Check,
  X,
  FileText
} from 'lucide-react';

export type EventType =
  | 'install'
  | 'delivery'
  | 'pickup'
  | 'drop_off'
  | 'fabric_pickup'
  | 'measure'
  | 'loading_dock'
  | 'errand'
  | 'other';

export interface ScheduleEvent {
  id: string;
  type: EventType;
  title: string;
  job_id?: string | null;
  customer_vendor?: string | null;
  location_address?: string | null;
  start_time: string;
  end_time?: string | null;
  status: 'planned' | 'confirmed' | 'done' | 'cancelled';
  notes?: string | null;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PickupDropoffLog {
  id: string;
  schedule_event_id?: string | null;
  job_id?: string | null;
  timestamp: string;
  direction: 'picked_up' | 'dropped_off';
  items: string;
  party?: string | null;
  notes?: string | null;
  created_by?: string;
}

export interface TodaySummary {
  date: string;
  total_events_today: number;
  upcoming_events_count: number;
  counts_by_type: Record<string, number>;
  events_today: ScheduleEvent[];
  pickup_dropoff_today: PickupDropoffLog[];
}

interface ScheduleControlProps {
  business?: string;
  initialJobId?: string;
}

const TYPE_CONFIG: Record<
  EventType,
  { label: string; bgLight: string; textLight: string; darkBg: string; darkText: string; icon: any }
> = {
  install: {
    label: 'Install',
    bgLight: '#eff6ff',
    textLight: '#1d4ed8',
    darkBg: 'rgba(37,99,235,0.2)',
    darkText: '#60a5fa',
    icon: Wrench,
  },
  delivery: {
    label: 'Delivery',
    bgLight: '#fef3c7',
    textLight: '#b45309',
    darkBg: 'rgba(245,158,11,0.2)',
    darkText: '#fbbf24',
    icon: Truck,
  },
  pickup: {
    label: 'Pickup',
    bgLight: '#fdf8eb',
    textLight: '#92400e',
    darkBg: 'rgba(217,119,6,0.2)',
    darkText: '#fcd34d',
    icon: PackageCheck,
  },
  drop_off: {
    label: 'Drop-off',
    bgLight: '#f0fdf4',
    textLight: '#15803d',
    darkBg: 'rgba(22,163,74,0.2)',
    darkText: '#4ade80',
    icon: PackageCheck,
  },
  fabric_pickup: {
    label: 'Fabric Pickup',
    bgLight: '#faf5ff',
    textLight: '#7e22ce',
    darkBg: 'rgba(124,58,237,0.2)',
    darkText: '#c084fc',
    icon: ClipboardList,
  },
  measure: {
    label: 'Measure',
    bgLight: '#e0f2fe',
    textLight: '#0369a1',
    darkBg: 'rgba(6,182,212,0.2)',
    darkText: '#38bdf8',
    icon: Clock,
  },
  loading_dock: {
    label: 'Loading Dock',
    bgLight: '#fee2e2',
    textLight: '#b91c1c',
    darkBg: 'rgba(220,38,38,0.2)',
    darkText: '#f87171',
    icon: Truck,
  },
  errand: {
    label: 'Errand',
    bgLight: '#f3f4f6',
    textLight: '#374151',
    darkBg: 'rgba(107,114,128,0.2)',
    darkText: '#9ca3af',
    icon: Clock,
  },
  other: {
    label: 'Other',
    bgLight: '#f4f4f5',
    textLight: '#52525b',
    darkBg: 'rgba(113,113,122,0.2)',
    darkText: '#a1a1aa',
    icon: CalendarIcon,
  },
};

const DAYS_OF_WEEK = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

export default function ScheduleControl({ business, initialJobId }: ScheduleControlProps) {
  const [viewMode, setViewMode] = useState<'agenda' | 'week' | 'month'>('agenda');
  const [activeDate, setActiveDate] = useState(() => new Date());
  const [events, setEvents] = useState<ScheduleEvent[]>([]);
  const [logs, setLogs] = useState<PickupDropoffLog[]>([]);
  const [todaySummary, setTodaySummary] = useState<TodaySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [jobs, setJobs] = useState<any[]>([]);

  // Modals & Panels
  const [showAddModal, setShowAddModal] = useState(false);
  const [quickAddType, setQuickAddType] = useState<EventType>('pickup');
  const [showCustodyModal, setShowCustodyModal] = useState(false);
  const [selectedEventForDone, setSelectedEventForDone] = useState<ScheduleEvent | null>(null);
  const [showProposalHelper, setShowProposalHelper] = useState(false);

  // Quick / Event Form State
  const [formTitle, setFormTitle] = useState('');
  const [formType, setFormType] = useState<EventType>('pickup');
  const [formJobId, setFormJobId] = useState<string>(initialJobId || '');
  const [formCustomerVendor, setFormCustomerVendor] = useState('');
  const [formLocation, setFormLocation] = useState('');
  const [formDate, setFormDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [formStartTime, setFormStartTime] = useState('10:00');
  const [formEndTime, setFormEndTime] = useState('11:00');
  const [formNotes, setFormNotes] = useState('');
  const [savingEvent, setSavingEvent] = useState(false);
  const [formError, setFormError] = useState('');

  // Custody Log Modal Form
  const [custodyDirection, setCustodyDirection] = useState<'picked_up' | 'dropped_off'>('picked_up');
  const [custodyItems, setCustodyItems] = useState('cushion covers');
  const [custodyParty, setCustodyParty] = useState('');
  const [custodyJobId, setCustodyJobId] = useState(initialJobId || '');
  const [custodyNotes, setCustodyNotes] = useState('');
  const [savingCustody, setSavingCustody] = useState(false);

  // Proposal Draft Helper State
  const [proposalText, setProposalText] = useState('');
  const [extractingProposals, setExtractingProposals] = useState(false);
  const [proposalsResult, setProposalsResult] = useState<any[]>([]);
  const [proposalNotice, setProposalNotice] = useState('');

  // Fetch Jobs list for dropdown picker
  useEffect(() => {
    fetch(`${API}/jobs`)
      .then((r) => r.json())
      .then((d) => setJobs(d.jobs || d || []))
      .catch(() => {});
  }, []);

  // Fetch Data
  const loadScheduleData = useCallback(async () => {
    setLoading(true);
    try {
      const [eventsRes, summaryRes, logsRes] = await Promise.all([
        fetch(`${API}/schedule/events?limit=200`),
        fetch(`${API}/schedule/today-summary`),
        fetch(`${API}/schedule/pickup-dropoff-logs?limit=50`),
      ]);

      if (eventsRes.ok) {
        const evData = await eventsRes.json();
        setEvents(evData.events || []);
      }
      if (summaryRes.ok) {
        const sData = await summaryRes.json();
        setTodaySummary(sData);
      }
      if (logsRes.ok) {
        const lData = await logsRes.json();
        setLogs(lData.logs || []);
      }
    } catch (e) {
      console.error('Failed to load schedule data:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadScheduleData();
  }, [loadScheduleData]);

  // Date Navigation Helpers
  const todayStr = useMemo(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }, []);

  const navigateDate = (delta: number) => {
    const next = new Date(activeDate);
    if (viewMode === 'month') {
      next.setMonth(next.getMonth() + delta);
    } else if (viewMode === 'week') {
      next.setDate(next.getDate() + delta * 7);
    } else {
      next.setDate(next.getDate() + delta);
    }
    setActiveDate(next);
  };

  const jumpToToday = () => {
    setActiveDate(new Date());
  };

  // Open Quick Add Modal
  const openQuickAdd = (type: EventType) => {
    setQuickAddType(type);
    setFormType(type);
    const label = TYPE_CONFIG[type]?.label || 'Event';
    setFormTitle(label);
    setFormDate(todayStr);
    setFormStartTime('10:00');
    setFormEndTime('11:00');
    setFormCustomerVendor('');
    setFormLocation('');
    setFormNotes('');
    setFormJobId(initialJobId || '');
    setFormError('');
    setShowAddModal(true);
  };

  // Create Event Handler
  const handleSaveEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) {
      setFormError('Please enter a title');
      return;
    }
    setSavingEvent(true);
    setFormError('');

    const startISO = `${formDate}T${formStartTime}:00`;
    const endISO = formEndTime ? `${formDate}T${formEndTime}:00` : null;

    try {
      const res = await fetch(`${API}/schedule/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: formTitle.trim(),
          type: formType,
          job_id: formJobId || null,
          customer_vendor: formCustomerVendor.trim() || null,
          location_address: formLocation.trim() || null,
          start_time: startISO,
          end_time: endISO,
          status: 'planned',
          notes: formNotes.trim() || null,
          created_by: 'manual',
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to save event');
      }

      setShowAddModal(false);
      await loadScheduleData();
    } catch (err: any) {
      setFormError(err.message || 'Error saving event');
    } finally {
      setSavingEvent(false);
    }
  };

  // Checkbox 'Done' Action
  const handleCheckDone = (event: ScheduleEvent) => {
    if (event.status === 'done') {
      // Revert to planned
      fetch(`${API}/schedule/events/${event.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'planned' }),
      }).then(() => loadScheduleData());
      return;
    }

    // If it's a pickup, drop_off, delivery, or fabric_pickup, prompt custody details
    if (['pickup', 'drop_off', 'delivery', 'fabric_pickup'].includes(event.type)) {
      setSelectedEventForDone(event);
      setCustodyDirection(event.type === 'pickup' || event.type === 'fabric_pickup' ? 'picked_up' : 'dropped_off');
      setCustodyParty(event.customer_vendor || '');
      setCustodyJobId(event.job_id || '');
      setCustodyNotes(`Completed from scheduled event: ${event.title}`);
      setShowCustodyModal(true);
    } else {
      // Mark done directly
      fetch(`${API}/schedule/events/${event.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'done' }),
      }).then(() => loadScheduleData());
    }
  };

  // Submit Custody Log + Mark Done
  const handleSaveCustodyLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!custodyItems.trim()) return;
    setSavingCustody(true);

    try {
      const res = await fetch(`${API}/schedule/pickup-dropoff-logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          schedule_event_id: selectedEventForDone?.id || null,
          job_id: custodyJobId || null,
          direction: custodyDirection,
          items: custodyItems.trim(),
          party: custodyParty.trim() || null,
          notes: custodyNotes.trim() || null,
          created_by: 'manual',
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to create pickup/drop-off log');
      }

      setShowCustodyModal(false);
      setSelectedEventForDone(null);
      await loadScheduleData();
    } catch (e: any) {
      alert(e.message || 'Error recording log');
    } finally {
      setSavingCustody(false);
    }
  };

  // Propose Draft Events from Email / Text
  const handleAnalyzeDraftProposals = async () => {
    if (!proposalText.trim()) return;
    setExtractingProposals(true);
    setProposalNotice('');

    try {
      const res = await fetch(`${API}/schedule/propose-events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: proposalText }),
      });
      if (res.ok) {
        const data = await res.json();
        setProposalsResult(data.proposals || []);
        setProposalNotice(data.notice || 'Draft proposals extracted.');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setExtractingProposals(false);
    }
  };

  // Confirm and Create One of the Proposed Events
  const handleConfirmProposedEvent = async (p: any) => {
    try {
      const res = await fetch(`${API}/schedule/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: p.title || 'Scheduled Event',
          type: p.type || 'other',
          job_id: p.job_id || null,
          customer_vendor: p.customer_vendor || null,
          location_address: p.location_address || null,
          start_time: p.start_time,
          end_time: p.end_time || null,
          status: 'confirmed',
          notes: p.notes || null,
          created_by: 'max',
        }),
      });
      if (res.ok) {
        // Remove from list
        setProposalsResult((prev) => prev.filter((item) => item !== p));
        await loadScheduleData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Agenda Filter Logic
  const agendaEvents = useMemo(() => {
    const today = new Date().toISOString().split('T')[0];
    const todayList = events.filter((e) => (e.start_time || '').startsWith(today));
    const upcomingList = events.filter((e) => (e.start_time || '') > today && !(e.start_time || '').startsWith(today));
    const pastList = events.filter((e) => (e.start_time || '') < today);

    return {
      today: todayList,
      upcoming: upcomingList,
      past: pastList,
    };
  }, [events]);

  // Week View Calculation
  const weekDays = useMemo(() => {
    const curr = new Date(activeDate);
    const day = curr.getDay(); // 0 is Sunday
    const firstDay = new Date(curr);
    firstDay.setDate(curr.getDate() - day);

    const days: { date: Date; dateStr: string; label: string; isToday: boolean }[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(firstDay);
      d.setDate(firstDay.getDate() + i);
      const str = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      days.push({
        date: d,
        dateStr: str,
        label: DAYS_OF_WEEK[d.getDay()],
        isToday: str === todayStr,
      });
    }
    return days;
  }, [activeDate, todayStr]);

  // Month View Calculation
  const monthData = useMemo(() => {
    const year = activeDate.getFullYear();
    const month = activeDate.getMonth();
    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const cells: { day: number | null; dateStr: string; isToday: boolean }[] = [];
    for (let i = 0; i < firstDayIndex; i++) {
      cells.push({ day: null, dateStr: '', isToday: false });
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      cells.push({
        day: d,
        dateStr,
        isToday: dateStr === todayStr,
      });
    }
    return {
      monthLabel: activeDate.toLocaleString('default', { month: 'long', year: 'numeric' }),
      cells,
    };
  }, [activeDate, todayStr]);

  return (
    <div
      className="flex-1 flex flex-col h-full overflow-y-auto w-full"
      style={{
        background: 'var(--bg, #f5f2ed)',
        color: 'var(--text, #1a1a1a)',
      }}
    >
      {/* ── Top Header Bar (Black + Gold Light / Dark Cyan) ── */}
      <header
        className="sticky top-0 z-20 px-3 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-3 shadow-sm border-b"
        style={{
          background: '#111111',
          borderColor: '#262626',
          color: '#ffffff',
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm"
            style={{
              background: 'linear-gradient(135deg, #b8960c, #d4af37)',
              color: '#111111',
              boxShadow: '0 2px 8px rgba(184, 150, 12, 0.4)',
            }}
          >
            EW
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-base font-bold text-white tracking-wide">
                Empire Workroom Schedule Control
              </h1>
              <span
                className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase"
                style={{
                  background: 'rgba(184, 150, 12, 0.25)',
                  color: '#facc15',
                  border: '1px solid rgba(184, 150, 12, 0.4)',
                }}
              >
                Max Sync
              </span>
            </div>
            <p className="text-[11px] text-neutral-400">
              Deliveries, Installs, Pickups & Loading Dock Log
            </p>
          </div>
        </div>

        {/* View Switcher & Action Buttons */}
        <div className="w-full sm:w-auto flex items-center justify-between sm:justify-end gap-2 pt-2 sm:pt-0">
          {/* View Toggle */}
          <div
            className="flex items-center gap-1 p-1 rounded-xl border border-neutral-800 bg-neutral-900/90"
            role="tablist"
          >
            {(['agenda', 'week', 'month'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all capitalize cursor-pointer ${
                  viewMode === mode
                    ? 'bg-[#b8960c] text-neutral-950 shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
                style={{ minHeight: 36 }}
              >
                {mode}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            {/* Proposal Helper Trigger */}
            <button
              onClick={() => setShowProposalHelper(!showProposalHelper)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl border border-neutral-700 bg-neutral-800/80 text-neutral-200 hover:bg-neutral-700 transition-colors cursor-pointer"
              style={{ minHeight: 44 }}
              title="Max Email/Text Proposal Helper"
            >
              <Sparkles size={14} className="text-[#facc15]" />
              <span className="hidden sm:inline">Draft Helper</span>
            </button>

            {/* Quick Add Custom Event */}
            <button
              onClick={() => openQuickAdd('pickup')}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-bold rounded-xl text-black hover:opacity-95 transition-all cursor-pointer shadow-md whitespace-nowrap"
              style={{
                minHeight: 40,
                background: '#b8960c',
              }}
            >
              <Plus size={15} />
              <span>Event</span>
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Content Container (Mobile-first, max-w, scrollable) ── */}
      <main className="w-full max-w-5xl mx-auto px-3 sm:px-6 py-4 space-y-4">
        {/* ── 1. TODAY SUMMARY BANNER ── */}
        <section
          className="rounded-2xl p-4 sm:p-5 border transition-all"
          style={{
            background: 'var(--panel, #ffffff)',
            borderColor: 'var(--border, #ece8e0)',
            boxShadow: '0 2px 10px rgba(0,0,0,0.03)',
          }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 border-b pb-3 border-[var(--border,#ece8e0)]">
            <div>
              <div className="text-[11px] font-bold text-[#b8960c] uppercase tracking-wider flex items-center gap-1.5">
                <Clock size={12} /> Today at a Glance
              </div>
              <h2 className="text-base sm:text-lg font-bold text-[var(--text,#1a1a1a)]">
                {new Date().toLocaleDateString('en-US', {
                  weekday: 'long',
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </h2>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[var(--card-bg,#faf9f7)] border border-[var(--border,#ece8e0)]">
                <span className="text-xs text-[var(--muted,#999)]">Today:</span>
                <span className="text-sm font-extrabold text-[#b8960c]">
                  {todaySummary?.total_events_today ?? 0}
                </span>
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[var(--card-bg,#faf9f7)] border border-[var(--border,#ece8e0)]">
                <span className="text-xs text-[var(--muted,#999)]">Upcoming:</span>
                <span className="text-sm font-extrabold text-[var(--text,#1a1a1a)]">
                  {todaySummary?.upcoming_events_count ?? 0}
                </span>
              </div>
            </div>
          </div>

          {/* Quick-Add 1-Tap Row */}
          <div className="space-y-1.5">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted,#999)]">
              Quick-Add 1-Tap
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                onClick={() => openQuickAdd('pickup')}
                className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] hover:border-[#b8960c] transition-all cursor-pointer text-xs font-bold text-[var(--text,#1a1a1a)] active:scale-[0.98]"
                style={{ minHeight: 44 }}
              >
                <PackageCheck size={16} className="text-[#b8960c]" />
                <span>Picked up</span>
              </button>

              <button
                onClick={() => openQuickAdd('drop_off')}
                className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] hover:border-[#16a34a] transition-all cursor-pointer text-xs font-bold text-[var(--text,#1a1a1a)] active:scale-[0.98]"
                style={{ minHeight: 44 }}
              >
                <PackageCheck size={16} className="text-[#16a34a]" />
                <span>Dropped off</span>
              </button>

              <button
                onClick={() => openQuickAdd('install')}
                className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] hover:border-[#2563eb] transition-all cursor-pointer text-xs font-bold text-[var(--text,#1a1a1a)] active:scale-[0.98]"
                style={{ minHeight: 44 }}
              >
                <Wrench size={16} className="text-[#2563eb]" />
                <span>Install</span>
              </button>

              <button
                onClick={() => openQuickAdd('loading_dock')}
                className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] hover:border-[#dc2626] transition-all cursor-pointer text-xs font-bold text-[var(--text,#1a1a1a)] active:scale-[0.98]"
                style={{ minHeight: 44 }}
              >
                <Truck size={16} className="text-[#dc2626]" />
                <span>Loading dock</span>
              </button>
            </div>
          </div>
        </section>

        {/* ── DRAFT-ONLY PROPOSAL HELPER DRAWER (Optional) ── */}
        {showProposalHelper && (
          <section
            className="rounded-2xl p-4 sm:p-5 border border-[#d4b84a] bg-[#fdf8eb] transition-all space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={16} className="text-[#b8960c]" />
                <h3 className="text-sm font-bold text-[#1a1a1a]">
                  Max Schedule Draft Assistant (Email & Text)
                </h3>
              </div>
              <button
                onClick={() => setShowProposalHelper(false)}
                className="text-neutral-500 hover:text-black p-1 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
            <p className="text-xs text-neutral-700 leading-relaxed">
              Paste email summaries or chat text below. Max will extract proposed dates,
              parties, and locations. <strong>Nothing is added to your calendar without your explicit confirmation.</strong>
            </p>
            <textarea
              value={proposalText}
              onChange={(e) => setProposalText(e.target.value)}
              placeholder="e.g.: 'Install scheduled with Whittington Design next Tuesday Oct 13 at 10am at 8400 Westpark Dr. Also pick up 2 drapery rolls from Kravet at 2pm.'"
              rows={3}
              className="w-full text-xs p-3 rounded-xl border border-[#d4b84a] bg-white text-black outline-none focus:ring-1 focus:ring-[#b8960c] resize-none"
            />
            <div className="flex items-center justify-between">
              <button
                onClick={handleAnalyzeDraftProposals}
                disabled={extractingProposals || !proposalText.trim()}
                className="px-4 py-2 text-xs font-bold rounded-xl bg-[#b8960c] text-white hover:opacity-90 disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                style={{ minHeight: 40 }}
              >
                {extractingProposals ? (
                  <>
                    <Loader2 size={13} className="animate-spin" /> Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles size={13} /> Extract Proposals
                  </>
                )}
              </button>
              {proposalNotice && (
                <span className="text-[11px] text-neutral-600 italic">
                  {proposalNotice}
                </span>
              )}
            </div>

            {/* Extracted Proposals Cards */}
            {proposalsResult.length > 0 && (
              <div className="space-y-2 pt-2">
                <div className="text-[11px] font-bold text-neutral-800 uppercase">
                  Proposed Events ({proposalsResult.length})
                </div>
                {proposalsResult.map((p, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-white rounded-xl border border-neutral-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-black">{p.title}</span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-neutral-100 text-neutral-700">
                          {p.type}
                        </span>
                      </div>
                      <div className="text-[11px] text-neutral-600 mt-0.5">
                        {p.start_time} {p.customer_vendor ? `· ${p.customer_vendor}` : ''}{' '}
                        {p.location_address ? `· ${p.location_address}` : ''}
                      </div>
                    </div>
                    <button
                      onClick={() => handleConfirmProposedEvent(p)}
                      className="px-3 py-1.5 rounded-lg bg-[#16a34a] text-white text-xs font-bold hover:bg-[#15803d] transition-all cursor-pointer flex items-center gap-1 self-start sm:self-auto"
                      style={{ minHeight: 36 }}
                    >
                      <Check size={14} /> Confirm & Add
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* ── 2. VIEW CONTROLS & DATE NAV ── */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigateDate(-1)}
              className="p-2 rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)] hover:bg-[var(--card-bg,#faf9f7)] transition-colors cursor-pointer"
              style={{ minHeight: 44, minWidth: 44, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              aria-label="Previous"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              onClick={jumpToToday}
              className="px-3.5 py-2 text-xs font-bold rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)] hover:border-[#b8960c] transition-colors cursor-pointer"
              style={{ minHeight: 44 }}
            >
              Today
            </button>
            <button
              onClick={() => navigateDate(1)}
              className="p-2 rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)] hover:bg-[var(--card-bg,#faf9f7)] transition-colors cursor-pointer"
              style={{ minHeight: 44, minWidth: 44, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              aria-label="Next"
            >
              <ChevronRight size={18} />
            </button>
          </div>

          <div className="text-sm font-extrabold text-[var(--text,#1a1a1a)]">
            {viewMode === 'month' && monthData.monthLabel}
            {viewMode === 'week' && (
              <span>
                {weekDays[0].label} {weekDays[0].dateStr.slice(5)} – {weekDays[6].label}{' '}
                {weekDays[6].dateStr.slice(5)}
              </span>
            )}
            {viewMode === 'agenda' && (
              <span>
                Active Agenda ({events.length} Events)
              </span>
            )}
          </div>
        </div>

        {/* ── 3. MAIN SCHEDULE VIEWS ── */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 size={32} className="animate-spin text-[#b8960c]" />
          </div>
        ) : viewMode === 'agenda' ? (
          /* ── AGENDA VIEW (Today & Upcoming) ── */
          <div className="space-y-6">
            {/* Today Section */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#b8960c]" />
                <h3 className="text-xs font-bold text-[var(--muted,#999)] uppercase tracking-wider">
                  Today's Events ({agendaEvents.today.length})
                </h3>
              </div>

              {agendaEvents.today.length === 0 ? (
                <div
                  className="p-6 text-center rounded-2xl border border-dashed border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-xs text-[var(--muted,#999)]"
                >
                  No events scheduled for today. Use Quick-Add above to log an event.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {agendaEvents.today.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onCheckDone={handleCheckDone}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Upcoming Section */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#2563eb]" />
                <h3 className="text-xs font-bold text-[var(--muted,#999)] uppercase tracking-wider">
                  Upcoming ({agendaEvents.upcoming.length})
                </h3>
              </div>

              {agendaEvents.upcoming.length === 0 ? (
                <div
                  className="p-6 text-center rounded-2xl border border-dashed border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-xs text-[var(--muted,#999)]"
                >
                  No future events scheduled.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {agendaEvents.upcoming.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onCheckDone={handleCheckDone}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Recent Custody Log Summary */}
            <div className="space-y-3 pt-4 border-t border-[var(--border,#ece8e0)]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <PackageCheck size={16} className="text-[#16a34a]" />
                  <h3 className="text-xs font-bold text-[var(--text,#1a1a1a)] uppercase tracking-wider">
                    Recent Custody Transfer Log (Pickups & Drop-offs)
                  </h3>
                </div>
                <button
                  onClick={() => {
                    setSelectedEventForDone(null);
                    setShowCustodyModal(true);
                  }}
                  className="text-xs font-bold text-[#b8960c] hover:underline cursor-pointer"
                >
                  + Manual Log
                </button>
              </div>

              {logs.length === 0 ? (
                <div className="p-4 text-center rounded-xl bg-[var(--card-bg,#faf9f7)] text-xs text-[var(--muted,#999)] border border-[var(--border,#ece8e0)]">
                  No custody logs recorded yet.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {logs.slice(0, 6).map((log) => (
                    <div
                      key={log.id}
                      className="p-3 rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)] flex flex-col justify-between gap-1 shadow-sm"
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                            log.direction === 'picked_up'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-green-100 text-green-800'
                          }`}
                        >
                          {log.direction === 'picked_up' ? 'Picked Up' : 'Dropped Off'}
                        </span>
                        <span className="text-[10px] text-[var(--muted,#999)]">
                          {log.timestamp.slice(0, 16).replace('T', ' ')}
                        </span>
                      </div>
                      <div className="text-xs font-bold text-[var(--text,#1a1a1a)]">
                        {log.items}
                      </div>
                      <div className="text-[11px] text-[var(--muted,#999)] truncate">
                        {log.party ? `Party: ${log.party}` : 'Party: N/A'}
                        {log.job_id ? ` · Job: ${log.job_id}` : ''}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : viewMode === 'week' ? (
          /* ── WEEK VIEW ── */
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-7 gap-2.5">
              {weekDays.map((day) => {
                const dayEvents = events.filter((e) =>
                  (e.start_time || '').startsWith(day.dateStr)
                );
                return (
                  <div
                    key={day.dateStr}
                    className={`rounded-2xl p-3 border flex flex-col min-h-[160px] ${
                      day.isToday
                        ? 'border-[#b8960c] bg-[#fdf8eb]/40 shadow-sm'
                        : 'border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-[var(--muted,#999)]">
                        {day.label}
                      </span>
                      <span
                        className={`text-xs font-extrabold w-6 h-6 flex items-center justify-center rounded-full ${
                          day.isToday
                            ? 'bg-[#b8960c] text-white'
                            : 'text-[var(--text,#1a1a1a)]'
                        }`}
                      >
                        {day.date.getDate()}
                      </span>
                    </div>

                    <div className="space-y-1.5 flex-1">
                      {dayEvents.map((ev) => (
                        <div
                          key={ev.id}
                          onClick={() => handleCheckDone(ev)}
                          className={`p-2 rounded-xl text-[11px] cursor-pointer transition-all border ${
                            ev.status === 'done'
                              ? 'line-through opacity-60 bg-neutral-100 border-neutral-200 text-neutral-500'
                              : 'bg-[var(--card-bg,#faf9f7)] border-[var(--border,#ece8e0)] hover:border-[#b8960c]'
                          }`}
                        >
                          <div className="font-bold truncate text-[var(--text,#1a1a1a)]">
                            {ev.title}
                          </div>
                          <div className="text-[10px] text-[var(--muted,#999)]">
                            {ev.start_time.slice(11, 16)} · {ev.type}
                          </div>
                        </div>
                      ))}
                      {dayEvents.length === 0 && (
                        <div className="h-full flex items-center justify-center text-[10px] text-[var(--muted,#999)] italic">
                          Clear
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          /* ── MONTH VIEW ── */
          <div
            className="rounded-2xl border border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)] overflow-hidden shadow-sm"
          >
            {/* Day Header Row */}
            <div className="grid grid-cols-7 border-b border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)]">
              {DAYS_OF_WEEK.map((d) => (
                <div
                  key={d}
                  className="py-2.5 text-center text-[10px] font-bold text-[var(--muted,#999)] uppercase"
                >
                  {d}
                </div>
              ))}
            </div>

            {/* Grid Cells */}
            <div className="grid grid-cols-7">
              {monthData.cells.map((cell, idx) => {
                const dayEvents = cell.dateStr
                  ? events.filter((e) => (e.start_time || '').startsWith(cell.dateStr))
                  : [];

                return (
                  <div
                    key={idx}
                    className={`min-h-[85px] sm:min-h-[110px] p-1.5 border-b border-r border-[var(--border,#ece8e0)] ${
                      cell.day === null
                        ? 'bg-[var(--card-bg,#faf9f7)]/50'
                        : cell.isToday
                        ? 'bg-[#fdf8eb]/40'
                        : 'bg-transparent'
                    }`}
                  >
                    {cell.day !== null && (
                      <div className="flex flex-col h-full justify-between">
                        <div className="flex items-center justify-between">
                          <span
                            className={`text-xs font-bold ${
                              cell.isToday
                                ? 'text-[#b8960c] font-extrabold'
                                : 'text-[var(--text,#1a1a1a)]'
                            }`}
                          >
                            {cell.day}
                          </span>
                          {dayEvents.length > 0 && (
                            <span className="text-[9px] font-bold text-[#b8960c] px-1 rounded bg-[#fdf8eb]">
                              {dayEvents.length}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1 mt-1">
                          {dayEvents.slice(0, 2).map((ev) => (
                            <div
                              key={ev.id}
                              className="text-[9px] font-medium p-1 rounded bg-[var(--card-bg,#faf9f7)] border border-[var(--border,#ece8e0)] truncate text-[var(--text,#1a1a1a)]"
                              title={`${ev.title} (${ev.type})`}
                            >
                              {ev.title}
                            </div>
                          ))}
                          {dayEvents.length > 2 && (
                            <div className="text-[8px] text-[var(--muted,#999)] pl-1">
                              +{dayEvents.length - 2} more
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>

      {/* ── MODAL: QUICK / EVENT ADD ── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 bg-black/50 backdrop-blur-xs">
          <div
            className="w-full max-w-md rounded-2xl p-5 border border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)] shadow-2xl max-h-[92vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border,#ece8e0)] mb-4">
              <h3 className="text-base font-bold text-[var(--text,#1a1a1a)] flex items-center gap-2">
                <CalendarIcon size={18} className="text-[#b8960c]" />
                Schedule Event
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-neutral-400 hover:text-black cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            {formError && (
              <div className="mb-3 p-3 rounded-xl bg-red-50 border border-red-200 text-red-600 text-xs flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEvent} className="space-y-3.5">
              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Type
                </label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value as EventType)}
                  className="w-full px-3 py-2 text-xs font-semibold rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                  style={{ minHeight: 44 }}
                >
                  <option value="pickup">Pickup</option>
                  <option value="drop_off">Drop-off</option>
                  <option value="fabric_pickup">Fabric Pickup</option>
                  <option value="install">Installation</option>
                  <option value="delivery">Delivery</option>
                  <option value="measure">Measure</option>
                  <option value="loading_dock">Loading Dock Reservation</option>
                  <option value="errand">Errand</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g. Pick up drapery fabrics"
                  className="w-full px-3 py-2 text-xs font-semibold rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none focus:border-[#b8960c]"
                  style={{ minHeight: 44 }}
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Link to Job (Optional)
                </label>
                <select
                  value={formJobId}
                  onChange={(e) => setFormJobId(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-semibold rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                  style={{ minHeight: 44 }}
                >
                  <option value="">No linked job</option>
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title || j.customer_name || j.id} {j.job_number ? `(${j.job_number})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                    Customer / Vendor
                  </label>
                  <input
                    type="text"
                    value={formCustomerVendor}
                    onChange={(e) => setFormCustomerVendor(e.target.value)}
                    placeholder="e.g. Whittington Design"
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                    style={{ minHeight: 44 }}
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                    Date
                  </label>
                  <input
                    type="date"
                    value={formDate}
                    onChange={(e) => setFormDate(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                    style={{ minHeight: 44 }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                    Start Time
                  </label>
                  <input
                    type="time"
                    value={formStartTime}
                    onChange={(e) => setFormStartTime(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                    style={{ minHeight: 44 }}
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                    End Time
                  </label>
                  <input
                    type="time"
                    value={formEndTime}
                    onChange={(e) => setFormEndTime(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                    style={{ minHeight: 44 }}
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Location / Address (Tap-to-Map)
                </label>
                <input
                  type="text"
                  value={formLocation}
                  onChange={(e) => setFormLocation(e.target.value)}
                  placeholder="e.g. 1400 K St NW, Washington DC"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                  style={{ minHeight: 44 }}
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Notes
                </label>
                <textarea
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  rows={2}
                  placeholder="Additional details, dock contacts, access codes..."
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border,#ece8e0)]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-[var(--border,#ece8e0)] text-neutral-600 hover:bg-neutral-100 cursor-pointer"
                  style={{ minHeight: 44 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingEvent}
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-[#b8960c] text-white hover:opacity-90 transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
                  style={{ minHeight: 44 }}
                >
                  {savingEvent ? (
                    <>
                      <Loader2 size={14} className="animate-spin" /> Saving...
                    </>
                  ) : (
                    'Save Event'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: CUSTODY LOG / MARK DONE ── */}
      {showCustodyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 bg-black/50 backdrop-blur-xs">
          <div
            className="w-full max-w-md rounded-2xl p-5 border border-[var(--border,#ece8e0)] bg-[var(--panel,#ffffff)] shadow-2xl"
          >
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border,#ece8e0)] mb-4">
              <h3 className="text-base font-bold text-[var(--text,#1a1a1a)] flex items-center gap-2">
                <PackageCheck size={18} className="text-[#16a34a]" />
                Record Custody Transfer Log
              </h3>
              <button
                onClick={() => setShowCustodyModal(false)}
                className="p-1 rounded-lg text-neutral-400 hover:text-black cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveCustodyLog} className="space-y-3.5">
              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Direction
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setCustodyDirection('picked_up')}
                    className={`px-3 py-2 text-xs font-bold rounded-xl border transition-all cursor-pointer ${
                      custodyDirection === 'picked_up'
                        ? 'border-[#b8960c] bg-[#fdf8eb] text-[#b8960c]'
                        : 'border-[var(--border,#ece8e0)] text-[var(--text,#1a1a1a)]'
                    }`}
                    style={{ minHeight: 44 }}
                  >
                    Picked Up
                  </button>
                  <button
                    type="button"
                    onClick={() => setCustodyDirection('dropped_off')}
                    className={`px-3 py-2 text-xs font-bold rounded-xl border transition-all cursor-pointer ${
                      custodyDirection === 'dropped_off'
                        ? 'border-[#16a34a] bg-[#f0fdf4] text-[#16a34a]'
                        : 'border-[var(--border,#ece8e0)] text-[var(--text,#1a1a1a)]'
                    }`}
                    style={{ minHeight: 44 }}
                  >
                    Dropped Off
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  What Changed Hands (Items) *
                </label>
                <input
                  type="text"
                  value={custodyItems}
                  onChange={(e) => setCustodyItems(e.target.value)}
                  placeholder="e.g. 4 cushion covers, 2 drapery panels, 1 bolt velvet"
                  className="w-full px-3 py-2 text-xs font-semibold rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none focus:border-[#16a34a]"
                  style={{ minHeight: 44 }}
                  required
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  From / To Party
                </label>
                <input
                  type="text"
                  value={custodyParty}
                  onChange={(e) => setCustodyParty(e.target.value)}
                  placeholder="e.g. Whittington Design, Client, Warehouse"
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                  style={{ minHeight: 44 }}
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Linked Job (Optional)
                </label>
                <select
                  value={custodyJobId}
                  onChange={(e) => setCustodyJobId(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-semibold rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none"
                  style={{ minHeight: 44 }}
                >
                  <option value="">No linked job</option>
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title || j.customer_name || j.id}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-[var(--muted,#999)] uppercase mb-1">
                  Notes
                </label>
                <textarea
                  value={custodyNotes}
                  onChange={(e) => setCustodyNotes(e.target.value)}
                  rows={2}
                  placeholder="Condition notes, signature, receipt reference..."
                  className="w-full px-3 py-2 text-xs rounded-xl border border-[var(--border,#ece8e0)] bg-[var(--card-bg,#faf9f7)] text-[var(--text,#1a1a1a)] outline-none resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border,#ece8e0)]">
                <button
                  type="button"
                  onClick={() => setShowCustodyModal(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl border border-[var(--border,#ece8e0)] text-neutral-600 hover:bg-neutral-100 cursor-pointer"
                  style={{ minHeight: 44 }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingCustody}
                  className="px-5 py-2 text-xs font-bold rounded-xl bg-[#16a34a] text-white hover:opacity-90 transition-all cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
                  style={{ minHeight: 44 }}
                >
                  {savingCustody ? (
                    <>
                      <Loader2 size={14} className="animate-spin" /> Recording...
                    </>
                  ) : (
                    'Record Log & Complete'
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ── SUB-COMPONENT: EVENT CARD ──
function EventCard({
  event,
  onCheckDone,
}: {
  event: ScheduleEvent;
  onCheckDone: (e: ScheduleEvent) => void;
}) {
  const isDone = event.status === 'done';
  const cfg = TYPE_CONFIG[event.type] || TYPE_CONFIG.other;
  const Icon = cfg.icon;

  // Format Map Link
  const mapUrl = event.location_address
    ? `https://maps.google.com/?q=${encodeURIComponent(event.location_address)}`
    : null;

  // Format Time
  const timeStr = event.start_time
    ? event.start_time.slice(11, 16)
    : '--:--';
  const endTimeStr = event.end_time
    ? event.end_time.slice(11, 16)
    : null;

  return (
    <div
      className={`rounded-2xl p-4 border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs ${
        isDone
          ? 'opacity-70 bg-neutral-50 border-neutral-200'
          : 'bg-[var(--panel,#ffffff)] border-[var(--border,#ece8e0)] hover:border-[#b8960c]'
      }`}
    >
      <div className="flex items-start gap-3 min-w-0">
        {/* Checkbox Tap Target >= 44px */}
        <button
          onClick={() => onCheckDone(event)}
          className="flex items-center justify-center p-2 rounded-xl text-[var(--muted,#999)] hover:text-[#16a34a] transition-colors cursor-pointer shrink-0"
          style={{ minWidth: 44, minHeight: 44 }}
          title={isDone ? 'Mark as planned' : 'Mark done and log custody'}
          aria-label="Toggle completed"
        >
          {isDone ? (
            <CheckCircle size={22} className="text-[#16a34a]" />
          ) : (
            <Circle size={22} className="text-neutral-300 hover:text-neutral-500" />
          )}
        </button>

        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="text-[10px] font-bold px-2 py-0.5 rounded-md uppercase flex items-center gap-1"
              style={{
                background: cfg.bgLight,
                color: cfg.textLight,
              }}
            >
              <Icon size={11} /> {cfg.label}
            </span>

            {event.status === 'confirmed' && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-blue-50 text-blue-700">
                Confirmed
              </span>
            )}

            <span className="text-xs font-semibold text-[var(--muted,#999)]">
              {timeStr} {endTimeStr ? `– ${endTimeStr}` : ''}
            </span>
          </div>

          <h4
            className={`text-sm font-bold truncate ${
              isDone
                ? 'line-through text-neutral-400'
                : 'text-[var(--text,#1a1a1a)]'
            }`}
          >
            {event.title}
          </h4>

          {/* Details & Job Link */}
          <div className="flex items-center gap-3 text-[11px] text-[var(--muted,#999)] flex-wrap">
            {event.customer_vendor && (
              <span className="font-medium text-[var(--text,#1a1a1a)]">
                {event.customer_vendor}
              </span>
            )}

            {event.job_id && (
              <a
                href={`/?screen=jobs&jobId=${encodeURIComponent(event.job_id)}`}
                className="font-bold text-[#b8960c] hover:underline flex items-center gap-1"
                title="View linked job in Job Hub"
              >
                <ClipboardList size={12} /> Job: {event.job_id.slice(0, 8)}...
              </a>
            )}

            {mapUrl && (
              <a
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[#2563eb] hover:underline font-medium"
                title="Open location in Google Maps"
              >
                <MapPin size={12} />
                <span className="truncate max-w-[180px] sm:max-w-[260px]">
                  {event.location_address}
                </span>
                <ExternalLink size={10} />
              </a>
            )}
          </div>

          {event.notes && (
            <p className="text-[11px] text-[var(--muted,#999)] italic pt-0.5">
              "{event.notes}"
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
