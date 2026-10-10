'use client';

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { API } from '../../../lib/api';
import { readTheme, EmpireTheme } from '../../ThemeToggle';
import { formatInches } from '../../../lib/formatInches';
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
  FileText,
  Building,
  User,
  Layers,
  ChevronDown,
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
    textLight: '#b8960c',
    darkBg: 'rgba(184,150,12,0.2)',
    darkText: '#facc15',
    icon: PackageCheck,
  },
  drop_off: {
    label: 'Drop-off',
    bgLight: '#ecfdf5',
    textLight: '#047857',
    darkBg: 'rgba(16,185,129,0.2)',
    darkText: '#34d399',
    icon: PackageCheck,
  },
  fabric_pickup: {
    label: 'Fabric Pickup',
    bgLight: '#fdf4ff',
    textLight: '#a21caf',
    darkBg: 'rgba(192,38,211,0.2)',
    darkText: '#e879f9',
    icon: Truck,
  },
  measure: {
    label: 'Measure',
    bgLight: '#f0fdfa',
    textLight: '#0f766e',
    darkBg: 'rgba(20,184,166,0.2)',
    darkText: '#2dd4bf',
    icon: Wrench,
  },
  loading_dock: {
    label: 'Loading Dock',
    bgLight: '#fff7ed',
    textLight: '#c2410c',
    darkBg: 'rgba(234,88,12,0.2)',
    darkText: '#fb923c',
    icon: Clock,
  },
  errand: {
    label: 'Errand',
    bgLight: '#f8fafc',
    textLight: '#475569',
    darkBg: 'rgba(100,116,139,0.2)',
    darkText: '#94a3b8',
    icon: MapPin,
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

// Common standard items for custody transfer
export const COMMON_ITEMS = [
  'cushion covers',
  'drapery',
  'roman shades',
  'fabric',
  'hardware',
  'bench parts',
  'samples',
  'other',
];

export interface PartySuggestion {
  category: 'Vendors (Preset)' | 'Places (Preset)' | 'Customers (Max API)' | 'Vendors (Max API)';
  name: string;
  isPreset: boolean;
}

// Fixed vendor and place presets designated by Rafael
export const PRESET_PARTIES: PartySuggestion[] = [
  { category: 'Vendors (Preset)', name: "Nelma's Workroom", isPreset: true },
  { category: 'Vendors (Preset)', name: 'Whittington Design', isPreset: true },
  { category: 'Places (Preset)', name: 'Warehouse', isPreset: true },
  { category: 'Places (Preset)', name: 'Client site', isPreset: true },
];

export default function ScheduleControl({ business, initialJobId }: ScheduleControlProps) {
  // Theme Detection
  const [theme, setTheme] = useState<EmpireTheme>(readTheme());
  useEffect(() => {
    setTheme(readTheme());
    const sync = () => setTheme(readTheme());
    window.addEventListener('empire-theme', sync);
    return () => window.removeEventListener('empire-theme', sync);
  }, []);
  const isDark = theme === 'dark';

  // Design tokens aligned with JobBoard & JobFolderModal
  const accentColor = isDark ? '#22d3ee' : '#b8960c';
  const accentHover = isDark ? '#06b6d4' : '#967b0a';
  const badgeBg = isDark ? 'linear-gradient(135deg, #0891b2, #22d3ee)' : 'linear-gradient(135deg, #b8960c, #d4af37)';
  const badgeText = isDark ? '#06131a' : '#121214';
  const headerBg = isDark ? '#0b0f14' : '#121214';
  const headerBorder = `2px solid ${isDark ? '#22d3ee' : '#b8960c'}`;
  const pageBg = isDark ? '#070a0e' : '#f5f2ed';
  const modalBg = isDark ? '#0b0f14' : '#ffffff';
  const modalSubHeaderBg = isDark ? '#121821' : '#faf9f7';
  const cardBg = isDark ? '#121821' : '#ffffff';
  const cardBorder = isDark ? 'rgba(34, 211, 238, 0.2)' : '#ece8e0';
  const textPrimary = isDark ? '#f4f7fa' : '#1a1a1a';
  const textMuted = isDark ? '#8b96a3' : '#666666';
  const inputBg = isDark ? '#161f2c' : '#ffffff';
  const inputBorder = isDark ? 'rgba(255, 255, 255, 0.15)' : '#dddddd';

  const [viewMode, setViewMode] = useState<'agenda' | 'week' | 'month'>('agenda');
  const [activeDate, setActiveDate] = useState(() => new Date());
  const [events, setEvents] = useState<ScheduleEvent[]>([]);
  const [logs, setLogs] = useState<PickupDropoffLog[]>([]);
  const [todaySummary, setTodaySummary] = useState<TodaySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  // Live jobs from Max API (honest - no mock fallbacks)
  const [jobs, setJobs] = useState<any[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsError, setJobsError] = useState<string | null>(null);

  // Live customers & vendors from Max API
  const [apiCustomers, setApiCustomers] = useState<{ id?: string; name: string }[]>([]);
  const [apiVendors, setApiVendors] = useState<{ id?: string; name: string }[]>([]);
  const [apiPartiesError, setApiPartiesError] = useState<string | null>(null);

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
  const [custodySelectedChips, setCustodySelectedChips] = useState<string[]>(['cushion covers']);
  const [customItemInput, setCustomItemInput] = useState('');
  const [custodyParty, setCustodyParty] = useState('');
  const [custodyJobId, setCustodyJobId] = useState(initialJobId || '');
  const [custodyNotes, setCustodyNotes] = useState('');
  const [savingCustody, setSavingCustody] = useState(false);

  // Dropdown Open States
  const [showPartyDropdown, setShowPartyDropdown] = useState(false);
  const [showJobDropdown, setShowJobDropdown] = useState(false);
  const [showAddJobDropdown, setShowAddJobDropdown] = useState(false);
  const [showAddPartyDropdown, setShowAddPartyDropdown] = useState(false);
  const [partySearchTerm, setPartySearchTerm] = useState('');
  const [jobSearchTerm, setJobSearchTerm] = useState('');

  // Proposal Draft Helper State
  const [proposalText, setProposalText] = useState('');
  const [extractingProposals, setExtractingProposals] = useState(false);
  const [proposalsResult, setProposalsResult] = useState<any[]>([]);
  const [proposalNotice, setProposalNotice] = useState('');

  // Fetch Jobs list for dropdown picker from Max API (honest - no mock fallbacks)
  useEffect(() => {
    let active = true;
    setJobsLoading(true);
    setJobsError(null);
    fetch(`${API}/jobs`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        if (!active) return;
        const fetched = d.jobs || (Array.isArray(d) ? d : []);
        setJobs(fetched);
      })
      .catch((err) => {
        if (!active) return;
        console.warn('Could not load jobs from Max API:', err);
        setJobs([]);
        setJobsError('Max Jobs API unavailable');
      })
      .finally(() => {
        if (active) setJobsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // Fetch Customers & Vendors from Max API (honest - no mock fallbacks)
  useEffect(() => {
    let active = true;
    Promise.all([
      fetch(`${API}/customers?limit=100`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
      fetch(`${API}/vendors?limit=100`)
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
    ]).then(([custData, vendData]) => {
      if (!active) return;
      const customers: { id?: string; name: string }[] = [];
      if (custData) {
        const list = custData.customers || (Array.isArray(custData) ? custData : []);
        for (const c of list) {
          const name = c.name || c.company || c.client_name;
          if (name && !customers.some((x) => x.name.toLowerCase() === name.toLowerCase())) {
            customers.push({ id: c.id, name });
          }
        }
      }
      setApiCustomers(customers);

      const vendors: { id?: string; name: string }[] = [];
      if (vendData) {
        const list = vendData.vendors || (Array.isArray(vendData) ? vendData : []);
        for (const v of list) {
          const name = v.name || v.contact_name;
          if (name && !vendors.some((x) => x.name.toLowerCase() === name.toLowerCase())) {
            vendors.push({ id: v.id, name });
          }
        }
      }
      setApiVendors(vendors);

      if (!custData && !vendData) {
        setApiPartiesError('Customers/Vendors API unavailable');
      }
    });
    return () => {
      active = false;
    };
  }, []);

  // Fetch Data from Max API (honest - no mock fallbacks)
  const loadScheduleData = useCallback(async () => {
    setLoading(true);
    setScheduleError(null);
    try {
      const [eventsRes, summaryRes, logsRes] = await Promise.all([
        fetch(`${API}/schedule/events?limit=200`).catch(() => null),
        fetch(`${API}/schedule/today-summary`).catch(() => null),
        fetch(`${API}/schedule/pickup-dropoff-logs?limit=50`).catch(() => null),
      ]);

      if (eventsRes && eventsRes.ok) {
        const evData = await eventsRes.json();
        const evList = evData.events || (Array.isArray(evData) ? evData : []);
        setEvents(evList);
      } else {
        setEvents([]);
        if (!eventsRes || !eventsRes.ok) {
          setScheduleError('Max Schedule API unavailable');
        }
      }

      if (summaryRes && summaryRes.ok) {
        const sData = await summaryRes.json();
        setTodaySummary(sData);
      } else {
        setTodaySummary(null);
      }

      if (logsRes && logsRes.ok) {
        const lData = await logsRes.json();
        const lList = lData.logs || (Array.isArray(lData) ? lData : []);
        setLogs(lList);
      } else {
        setLogs([]);
      }
    } catch (e) {
      console.warn('Failed to load schedule data from Max API:', e);
      setEvents([]);
      setLogs([]);
      setTodaySummary(null);
      setScheduleError('Max Schedule API unavailable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadScheduleData();
  }, [loadScheduleData]);

  // Combined Party list: Fixed presets designated by Rafael + real records from Max API
  const availableParties = useMemo<PartySuggestion[]>(() => {
    const list: PartySuggestion[] = [...PRESET_PARTIES];
    // Add real customers from Max API
    for (const c of apiCustomers) {
      if (c.name && !list.some((p) => p.name.toLowerCase() === c.name.toLowerCase())) {
        list.push({ category: 'Customers (Max API)', name: c.name, isPreset: false });
      }
    }
    // Add real vendors from Max API
    for (const v of apiVendors) {
      if (v.name && !list.some((p) => p.name.toLowerCase() === v.name.toLowerCase())) {
        list.push({ category: 'Vendors (Max API)', name: v.name, isPreset: false });
      }
    }
    // Add client/customer from loaded live jobs
    for (const j of jobs) {
      const name = j.customer_name || j.client_name;
      if (name && !list.some((p) => p.name.toLowerCase() === name.toLowerCase())) {
        list.push({ category: 'Customers (Max API)', name, isPreset: false });
      }
    }
    return list;
  }, [apiCustomers, apiVendors, jobs]);

  // Derived: Selected Custody Job & Quote Line Items
  const selectedCustodyJob = useMemo(() => {
    if (!custodyJobId) return null;
    return jobs.find((j) => String(j.id) === String(custodyJobId) || String(j.job_number) === String(custodyJobId));
  }, [custodyJobId, jobs]);

  // Available Items for Custody: Common presets + Job quote lines/items
  const availableCustodyItems = useMemo(() => {
    const itemsSet = new Set<string>();
    if (selectedCustodyJob) {
      if (Array.isArray(selectedCustodyJob.items)) {
        selectedCustodyJob.items.forEach((it: string) => itemsSet.add(it));
      }
      if (Array.isArray(selectedCustodyJob.quote_lines)) {
        selectedCustodyJob.quote_lines.forEach((ql: string) => itemsSet.add(ql));
      }
      if (selectedCustodyJob.title) {
        itemsSet.add(selectedCustodyJob.title);
      }
    }
    COMMON_ITEMS.forEach((it) => itemsSet.add(it));
    return Array.from(itemsSet);
  }, [selectedCustodyJob]);

  // Auto-fill party and items when Job is chosen in Custody Modal
  const handleSelectCustodyJob = (job: any) => {
    setCustodyJobId(job.id || job.job_number);
    const partyName = job.client_name || job.customer_name || '';
    if (partyName) {
      setCustodyParty(partyName);
    }
    // Pull primary items from job
    if (Array.isArray(job.items) && job.items.length > 0) {
      const topItems = job.items.slice(0, 2);
      setCustodySelectedChips(topItems);
      setCustodyItems(topItems.join(', '));
    } else if (job.title) {
      setCustodySelectedChips([job.title]);
      setCustodyItems(job.title);
    }
    setShowJobDropdown(false);
  };

  // Toggle item in multi-select
  const handleToggleItemChip = (item: string) => {
    setCustodySelectedChips((prev) => {
      let updated: string[];
      if (prev.includes(item)) {
        updated = prev.filter((i) => i !== item);
      } else {
        updated = [...prev, item];
      }
      setCustodyItems(updated.join(', '));
      return updated;
    });
  };

  // Add custom item
  const handleAddCustomItem = () => {
    const val = customItemInput.trim();
    if (!val) return;
    setCustodySelectedChips((prev) => {
      const updated = prev.includes(val) ? prev : [...prev, val];
      setCustodyItems(updated.join(', '));
      return updated;
    });
    setCustomItemInput('');
  };

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

    const newEvt: ScheduleEvent = {
      id: `evt-${Date.now()}`,
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
    };

    try {
      const res = await fetch(`${API}/schedule/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEvt),
      });

      if (!res.ok) {
        // Fallback update local state for responsive dev/offline
        setEvents((prev) => [newEvt, ...prev]);
      } else {
        await loadScheduleData();
      }
      setShowAddModal(false);
    } catch {
      // Fallback
      setEvents((prev) => [newEvt, ...prev]);
      setShowAddModal(false);
    } finally {
      setSavingEvent(false);
    }
  };

  // Checkbox 'Done' Action
  const handleCheckDone = (event: ScheduleEvent) => {
    if (event.status === 'done') {
      // Revert to planned
      setEvents((prev) =>
        prev.map((e) => (e.id === event.id ? { ...e, status: 'planned' } : e))
      );
      fetch(`${API}/schedule/events/${event.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'planned' }),
      }).catch(() => {});
      return;
    }

    // Prompt custody details for transfers
    if (['pickup', 'drop_off', 'delivery', 'fabric_pickup'].includes(event.type)) {
      setSelectedEventForDone(event);
      setCustodyDirection(event.type === 'pickup' || event.type === 'fabric_pickup' ? 'picked_up' : 'dropped_off');
      setCustodyParty(event.customer_vendor || '');
      setCustodyJobId(event.job_id || '');
      setCustodyNotes(`Completed from scheduled event: ${event.title}`);
      setShowCustodyModal(true);
    } else {
      // Mark done directly
      setEvents((prev) =>
        prev.map((e) => (e.id === event.id ? { ...e, status: 'done' } : e))
      );
      fetch(`${API}/schedule/events/${event.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'done' }),
      }).catch(() => {});
    }
  };

  // Submit Custody Log + Mark Done
  const handleSaveCustodyLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!custodyItems.trim()) return;
    setSavingCustody(true);

    const newLog: PickupDropoffLog = {
      id: `log-${Date.now()}`,
      schedule_event_id: selectedEventForDone?.id || null,
      job_id: custodyJobId || null,
      direction: custodyDirection,
      items: custodyItems.trim(),
      party: custodyParty.trim() || null,
      notes: custodyNotes.trim() || null,
      timestamp: new Date().toISOString(),
      created_by: 'manual',
    };

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

      if (res.ok) {
        await loadScheduleData();
      } else {
        setLogs((prev) => [newLog, ...prev]);
      }

      // Mark the parent event as done if linked
      if (selectedEventForDone) {
        setEvents((prev) =>
          prev.map((ev) => (ev.id === selectedEventForDone.id ? { ...ev, status: 'done' } : ev))
        );
      }

      setShowCustodyModal(false);
      setSelectedEventForDone(null);
    } catch {
      // Offline fallback
      setLogs((prev) => [newLog, ...prev]);
      if (selectedEventForDone) {
        setEvents((prev) =>
          prev.map((ev) => (ev.id === selectedEventForDone.id ? { ...ev, status: 'done' } : ev))
        );
      }
      setShowCustodyModal(false);
      setSelectedEventForDone(null);
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
      const res = await fetch(`${API}/schedule/analyze-proposals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: proposalText }),
      });
      if (res.ok) {
        const data = await res.json();
        setProposalsResult(data.proposed_events || []);
        if ((data.proposed_events || []).length === 0) {
          setProposalNotice('No scheduled events detected in text.');
        }
      }
    } catch (e: any) {
      setProposalNotice('Could not extract events. You can manually create one.');
    } finally {
      setExtractingProposals(false);
    }
  };

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
    return { year, month, cells };
  }, [activeDate, todayStr]);

  return (
    <div
      style={{
        backgroundColor: pageBg,
        minHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        padding: '16px 20px',
        overflowY: 'auto',
      }}
    >
      {/* ── TOP HEADER BANNER (Consistent with JobBoard) ── */}
      <header
        style={{
          background: headerBg,
          color: '#ffffff',
          borderRadius: '14px',
          padding: '16px 20px',
          borderBottom: headerBorder,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              background: badgeBg,
              color: badgeText,
              fontSize: '11px',
              fontWeight: 800,
              padding: '4px 10px',
              borderRadius: '6px',
              letterSpacing: '0.5px',
              flexShrink: 0,
            }}
          >
            EMPIRE WORKROOM
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h1 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                Schedule & Custody Control
              </h1>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  background: isDark ? 'rgba(34, 211, 238, 0.2)' : 'rgba(184, 150, 12, 0.25)',
                  color: accentColor,
                  border: `1px solid ${accentColor}`,
                }}
              >
                Max Sync
              </span>
            </div>
            <p style={{ fontSize: '11px', color: '#9ca3af', margin: '2px 0 0 0' }}>
              Deliveries, Installs, Pickups & Custody Transfer Log
            </p>
          </div>
        </div>

        {/* View Switcher & Action Buttons (Min 44px tap targets) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {/* View Toggle */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: 4,
              borderRadius: 10,
              background: isDark ? '#161f2c' : '#1c1c20',
              border: `1px solid ${isDark ? 'rgba(34, 211, 238, 0.25)' : '#333'}`,
            }}
            role="tablist"
          >
            {(['agenda', 'week', 'month'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                style={{
                  minHeight: 44,
                  minWidth: 44,
                  padding: '6px 14px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: 8,
                  border: 'none',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                  transition: 'all 0.15s ease',
                  background: viewMode === mode ? accentColor : 'transparent',
                  color: viewMode === mode ? (isDark ? '#06131a' : '#121214') : '#9ca3af',
                }}
              >
                {mode}
              </button>
            ))}
          </div>

          <button
            onClick={() => setShowProposalHelper(!showProposalHelper)}
            title="Max Email/Text Proposal Helper"
            style={{
              minHeight: 44,
              padding: '8px 14px',
              borderRadius: 10,
              fontSize: '12px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: isDark ? '#1a222f' : '#222',
              color: '#fff',
              border: `1px solid ${accentColor}`,
              cursor: 'pointer',
            }}
          >
            <Sparkles size={15} color={accentColor} />
            <span className="hidden sm:inline">Draft Helper</span>
          </button>

          <button
            onClick={() => openQuickAdd('pickup')}
            style={{
              minHeight: 44,
              padding: '8px 16px',
              borderRadius: 10,
              fontSize: '12px',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: accentColor,
              color: isDark ? '#06131a' : '#121214',
              border: 'none',
              cursor: 'pointer',
              boxShadow: `0 2px 8px ${accentColor}40`,
            }}
          >
            <Plus size={16} />
            <span>+ Event</span>
          </button>
        </div>
      </header>

      {/* ── Main Content Container (Mobile-first, max-w, scrollable) ── */}
      <main className="w-full max-w-5xl mx-auto space-y-4">
        {/* ── 1. TODAY SUMMARY BANNER ── */}
        <section
          style={{
            background: cardBg,
            borderColor: cardBorder,
            borderRadius: '14px',
            border: `1px solid ${cardBorder}`,
            padding: '16px 20px',
          }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 border-b pb-3 border-[var(--border,#ece8e0)]">
            <div>
              <div style={{ color: accentColor, fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Clock size={13} /> Today at a Glance
              </div>
              <h2 style={{ fontSize: '17px', fontWeight: 700, color: textPrimary, margin: '2px 0 0 0' }}>
                {new Date().toLocaleDateString('en-US', {
                  weekday: 'long',
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </h2>
            </div>
            <div className="flex items-center gap-3">
              <div style={{ background: isDark ? '#161f2c' : '#faf9f7', border: `1px solid ${cardBorder}`, borderRadius: 10, padding: '6px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: '12px', color: textMuted }}>Today:</span>
                <span style={{ fontSize: '14px', fontWeight: 800, color: accentColor }}>
                  {todaySummary?.total_events_today ?? events.filter((e) => (e.start_time || '').startsWith(todayStr)).length}
                </span>
              </div>
              <div style={{ background: isDark ? '#161f2c' : '#faf9f7', border: `1px solid ${cardBorder}`, borderRadius: 10, padding: '6px 12px', display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: '12px', color: textMuted }}>Upcoming:</span>
                <span style={{ fontSize: '14px', fontWeight: 800, color: textPrimary }}>
                  {todaySummary?.upcoming_events_count ?? events.filter((e) => (e.start_time || '') > todayStr).length}
                </span>
              </div>
            </div>
          </div>

          {/* Quick-Add 1-Tap Row */}
          <div className="space-y-1.5">
            <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', color: textMuted, letterSpacing: '0.5px' }}>
              Quick-Add 1-Tap
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                onClick={() => openQuickAdd('pickup')}
                style={{
                  minHeight: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 10,
                  border: `1px solid ${cardBorder}`,
                  background: isDark ? '#161f2c' : '#faf9f7',
                  color: textPrimary,
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <PackageCheck size={16} color={accentColor} />
                <span>Picked up</span>
              </button>

              <button
                onClick={() => openQuickAdd('drop_off')}
                style={{
                  minHeight: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 10,
                  border: `1px solid ${cardBorder}`,
                  background: isDark ? '#161f2c' : '#faf9f7',
                  color: textPrimary,
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <PackageCheck size={16} color="#16a34a" />
                <span>Dropped off</span>
              </button>

              <button
                onClick={() => openQuickAdd('install')}
                style={{
                  minHeight: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 10,
                  border: `1px solid ${cardBorder}`,
                  background: isDark ? '#161f2c' : '#faf9f7',
                  color: textPrimary,
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <Wrench size={16} color="#3b82f6" />
                <span>Installation</span>
              </button>

              <button
                onClick={() => openQuickAdd('delivery')}
                style={{
                  minHeight: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  padding: '8px 12px',
                  borderRadius: 10,
                  border: `1px solid ${cardBorder}`,
                  background: isDark ? '#161f2c' : '#faf9f7',
                  color: textPrimary,
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                <Truck size={16} color="#f59e0b" />
                <span>Delivery</span>
              </button>
            </div>
          </div>
        </section>

        {/* ── Max Proposal Draft Helper Panel ── */}
        {showProposalHelper && (
          <section
            style={{
              background: cardBg,
              border: `1px solid ${accentColor}`,
              borderRadius: 14,
              padding: 16,
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Sparkles size={16} color={accentColor} />
                <h3 style={{ fontSize: '13px', fontWeight: 700, color: textPrimary, margin: 0 }}>
                  Max AI Schedule Proposal Assistant
                </h3>
              </div>
              <button
                onClick={() => setShowProposalHelper(false)}
                style={{ background: 'none', border: 'none', color: textMuted, cursor: 'pointer', padding: 4 }}
              >
                <X size={16} />
              </button>
            </div>

            <p style={{ fontSize: '11px', color: textMuted, marginBottom: 8 }}>
              Paste customer email, vendor text, or workroom notes to auto-detect pickup, delivery, and install events:
            </p>

            <textarea
              value={proposalText}
              onChange={(e) => setProposalText(e.target.value)}
              placeholder="e.g. 'Client says we can pick up the fabric bolts at the warehouse tomorrow at 10am, and delivery is set for Friday 2pm.'"
              rows={3}
              style={{
                width: '100%',
                padding: '10px 12px',
                fontSize: '12px',
                borderRadius: 10,
                border: `1px solid ${inputBorder}`,
                background: inputBg,
                color: textPrimary,
                outline: 'none',
                resize: 'none',
              }}
            />

            <div className="flex items-center justify-between mt-2 flex-wrap gap-2">
              <span style={{ fontSize: '11px', color: textMuted }}>{proposalNotice}</span>
              <button
                onClick={handleAnalyzeDraftProposals}
                disabled={extractingProposals || !proposalText.trim()}
                style={{
                  minHeight: 44,
                  padding: '8px 16px',
                  fontSize: '12px',
                  fontWeight: 700,
                  borderRadius: 10,
                  background: accentColor,
                  color: isDark ? '#06131a' : '#121214',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {extractingProposals ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles size={14} /> Detect Events
                  </>
                )}
              </button>
            </div>
          </section>
        )}

        {/* ── 2. VIEW CONTROLS & DATE NAV ── */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigateDate(-1)}
              style={{
                minHeight: 44,
                minWidth: 44,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 10,
                border: `1px solid ${cardBorder}`,
                background: cardBg,
                color: textPrimary,
                cursor: 'pointer',
              }}
              aria-label="Previous"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              onClick={jumpToToday}
              style={{
                minHeight: 44,
                padding: '8px 14px',
                fontSize: '12px',
                fontWeight: 700,
                borderRadius: 10,
                border: `1px solid ${cardBorder}`,
                background: cardBg,
                color: textPrimary,
                cursor: 'pointer',
              }}
            >
              Today
            </button>
            <button
              onClick={() => navigateDate(1)}
              style={{
                minHeight: 44,
                minWidth: 44,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: 10,
                border: `1px solid ${cardBorder}`,
                background: cardBg,
                color: textPrimary,
                cursor: 'pointer',
              }}
              aria-label="Next"
            >
              <ChevronRight size={18} />
            </button>
          </div>

          <div style={{ fontSize: '14px', fontWeight: 700, color: textPrimary }}>
            {viewMode === 'month'
              ? activeDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
              : viewMode === 'week'
              ? `Week of ${weekDays[0]?.label || ''} ${weekDays[0]?.dateStr || ''}`
              : activeDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
          </div>
        </div>

        {/* ── 3. VIEWS CONTAINER ── */}
        {scheduleError && (
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 10,
              border: `1px solid ${isDark ? 'rgba(239, 68, 68, 0.3)' : '#fecaca'}`,
              background: isDark ? 'rgba(239, 68, 68, 0.1)' : '#fef2f2',
              color: isDark ? '#f87171' : '#b91c1c',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <AlertCircle size={14} className="flex-shrink-0" />
            <span>Max API Notice: {scheduleError}. No simulated or mock data is shown.</span>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={28} className="animate-spin text-[#b8960c]" />
          </div>
        ) : viewMode === 'agenda' ? (
          /* ── AGENDA VIEW ── */
          <div className="space-y-4">
            {/* Today Section */}
            <div className="space-y-2">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: accentColor }}>
                <Clock size={12} /> Today ({agendaEvents.today.length})
              </div>
              {agendaEvents.today.length === 0 ? (
                <div style={{ padding: 14, textAlign: 'center', borderRadius: 10, background: cardBg, border: `1px dashed ${cardBorder}`, fontSize: '12px', color: textMuted }}>
                  No events scheduled for today.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {agendaEvents.today.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onCheckDone={handleCheckDone}
                      isDark={isDark}
                      cardBg={cardBg}
                      cardBorder={cardBorder}
                      textPrimary={textPrimary}
                      textMuted={textMuted}
                      accentColor={accentColor}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Upcoming Section */}
            <div className="space-y-2">
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '11px', fontWeight: 800, textTransform: 'uppercase', color: textMuted }}>
                <CalendarIcon size={12} /> Upcoming ({agendaEvents.upcoming.length})
              </div>
              {agendaEvents.upcoming.length === 0 ? (
                <div style={{ padding: 14, textAlign: 'center', borderRadius: 10, background: cardBg, border: `1px dashed ${cardBorder}`, fontSize: '12px', color: textMuted }}>
                  No upcoming events.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {agendaEvents.upcoming.map((event) => (
                    <EventCard
                      key={event.id}
                      event={event}
                      onCheckDone={handleCheckDone}
                      isDark={isDark}
                      cardBg={cardBg}
                      cardBorder={cardBorder}
                      textPrimary={textPrimary}
                      textMuted={textMuted}
                      accentColor={accentColor}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Recent Custody Log Summary */}
            <div style={{ paddingTop: 16, borderTop: `1px solid ${cardBorder}` }} className="space-y-3">
              <div className="flex items-center justify-between">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <PackageCheck size={18} color="#16a34a" />
                  <h3 style={{ fontSize: '13px', fontWeight: 800, color: textPrimary, textTransform: 'uppercase', margin: 0 }}>
                    Recent Custody Transfer Log (Pickups & Drop-offs)
                  </h3>
                </div>
                <button
                  onClick={() => {
                    setSelectedEventForDone(null);
                    setShowCustodyModal(true);
                  }}
                  style={{
                    minHeight: 44,
                    padding: '8px 12px',
                    fontSize: '12px',
                    fontWeight: 700,
                    color: accentColor,
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    textDecoration: 'underline',
                  }}
                >
                  + Record Custody Log
                </button>
              </div>

              {logs.length === 0 ? (
                <div style={{ padding: 16, textAlign: 'center', borderRadius: 10, background: cardBg, border: `1px dashed ${cardBorder}`, fontSize: '12px', color: textMuted }}>
                  No custody logs recorded yet.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {logs.slice(0, 6).map((log) => (
                    <div
                      key={log.id}
                      style={{
                        padding: 14,
                        borderRadius: 12,
                        border: `1px solid ${cardBorder}`,
                        background: cardBg,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 6,
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 800,
                            padding: '2px 8px',
                            borderRadius: 999,
                            textTransform: 'uppercase',
                            background: log.direction === 'picked_up' ? 'rgba(184, 150, 12, 0.2)' : 'rgba(22, 163, 74, 0.2)',
                            color: log.direction === 'picked_up' ? accentColor : '#16a34a',
                          }}
                        >
                          {log.direction === 'picked_up' ? 'Picked Up' : 'Dropped Off'}
                        </span>
                        <span style={{ fontSize: '10px', color: textMuted }}>
                          {log.timestamp.slice(0, 16).replace('T', ' ')}
                        </span>
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: textPrimary }}>
                        {log.items}
                      </div>
                      <div style={{ fontSize: '11px', color: textMuted }} className="truncate">
                        {log.party ? `Party: ${log.party}` : 'Party: N/A'}
                        {log.job_id ? ` · Job: ${log.job_id}` : ''}
                      </div>
                      {log.notes && (
                        <div style={{ fontSize: '11px', color: textMuted, fontStyle: 'italic' }}>
                          "{log.notes}"
                        </div>
                      )}
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
                const dayEvents = events.filter((e) => (e.start_time || '').startsWith(day.dateStr));
                return (
                  <div
                    key={day.dateStr}
                    style={{
                      borderRadius: 12,
                      padding: 10,
                      border: day.isToday ? `2px solid ${accentColor}` : `1px solid ${cardBorder}`,
                      background: day.isToday ? (isDark ? '#1a222f' : '#fdf8eb') : cardBg,
                      minHeight: 140,
                      display: 'flex',
                      flexDirection: 'column',
                    }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span style={{ fontSize: '10px', fontWeight: 700, color: textMuted }}>{day.label}</span>
                      <span style={{ fontSize: '12px', fontWeight: day.isToday ? 800 : 600, color: day.isToday ? accentColor : textPrimary }}>
                        {day.date.getDate()}
                      </span>
                    </div>

                    <div className="space-y-1.5 flex-1">
                      {dayEvents.map((ev) => (
                        <div
                          key={ev.id}
                          onClick={() => handleCheckDone(ev)}
                          style={{
                            padding: '6px 8px',
                            borderRadius: 8,
                            fontSize: '11px',
                            cursor: 'pointer',
                            border: `1px solid ${cardBorder}`,
                            background: ev.status === 'done' ? (isDark ? '#161f2c' : '#f1f1f1') : (isDark ? '#0b0f14' : '#faf9f7'),
                            opacity: ev.status === 'done' ? 0.6 : 1,
                            textDecoration: ev.status === 'done' ? 'line-through' : 'none',
                          }}
                        >
                          <div style={{ fontWeight: 700, color: textPrimary }} className="truncate">
                            {ev.title}
                          </div>
                          <div style={{ fontSize: '10px', color: textMuted }}>
                            {ev.start_time.slice(11, 16)} · {ev.type}
                          </div>
                        </div>
                      ))}
                      {dayEvents.length === 0 && (
                        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', color: textMuted, fontStyle: 'italic' }}>
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
            style={{
              borderRadius: 14,
              border: `1px solid ${cardBorder}`,
              background: cardBg,
              overflow: 'hidden',
            }}
          >
            {/* Day Header Row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                borderBottom: `1px solid ${cardBorder}`,
                background: isDark ? '#161f2c' : '#faf9f7',
              }}
            >
              {DAYS_OF_WEEK.map((d) => (
                <div
                  key={d}
                  style={{
                    padding: '8px 4px',
                    textAlign: 'center',
                    fontSize: '10px',
                    fontWeight: 700,
                    color: textMuted,
                    textTransform: 'uppercase',
                  }}
                >
                  {d}
                </div>
              ))}
            </div>

            {/* Grid Cells */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)' }}>
              {monthData.cells.map((cell, idx) => {
                const dayEvents = cell.dateStr ? events.filter((e) => (e.start_time || '').startsWith(cell.dateStr)) : [];
                return (
                  <div
                    key={idx}
                    style={{
                      minHeight: 85,
                      padding: 6,
                      borderBottom: `1px solid ${cardBorder}`,
                      borderRight: `1px solid ${cardBorder}`,
                      background: cell.day === null ? (isDark ? '#0b0f14' : '#faf9f7') : cell.isToday ? (isDark ? '#1a222f' : '#fdf8eb') : 'transparent',
                    }}
                  >
                    {cell.day !== null && (
                      <div className="flex flex-col h-full justify-between">
                        <div className="flex items-center justify-between">
                          <span
                            style={{
                              fontSize: '12px',
                              fontWeight: cell.isToday ? 800 : 600,
                              color: cell.isToday ? accentColor : textPrimary,
                            }}
                          >
                            {cell.day}
                          </span>
                          {dayEvents.length > 0 && (
                            <span
                              style={{
                                fontSize: '9px',
                                fontWeight: 800,
                                padding: '1px 5px',
                                borderRadius: 4,
                                background: accentColor,
                                color: isDark ? '#06131a' : '#121214',
                              }}
                            >
                              {dayEvents.length}
                            </span>
                          )}
                        </div>

                        <div className="space-y-1 mt-1">
                          {dayEvents.slice(0, 2).map((ev) => (
                            <div
                              key={ev.id}
                              style={{
                                fontSize: '9px',
                                fontWeight: 600,
                                padding: 2,
                                borderRadius: 4,
                                border: `1px solid ${cardBorder}`,
                                background: isDark ? '#161f2c' : '#faf9f7',
                                color: textPrimary,
                              }}
                              className="truncate"
                              title={`${ev.title} (${ev.type})`}
                            >
                              {ev.title}
                            </div>
                          ))}
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

      {/* ── MODAL: QUICK / EVENT ADD (Empire Design System) ── */}
      {showAddModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
            background: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(3px)',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: 500,
              maxHeight: '90vh',
              overflowY: 'auto',
              borderRadius: 16,
              background: modalBg,
              border: headerBorder,
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                background: headerBg,
                color: '#fff',
                padding: '16px 20px',
                borderBottom: headerBorder,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span
                  style={{
                    background: badgeBg,
                    color: badgeText,
                    fontSize: '11px',
                    fontWeight: 800,
                    padding: '4px 8px',
                    borderRadius: 6,
                  }}
                >
                  EMPIRE WORKROOM
                </span>
                <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#fff', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CalendarIcon size={16} color={accentColor} /> Schedule Event
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                aria-label="Close schedule modal"
                style={{
                  minHeight: 44,
                  minWidth: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: 8,
                  color: '#fff',
                  cursor: 'pointer',
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Body */}
            <form onSubmit={handleSaveEvent} style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              {formError && (
                <div style={{ padding: '8px 12px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid #f87171', borderRadius: 8, color: '#f87171', fontSize: '12px' }}>
                  {formError}
                </div>
              )}

              {/* Linked Job (Quick-select & auto-fill) */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Linked Job (Optional - Auto-Fills Party)
                </label>
                <div style={{ position: 'relative' }}>
                  <button
                    type="button"
                    onClick={() => setShowAddJobDropdown(!showAddJobDropdown)}
                    style={{
                      width: '100%',
                      minHeight: 44,
                      padding: '10px 14px',
                      borderRadius: 10,
                      border: `1px solid ${inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      fontWeight: 600,
                      textAlign: 'left',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                    }}
                  >
                    <span className="truncate">
                      {formJobId
                        ? (() => {
                            const match = jobs.find((j) => String(j.id) === String(formJobId) || String(j.job_number) === String(formJobId));
                            return match ? `${match.job_number || match.id}: ${match.customer_name || match.client_name} — ${match.title}` : `Job: ${formJobId}`;
                          })()
                        : 'Select a live job to auto-fill...'}
                    </span>
                    <ChevronDown size={16} color={textMuted} />
                  </button>

                  {showAddJobDropdown && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 70,
                        marginTop: 4,
                        maxHeight: 200,
                        overflowY: 'auto',
                        borderRadius: 10,
                        background: cardBg,
                        border: `1px solid ${cardBorder}`,
                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                      }}
                    >
                      <div
                        onClick={() => {
                          setFormJobId('');
                          setShowAddJobDropdown(false);
                        }}
                        style={{
                          padding: '10px 14px',
                          fontSize: '12px',
                          borderBottom: `1px solid ${cardBorder}`,
                          cursor: 'pointer',
                          color: textMuted,
                          minHeight: 44,
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        No linked job
                      </div>
                      {jobsLoading ? (
                        <div style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: 8, fontSize: '12px', color: textMuted }}>
                          <Loader2 size={14} className="animate-spin" /> Loading jobs from Max API...
                        </div>
                      ) : jobs.length === 0 ? (
                        <div style={{ padding: '12px', fontSize: '11px', color: textMuted }}>
                          {jobsError || 'No jobs found in Max API.'}
                        </div>
                      ) : (
                        jobs.map((j) => (
                          <div
                            key={j.id}
                            onClick={() => {
                              setFormJobId(j.id || j.job_number);
                              if (j.customer_name || j.client_name) {
                                setFormCustomerVendor(j.customer_name || j.client_name);
                              }
                              if (j.title) {
                                setFormTitle(`${TYPE_CONFIG[formType]?.label || 'Event'}: ${j.title}`);
                              }
                              setShowAddJobDropdown(false);
                            }}
                            style={{
                              padding: '10px 14px',
                              fontSize: '12px',
                              cursor: 'pointer',
                              color: textPrimary,
                              borderBottom: `1px solid ${cardBorder}`,
                              minHeight: 44,
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'center',
                            }}
                          >
                            <div style={{ fontWeight: 700, color: accentColor }}>
                              {j.job_number || j.id}: {j.customer_name || j.client_name}
                            </div>
                            <div style={{ fontSize: '11px', color: textMuted }} className="truncate">
                              {j.title}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Type Selector */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Event Type
                </label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value as EventType)}
                  style={{
                    width: '100%',
                    minHeight: 44,
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: `1px solid ${inputBorder}`,
                    background: inputBg,
                    color: textPrimary,
                    fontSize: '13px',
                    fontWeight: 600,
                    outline: 'none',
                  }}
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

              {/* Title */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Title *
                </label>
                <input
                  type="text"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g. Pick up drapery fabrics"
                  required
                  style={{
                    width: '100%',
                    minHeight: 44,
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: `1px solid ${inputBorder}`,
                    background: inputBg,
                    color: textPrimary,
                    fontSize: '13px',
                    fontWeight: 600,
                    outline: 'none',
                  }}
                />
              </div>

              {/* Customer / Vendor / Party (Typeahead / Searchable) */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Customer / Vendor / Party
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    value={formCustomerVendor}
                    onChange={(e) => {
                      setFormCustomerVendor(e.target.value);
                      setShowAddPartyDropdown(true);
                    }}
                    onFocus={() => setShowAddPartyDropdown(true)}
                    placeholder="Search customer, vendor, or enter custom party..."
                    style={{
                      width: '100%',
                      minHeight: 44,
                      padding: '10px 14px',
                      borderRadius: 10,
                      border: `1px solid ${inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      outline: 'none',
                    }}
                  />
                  {showAddPartyDropdown && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 70,
                        marginTop: 4,
                        maxHeight: 220,
                        overflowY: 'auto',
                        borderRadius: 10,
                        background: cardBg,
                        border: `1px solid ${cardBorder}`,
                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                      }}
                    >
                      {availableParties.filter((p) =>
                        p.name.toLowerCase().includes(formCustomerVendor.toLowerCase())
                      ).length === 0 ? (
                        <div style={{ padding: '10px 12px', fontSize: '11px', color: textMuted }}>
                          No matching presets or Max API contacts. Custom party name will be saved.
                        </div>
                      ) : (
                        availableParties
                          .filter((p) => p.name.toLowerCase().includes(formCustomerVendor.toLowerCase()))
                          .map((p) => (
                            <div
                              key={`${p.category}-${p.name}`}
                              onClick={() => {
                                setFormCustomerVendor(p.name);
                                setShowAddPartyDropdown(false);
                              }}
                              style={{
                                padding: '8px 12px',
                                fontSize: '12px',
                                cursor: 'pointer',
                                color: textPrimary,
                                borderBottom: `1px solid ${cardBorder}`,
                                minHeight: 40,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                              }}
                            >
                              <span style={{ fontWeight: 600 }}>{p.name}</span>
                              <span
                                style={{
                                  fontSize: '10px',
                                  padding: '2px 6px',
                                  borderRadius: 4,
                                  background: p.isPreset
                                    ? (isDark ? 'rgba(34, 211, 238, 0.15)' : '#fef3c7')
                                    : (isDark ? 'rgba(255,255,255,0.08)' : '#f1f1f1'),
                                  color: p.isPreset ? accentColor : textMuted,
                                  fontWeight: 700,
                                }}
                              >
                                {p.category}
                              </span>
                            </div>
                          ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Date & Time Row */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                    Date
                  </label>
                  <input
                    type="date"
                    value={formDate}
                    onChange={(e) => setFormDate(e.target.value)}
                    style={{
                      width: '100%',
                      minHeight: 44,
                      padding: '10px 12px',
                      borderRadius: 10,
                      border: `1px solid ${inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                    Start Time
                  </label>
                  <input
                    type="time"
                    value={formStartTime}
                    onChange={(e) => setFormStartTime(e.target.value)}
                    style={{
                      width: '100%',
                      minHeight: 44,
                      padding: '10px 12px',
                      borderRadius: 10,
                      border: `1px solid ${inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                    End Time
                  </label>
                  <input
                    type="time"
                    value={formEndTime}
                    onChange={(e) => setFormEndTime(e.target.value)}
                    style={{
                      width: '100%',
                      minHeight: 44,
                      padding: '10px 12px',
                      borderRadius: 10,
                      border: `1px solid ${inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      outline: 'none',
                    }}
                  />
                </div>
              </div>

              {/* Location & Notes */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Location Address
                </label>
                <input
                  type="text"
                  value={formLocation}
                  onChange={(e) => setFormLocation(e.target.value)}
                  placeholder="e.g. 1420 Luxury Lane or Warehouse Dock B"
                  style={{
                    width: '100%',
                    minHeight: 44,
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: `1px solid ${inputBorder}`,
                    background: inputBg,
                    color: textPrimary,
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Notes
                </label>
                <textarea
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  placeholder="Gate code, receiving contact, special instructions..."
                  rows={2}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: `1px solid ${inputBorder}`,
                    background: inputBg,
                    color: textPrimary,
                    fontSize: '13px',
                    outline: 'none',
                    resize: 'none',
                  }}
                />
              </div>

              {/* Modal Footer */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10, paddingTop: 12, borderTop: `1px solid ${cardBorder}` }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  style={{
                    minHeight: 44,
                    padding: '10px 18px',
                    borderRadius: 10,
                    border: `1px solid ${cardBorder}`,
                    background: 'transparent',
                    color: textMuted,
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingEvent}
                  style={{
                    minHeight: 44,
                    padding: '10px 22px',
                    borderRadius: 10,
                    border: 'none',
                    background: accentColor,
                    color: isDark ? '#06131a' : '#121214',
                    fontSize: '13px',
                    fontWeight: 800,
                    cursor: 'pointer',
                    boxShadow: `0 2px 10px ${accentColor}40`,
                  }}
                >
                  {savingEvent ? 'Saving...' : 'Create Event'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: CUSTODY LOG / RECORD TRANSFER (Empire Design System) ── */}
      {showCustodyModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 60,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
            background: 'rgba(0, 0, 0, 0.7)',
            backdropFilter: 'blur(3px)',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: 540,
              maxHeight: '92vh',
              overflowY: 'auto',
              borderRadius: 16,
              background: modalBg,
              border: headerBorder,
              boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                background: headerBg,
                color: '#fff',
                padding: '16px 20px',
                borderBottom: headerBorder,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span
                  style={{
                    background: badgeBg,
                    color: badgeText,
                    fontSize: '11px',
                    fontWeight: 800,
                    padding: '4px 8px',
                    borderRadius: 6,
                  }}
                >
                  EMPIRE WORKROOM
                </span>
                <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#fff', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <PackageCheck size={18} color="#16a34a" /> Record Custody Transfer Log
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowCustodyModal(false)}
                aria-label="Close custody modal"
                style={{
                  minHeight: 44,
                  minWidth: 44,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: 8,
                  color: '#fff',
                  cursor: 'pointer',
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleSaveCustodyLog} style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Direction Toggle (Min 44px tap targets) */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Transfer Direction *
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <button
                    type="button"
                    onClick={() => setCustodyDirection('picked_up')}
                    style={{
                      minHeight: 44,
                      padding: '10px 14px',
                      fontSize: '13px',
                      fontWeight: 800,
                      borderRadius: 10,
                      border: custodyDirection === 'picked_up' ? `2px solid ${accentColor}` : `1px solid ${cardBorder}`,
                      background: custodyDirection === 'picked_up' ? (isDark ? '#1a222f' : '#fdf8eb') : (isDark ? '#161f2c' : '#ffffff'),
                      color: custodyDirection === 'picked_up' ? accentColor : textMuted,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                    }}
                  >
                    <PackageCheck size={16} color={custodyDirection === 'picked_up' ? accentColor : textMuted} />
                    Picked Up
                  </button>

                  <button
                    type="button"
                    onClick={() => setCustodyDirection('dropped_off')}
                    style={{
                      minHeight: 44,
                      padding: '10px 14px',
                      fontSize: '13px',
                      fontWeight: 800,
                      borderRadius: 10,
                      border: custodyDirection === 'dropped_off' ? '2px solid #16a34a' : `1px solid ${cardBorder}`,
                      background: custodyDirection === 'dropped_off' ? 'rgba(22, 163, 74, 0.15)' : (isDark ? '#161f2c' : '#ffffff'),
                      color: custodyDirection === 'dropped_off' ? '#16a34a' : textMuted,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                    }}
                  >
                    <PackageCheck size={16} color={custodyDirection === 'dropped_off' ? '#16a34a' : textMuted} />
                    Dropped Off
                  </button>
                </div>
              </div>

              {/* Linked Job (3: Searchable dropdown auto-filling party & items) */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Linked Job (Auto-fills Party & Item Lines)
                </label>
                <div style={{ position: 'relative' }}>
                  <button
                    type="button"
                    onClick={() => setShowJobDropdown(!showJobDropdown)}
                    style={{
                      width: '100%',
                      minHeight: 44,
                      padding: '10px 14px',
                      borderRadius: 10,
                      border: `1px solid ${custodyJobId ? accentColor : inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      fontWeight: 600,
                      textAlign: 'left',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                    }}
                  >
                    <span className="truncate">
                      {selectedCustodyJob
                        ? `${selectedCustodyJob.job_number || selectedCustodyJob.id}: ${selectedCustodyJob.customer_name || selectedCustodyJob.client_name} — ${selectedCustodyJob.title}`
                        : 'Select linked live job...'}
                    </span>
                    <ChevronDown size={16} color={textMuted} />
                  </button>

                  {showJobDropdown && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 70,
                        marginTop: 4,
                        maxHeight: 220,
                        overflowY: 'auto',
                        borderRadius: 10,
                        background: cardBg,
                        border: `1px solid ${cardBorder}`,
                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                      }}
                    >
                      <div
                        onClick={() => {
                          setCustodyJobId('');
                          setShowJobDropdown(false);
                        }}
                        style={{
                          padding: '10px 14px',
                          fontSize: '12px',
                          borderBottom: `1px solid ${cardBorder}`,
                          cursor: 'pointer',
                          color: textMuted,
                          minHeight: 44,
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        No linked job
                      </div>
                      {jobsLoading ? (
                        <div style={{ padding: '12px', display: 'flex', alignItems: 'center', gap: 8, fontSize: '12px', color: textMuted }}>
                          <Loader2 size={14} className="animate-spin" /> Loading jobs from Max API...
                        </div>
                      ) : jobs.length === 0 ? (
                        <div style={{ padding: '12px', fontSize: '11px', color: textMuted }}>
                          {jobsError || 'No jobs found in Max API.'}
                        </div>
                      ) : (
                        jobs.map((j) => (
                          <div
                            key={j.id}
                            onClick={() => handleSelectCustodyJob(j)}
                            style={{
                              padding: '10px 14px',
                              fontSize: '12px',
                              cursor: 'pointer',
                              color: textPrimary,
                              borderBottom: `1px solid ${cardBorder}`,
                              minHeight: 44,
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'center',
                            }}
                          >
                            <div style={{ fontWeight: 700, color: accentColor }}>
                              {j.job_number || j.id}: {j.customer_name || j.client_name}
                            </div>
                            <div style={{ fontSize: '11px', color: textMuted }} className="truncate">
                              {j.title}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* From / To Party (2: Searchable dropdown with customers, vendors, places + custom entry) */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  From / To Party *
                </label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    value={custodyParty}
                    onChange={(e) => {
                      setCustodyParty(e.target.value);
                      setShowPartyDropdown(true);
                    }}
                    onFocus={() => setShowPartyDropdown(true)}
                    placeholder="Search customer, vendor (Nelma's, Whittington), place (Warehouse), or type..."
                    required
                    style={{
                      width: '100%',
                      minHeight: 44,
                      padding: '10px 14px',
                      borderRadius: 10,
                      border: `1px solid ${inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      fontWeight: 600,
                      outline: 'none',
                    }}
                  />

                  {showPartyDropdown && (
                    <div
                      style={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 70,
                        marginTop: 4,
                        maxHeight: 220,
                        overflowY: 'auto',
                        borderRadius: 10,
                        background: cardBg,
                        border: `1px solid ${cardBorder}`,
                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                      }}
                    >
                      {availableParties.filter((p) =>
                        p.name.toLowerCase().includes(custodyParty.toLowerCase())
                      ).length === 0 ? (
                        <div style={{ padding: '10px 12px', fontSize: '11px', color: textMuted }}>
                          No matching presets or Max API contacts. Custom party name will be recorded.
                        </div>
                      ) : (
                        availableParties
                          .filter((p) => p.name.toLowerCase().includes(custodyParty.toLowerCase()))
                          .map((p) => (
                            <div
                              key={`${p.category}-${p.name}`}
                              onClick={() => {
                                setCustodyParty(p.name);
                                setShowPartyDropdown(false);
                              }}
                              style={{
                                padding: '8px 12px',
                                fontSize: '12px',
                                cursor: 'pointer',
                                color: textPrimary,
                                borderBottom: `1px solid ${cardBorder}`,
                                minHeight: 44,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                              }}
                            >
                              <span style={{ fontWeight: 600 }}>{p.name}</span>
                              <span
                                style={{
                                  fontSize: '10px',
                                  padding: '2px 6px',
                                  borderRadius: 4,
                                  background: p.isPreset
                                    ? (isDark ? 'rgba(34, 211, 238, 0.15)' : '#fef3c7')
                                    : (isDark ? 'rgba(255,255,255,0.08)' : '#f1f1f1'),
                                  color: p.isPreset ? accentColor : textMuted,
                                  fontWeight: 700,
                                }}
                              >
                                {p.category}
                              </span>
                            </div>
                          ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* What Changed Hands (1: Multi-select quick-pills, quote items, + custom entry) */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <label style={{ fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase' }}>
                    What Changed Hands (Items) *
                  </label>
                  {selectedCustodyJob && (
                    <span style={{ fontSize: '10px', color: accentColor, fontWeight: 700, marginLeft: 'auto' }}>
                      Pilled from {selectedCustodyJob.job_number || selectedCustodyJob.id}
                    </span>
                  )}
                </div>

                {/* Quick-Select Pills (Common items + Job quote lines) */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                  {availableCustodyItems.map((item) => {
                    const isSelected = custodySelectedChips.includes(item);
                    return (
                      <button
                        key={item}
                        type="button"
                        onClick={() => handleToggleItemChip(item)}
                        style={{
                          minHeight: 36,
                          padding: '6px 12px',
                          borderRadius: 8,
                          fontSize: '12px',
                          fontWeight: isSelected ? 700 : 500,
                          cursor: 'pointer',
                          border: isSelected ? `1.5px solid ${accentColor}` : `1px solid ${cardBorder}`,
                          background: isSelected ? (isDark ? 'rgba(34, 211, 238, 0.18)' : '#fdf8eb') : (isDark ? '#161f2c' : '#faf9f7'),
                          color: isSelected ? accentColor : textPrimary,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {isSelected && <Check size={12} />}
                        <span>{item}</span>
                      </button>
                    );
                  })}
                </div>

                {/* Custom Entry input */}
                <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
                  <input
                    type="text"
                    value={customItemInput}
                    onChange={(e) => setCustomItemInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddCustomItem();
                      }
                    }}
                    placeholder="Type custom item (e.g. 4 bolster pillows, brass hardware)..."
                    style={{
                      flex: 1,
                      minHeight: 44,
                      padding: '10px 14px',
                      borderRadius: 10,
                      border: `1px solid ${inputBorder}`,
                      background: inputBg,
                      color: textPrimary,
                      fontSize: '13px',
                      outline: 'none',
                    }}
                  />
                  <button
                    type="button"
                    onClick={handleAddCustomItem}
                    style={{
                      minHeight: 44,
                      padding: '10px 16px',
                      borderRadius: 10,
                      border: `1px solid ${accentColor}`,
                      background: 'transparent',
                      color: accentColor,
                      fontSize: '12px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    + Add
                  </button>
                </div>

                {/* Combined editable string field */}
                <input
                  type="text"
                  value={custodyItems}
                  onChange={(e) => {
                    setCustodyItems(e.target.value);
                    setCustodySelectedChips(e.target.value.split(',').map((s) => s.trim()).filter(Boolean));
                  }}
                  placeholder="Items summary (comma separated)..."
                  required
                  style={{
                    width: '100%',
                    minHeight: 44,
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: `1px solid ${inputBorder}`,
                    background: inputBg,
                    color: textPrimary,
                    fontSize: '13px',
                    fontWeight: 600,
                    outline: 'none',
                  }}
                />
              </div>

              {/* Notes */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: textMuted, textTransform: 'uppercase', marginBottom: 6 }}>
                  Notes & Sign-off Details
                </label>
                <textarea
                  value={custodyNotes}
                  onChange={(e) => setCustodyNotes(e.target.value)}
                  rows={2}
                  placeholder="Condition notes, fabric inspection, signature reference..."
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 10,
                    border: `1px solid ${inputBorder}`,
                    background: inputBg,
                    color: textPrimary,
                    fontSize: '13px',
                    outline: 'none',
                    resize: 'none',
                  }}
                />
              </div>

              {/* Modal Footer */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10, paddingTop: 12, borderTop: `1px solid ${cardBorder}` }}>
                <button
                  type="button"
                  onClick={() => setShowCustodyModal(false)}
                  style={{
                    minHeight: 44,
                    padding: '10px 18px',
                    borderRadius: 10,
                    border: `1px solid ${cardBorder}`,
                    background: 'transparent',
                    color: textMuted,
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingCustody}
                  style={{
                    minHeight: 44,
                    padding: '10px 22px',
                    borderRadius: 10,
                    border: 'none',
                    background: '#16a34a',
                    color: '#ffffff',
                    fontSize: '13px',
                    fontWeight: 800,
                    cursor: 'pointer',
                    boxShadow: '0 2px 10px rgba(22, 163, 74, 0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  {savingCustody ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Recording...
                    </>
                  ) : (
                    <>
                      <PackageCheck size={16} /> Record Log & Complete
                    </>
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

// ── SUB-COMPONENT: EVENT CARD (Empire Design Tokens) ──
function EventCard({
  event,
  onCheckDone,
  isDark,
  cardBg,
  cardBorder,
  textPrimary,
  textMuted,
  accentColor,
}: {
  event: ScheduleEvent;
  onCheckDone: (e: ScheduleEvent) => void;
  isDark: boolean;
  cardBg: string;
  cardBorder: string;
  textPrimary: string;
  textMuted: string;
  accentColor: string;
}) {
  const isDone = event.status === 'done';
  const cfg = TYPE_CONFIG[event.type] || TYPE_CONFIG.other;
  const Icon = cfg.icon;

  const mapUrl = event.location_address
    ? `https://maps.google.com/?q=${encodeURIComponent(event.location_address)}`
    : null;

  const timeStr = event.start_time ? event.start_time.slice(11, 16) : '--:--';
  const endTimeStr = event.end_time ? event.end_time.slice(11, 16) : null;

  return (
    <div
      style={{
        borderRadius: 14,
        padding: '14px 18px',
        border: `1px solid ${cardBorder}`,
        background: cardBg,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        opacity: isDone ? 0.65 : 1,
        transition: 'all 0.15s ease',
      }}
      className="sm:flex-row sm:items-center sm:justify-between"
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, minWidth: 0 }}>
        {/* Min 44px tap target checkbox */}
        <button
          onClick={() => onCheckDone(event)}
          style={{
            minWidth: 44,
            minHeight: 44,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            flexShrink: 0,
          }}
          title={isDone ? 'Mark as planned' : 'Mark done and log custody transfer'}
          aria-label="Toggle completed"
        >
          {isDone ? (
            <CheckCircle size={22} color="#16a34a" />
          ) : (
            <Circle size={22} color={isDark ? '#4b5563' : '#d1d5db'} />
          )}
        </button>

        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 800,
                padding: '2px 8px',
                borderRadius: 6,
                textTransform: 'uppercase',
                background: isDark ? cfg.darkBg : cfg.bgLight,
                color: isDark ? cfg.darkText : cfg.textLight,
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <Icon size={12} />
              {cfg.label}
            </span>

            {event.job_id && (
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 6,
                  background: isDark ? 'rgba(34, 211, 238, 0.15)' : '#fdf8eb',
                  color: accentColor,
                }}
              >
                {event.job_id}
              </span>
            )}
          </div>

          <h4
            style={{
              fontSize: '14px',
              fontWeight: 700,
              color: textPrimary,
              margin: '4px 0 2px 0',
              textDecoration: isDone ? 'line-through' : 'none',
            }}
          >
            {event.title}
          </h4>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: '11px', color: textMuted, flexWrap: 'wrap' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Clock size={12} />
              {timeStr} {endTimeStr ? `- ${endTimeStr}` : ''}
            </span>

            {event.customer_vendor && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <User size={12} />
                {event.customer_vendor}
              </span>
            )}

            {event.location_address && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <MapPin size={12} />
                {event.location_address}
              </span>
            )}
          </div>

          {event.notes && (
            <p style={{ fontSize: '11px', color: textMuted, margin: '4px 0 0 0', fontStyle: 'italic' }}>
              {event.notes}
            </p>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, alignSelf: 'flex-end' }} className="sm:align-self-center">
        {mapUrl && (
          <a
            href={mapUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              minHeight: 44,
              minWidth: 44,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 8,
              border: `1px solid ${cardBorder}`,
              background: cardBg,
              color: textMuted,
              textDecoration: 'none',
            }}
            title="Open in Maps"
          >
            <ExternalLink size={16} />
          </a>
        )}
      </div>
    </div>
  );
}
