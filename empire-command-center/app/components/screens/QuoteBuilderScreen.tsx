'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  ArrowLeft, ArrowRight, User, Camera, Layers, Settings, FileText,
  Plus, Trash2, Upload, X, Check, Loader2, ChevronDown, GripVertical, Search,
  Eye, Download, Sparkles, ImageIcon, FolderOpen, CheckSquare, Edit3, Box, Ruler, CheckCircle
} from 'lucide-react';
import MeasurementDiagram from '../business/quotes/MeasurementDiagram';
import dynamic from 'next/dynamic';

const CushionBuilder = dynamic(() => import('../business/upholstery/CushionBuilder'), { ssr: false });

interface CustomerInfo {
  name: string;
  email: string;
  phone: string;
  address: string;
}

interface PhotoFile {
  file?: File;
  preview: string;
  uploadedFilename?: string;
  serverUrl?: string;
  originalName?: string;
  fromIntake?: boolean;
}

interface AnalysisItem {
  type: string;
  description: string;
  width?: string;
  height?: string;
  depth?: string;
  condition?: string;
  checked?: boolean;
}

interface RoomItem {
  id: string;
  type: string;
  width: string;
  height: string;
  depth: string;
  quantity: number;
  notes: string;
}

interface Room {
  id: string;
  name: string;
  items: RoomItem[];
}

interface QuoteOptions {
  fabricGrade: 'A' | 'B' | 'C';
  liningType: 'standard' | 'blackout' | 'interlining' | 'thermal' | 'none';
  tufting: boolean;
  welting: boolean;
  nailhead: boolean;
  skirt: boolean;
  contrastPiping: boolean;
  patternMatch: boolean;
  rushOrder: boolean;
  delivery: boolean;
}

const ITEM_TYPES = [
  'sofa', 'loveseat', 'chair', 'dining_chair', 'ottoman', 'bench', 'headboard', 'sectional',
  'drapery', 'roman_shade', 'valance', 'cornice',
  'cushion', 'throw_pillow', 'bedskirt', 'duvet', 'table_runner', 'placemats',
];

type QuoteInputMethod = 'photos' | '3dscan' | 'manual' | 'intake';

type ManualItemType = 'window' | 'sofa' | 'chair' | 'cushion' | 'pillow' | 'cornice' | 'valance' | 'roman_shade' | 'other';

const MANUAL_ITEM_TYPES: { key: ManualItemType; label: string; icon: string }[] = [
  { key: 'window', label: 'Window', icon: '🪟' },
  { key: 'sofa', label: 'Sofa', icon: '🛋' },
  { key: 'chair', label: 'Chair', icon: '💺' },
  { key: 'cushion', label: 'Cushion', icon: '🛏' },
  { key: 'pillow', label: 'Pillow', icon: '🛌' },
  { key: 'cornice', label: 'Cornice', icon: '📐' },
  { key: 'valance', label: 'Valance', icon: '🎪' },
  { key: 'roman_shade', label: 'Roman Shade', icon: '🪟' },
  { key: 'other', label: 'Other', icon: '📏' },
];

const STEPS = [
  { id: 1, label: 'Customer', icon: User },
  { id: 2, label: 'Photos', icon: Camera },
  { id: 3, label: 'Rooms & Items', icon: Layers },
  { id: 4, label: 'Options', icon: Settings },
  { id: 5, label: 'Review', icon: FileText },
];

const TIERS = [
  { label: 'Essential', key: 'A', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
  { label: 'Designer', key: 'B', color: '#b8960c', bg: '#fdf8eb', border: '#f5ecd0' },
  { label: 'Premium', key: 'C', color: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff' },
];

interface Props {
  onBack: () => void;
  editQuoteId?: string;
}

export default function QuoteBuilderScreen({ onBack, editQuoteId }: Props) {
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');

  const [customer, setCustomer] = useState<CustomerInfo>({ name: '', email: '', phone: '', address: '' });
  const [photos, setPhotos] = useState<PhotoFile[]>([]);
  const [rooms, setRooms] = useState<Room[]>([{ id: crypto.randomUUID(), name: 'Living Room', items: [] }]);
  const [options, setOptions] = useState<QuoteOptions>({
    fabricGrade: 'B', liningType: 'standard',
    tufting: false, welting: false, nailhead: false, skirt: false,
    contrastPiping: false, patternMatch: false, rushOrder: false, delivery: false,
  });

  // Intake project loading
  const [intakeProjects, setIntakeProjects] = useState<any[]>([]);
  const [loadingIntake, setLoadingIntake] = useState(false);
  const [selectedIntakeId, setSelectedIntakeId] = useState<string | null>(null);

  // Photo analysis
  const [analyzingPhoto, setAnalyzingPhoto] = useState<number | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisItem[] | null>(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [analysisPhotoIdx, setAnalysisPhotoIdx] = useState<number | null>(null);

  const API_BASE = API.replace(/\/api\/v1$/, '');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch intake projects when entering Photos step
  useEffect(() => {
    if (step === 2) {
      setLoadingIntake(true);
      fetch(`${API}/intake/admin/projects-with-photos`)
        .then(r => r.json())
        .then(data => setIntakeProjects(data.projects || data || []))
        .catch(() => {})
        .finally(() => setLoadingIntake(false));
    }
  }, [step]);

  // Load intake project photos and customer info
  const loadIntakeProject = (project: any) => {
    setSelectedIntakeId(project.id);
    const intakePhotos: PhotoFile[] = (project.photos || []).map((p: any) => ({
      preview: `${API_BASE}${p.url || p.path}`,
      serverUrl: `${API_BASE}${p.url || p.path}`,
      originalName: p.original_name || p.filename,
      fromIntake: true,
    }));
    setPhotos(prev => [...intakePhotos, ...prev.filter(p => !p.fromIntake)]);
    // Auto-fill customer info
    if (project.customer_name) {
      setCustomer({
        name: project.customer_name || '',
        email: project.customer_email || '',
        phone: project.customer_phone || '',
        address: project.address || '',
      });
    }
  };

  // Analyze a photo via vision API
  const analyzePhoto = async (idx: number) => {
    setAnalyzingPhoto(idx);
    setAnalysisResult(null);
    setShowAnalysis(true);
    setAnalysisPhotoIdx(idx);

    try {
      const photo = photos[idx];
      let base64: string;

      if (photo.serverUrl) {
        // Fetch server photo and convert to base64
        const res = await fetch(photo.serverUrl);
        const blob = await res.blob();
        base64 = await new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
          reader.readAsDataURL(blob);
        });
      } else if (photo.file) {
        base64 = await new Promise<string>((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
          reader.readAsDataURL(photo.file!);
        });
      } else {
        throw new Error('No photo source available');
      }

      const res = await fetch(`${API}/vision/room-scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64 }),
      });

      if (res.ok) {
        const data = await res.json();
        // room-scan returns {windows: [{name, width_inches, height_inches, window_type, ...}], ...}
        const windows = data.windows || data.items || data.detected_items || [];
        const items: AnalysisItem[] = windows.map((it: any) => ({
          type: it.window_type || it.type || it.item_type || 'drapery',
          description: it.name || it.description || '',
          width: it.width_inches ? `${it.width_inches}"` : (it.width || ''),
          height: it.height_inches ? `${it.height_inches}"` : (it.height || ''),
          depth: it.depth || it.dimensions?.depth || '',
          condition: it.condition || it.notes || '',
          checked: true,
        }));
        setAnalysisResult(items);
      } else {
        setAnalysisResult([]);
      }
    } catch {
      setAnalysisResult([]);
    }
    setAnalyzingPhoto(null);
  };

  // Add analyzed items to rooms
  const addAnalyzedItems = () => {
    if (!analysisResult) return;
    const selected = analysisResult.filter(it => it.checked);
    if (selected.length === 0) return;

    const newItems: RoomItem[] = selected.map(it => ({
      id: crypto.randomUUID(),
      type: ITEM_TYPES.includes(it.type) ? it.type : 'sofa',
      width: it.width || '',
      height: it.height || '',
      depth: it.depth || '',
      quantity: 1,
      notes: [it.description, it.condition].filter(Boolean).join(' - '),
    }));

    setRooms(prev => {
      const copy = [...prev];
      copy[0] = { ...copy[0], items: [...copy[0].items, ...newItems] };
      return copy;
    });

    setShowAnalysis(false);
    setAnalysisResult(null);
    setAnalysisPhotoIdx(null);
  };

  // Add a manually entered item to Room 1
  const addManualItem = (item: any) => {
    const newItem: RoomItem = {
      id: crypto.randomUUID(),
      type: ITEM_TYPES.includes(item.type) ? item.type : 'sofa',
      width: item.width || '',
      height: item.height || '',
      depth: item.depth || '',
      quantity: 1,
      notes: item.description || '',
    };
    setRooms(prev => {
      const copy = [...prev];
      copy[0] = { ...copy[0], items: [...copy[0].items, newItem] };
      return copy;
    });
  };

  const canAdvance = () => {
    if (step === 1) return customer.name.trim().length > 0;
    if (step === 2) return true; // photos optional
    if (step === 3) return rooms.some(r => r.items.length > 0);
    return true;
  };

  // -- Photo handling --
  const handleFiles = useCallback((files: FileList | File[]) => {
    const newPhotos: PhotoFile[] = Array.from(files)
      .filter(f => f.type.startsWith('image/'))
      .map(f => ({ file: f, preview: URL.createObjectURL(f) }));
    setPhotos(prev => [...prev, ...newPhotos]);
  }, []);

  const removePhoto = (idx: number) => {
    setPhotos(prev => {
      const copy = [...prev];
      if (!copy[idx].fromIntake && copy[idx].file) {
        URL.revokeObjectURL(copy[idx].preview);
      }
      copy.splice(idx, 1);
      return copy;
    });
  };

  const uploadPhoto = async (photo: PhotoFile): Promise<string | null> => {
    if (photo.uploadedFilename) return photo.uploadedFilename;
    if (photo.fromIntake && photo.serverUrl) return photo.originalName || photo.serverUrl;
    if (!photo.file) return null;
    const form = new FormData();
    form.append('file', photo.file);
    try {
      const res = await fetch(API + '/files/upload', { method: 'POST', body: form });
      if (res.ok) {
        const data = await res.json();
        return data.filename || data.file_id || null;
      }
    } catch { /* */ }
    return null;
  };

  // -- Room / Item management --
  const addRoom = () => {
    setRooms(prev => [...prev, { id: crypto.randomUUID(), name: `Room ${prev.length + 1}`, items: [] }]);
  };

  const removeRoom = (roomId: string) => {
    setRooms(prev => prev.filter(r => r.id !== roomId));
  };

  const updateRoomName = (roomId: string, name: string) => {
    setRooms(prev => prev.map(r => r.id === roomId ? { ...r, name } : r));
  };

  const addItem = (roomId: string) => {
    setRooms(prev => prev.map(r => r.id === roomId ? {
      ...r, items: [...r.items, {
        id: crypto.randomUUID(), type: 'sofa', width: '', height: '', depth: '', quantity: 1, notes: '',
      }]
    } : r));
  };

  const removeItem = (roomId: string, itemId: string) => {
    setRooms(prev => prev.map(r => r.id === roomId ? { ...r, items: r.items.filter(it => it.id !== itemId) } : r));
  };

  const updateItem = (roomId: string, itemId: string, field: keyof RoomItem, value: any) => {
    setRooms(prev => prev.map(r => r.id === roomId ? {
      ...r, items: r.items.map(it => it.id === itemId ? { ...it, [field]: value } : it)
    } : r));
  };

  // -- Submit --
  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      // Upload photos first
      const uploadedFilenames: string[] = [];
      for (const photo of photos) {
        const fn = await uploadPhoto(photo);
        if (fn) uploadedFilenames.push(fn);
      }

      const payload = {
        customer_name: customer.name,
        customer_email: customer.email,
        customer_phone: customer.phone,
        customer_address: customer.address,
        photos: uploadedFilenames,
        rooms: rooms.filter(r => r.items.length > 0).map(r => ({
          name: r.name,
          items: r.items.map(it => ({
            type: it.type,
            dimensions: { width: it.width, height: it.height, depth: it.depth },
            quantity: it.quantity,
            notes: it.notes,
          })),
        })),
        options: {
          fabric_grade: options.fabricGrade,
          lining_type: options.liningType,
          features: {
            tufting: options.tufting,
            welting: options.welting,
            nailhead: options.nailhead,
            skirt: options.skirt,
            contrast_piping: options.contrastPiping,
            pattern_match: options.patternMatch,
          },
          rush_order: options.rushOrder,
          delivery: options.delivery,
        },
      };

      // Try analyze-photo endpoint if we have photos, otherwise create quote
      let res: Response;
      if (uploadedFilenames.length > 0) {
        res = await fetch(API + '/quotes/analyze-photo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch(API + '/quotes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (res.ok) {
        const data = await res.json();
        setResult(data);
      } else {
        const errData = await res.json().catch(() => null);
        setError(errData?.detail || `Server error ${res.status}`);
      }
    } catch (e: any) {
      setError(e.message || 'Network error');
    }
    setSubmitting(false);
  };

  const totalItems = rooms.reduce((s, r) => s + r.items.reduce((s2, it) => s2 + it.quantity, 0), 0);

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={onBack}
          className="flex items-center gap-1.5 cursor-pointer transition-colors hover:text-[#b8960c]"
          style={{ background: 'none', border: 'none', fontSize: 13, fontWeight: 600, color: '#777', padding: 0 }}>
          <ArrowLeft size={16} /> Back
        </button>
        <div className="flex-1" />
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <FileText size={18} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Quote Builder</h1>
            <p style={{ fontSize: 11, color: '#999', margin: 0 }}>Create a new workroom quote</p>
          </div>
        </div>
        <div className="flex-1" />
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-center gap-1 mb-8">
        {STEPS.map((s, i) => {
          const Icon = s.icon;
          const isActive = step === s.id;
          const isDone = step > s.id;
          return (
            <div key={s.id} className="flex items-center gap-1">
              <button
                onClick={() => { if (isDone || isActive) setStep(s.id); }}
                className="flex items-center gap-1.5 cursor-pointer transition-all"
                style={{
                  padding: '8px 14px', borderRadius: 10, border: 'none', fontSize: 12, fontWeight: 600,
                  background: isActive ? '#fdf8eb' : isDone ? '#f0fdf4' : '#f5f3ef',
                  color: isActive ? '#b8960c' : isDone ? '#16a34a' : '#aaa',
                  outline: isActive ? '2px solid #b8960c' : 'none',
                }}>
                {isDone ? <Check size={14} /> : <Icon size={14} />}
                <span className="hidden sm:inline">{s.label}</span>
              </button>
              {i < STEPS.length - 1 && (
                <div style={{ width: 20, height: 2, background: isDone ? '#bbf7d0' : '#ece8e0', borderRadius: 1 }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <div className="empire-card" style={{ padding: 28, minHeight: 340 }}>
        {step === 1 && <StepCustomer customer={customer} setCustomer={setCustomer} />}
        {step === 2 && (
          <>
            <StepPhotos
              photos={photos} onAdd={handleFiles} onRemove={removePhoto} fileInputRef={fileInputRef}
              intakeProjects={intakeProjects} loadingIntake={loadingIntake}
              selectedIntakeId={selectedIntakeId} onLoadIntake={loadIntakeProject}
              onAnalyze={analyzePhoto} analyzingPhoto={analyzingPhoto}
              onManualItem={addManualItem}
            />
            {showAnalysis && (
              <AnalysisModal
                photo={analysisPhotoIdx !== null ? photos[analysisPhotoIdx] : null}
                items={analysisResult}
                analyzing={analyzingPhoto !== null}
                onToggleItem={(idx) => {
                  if (!analysisResult) return;
                  const copy = [...analysisResult];
                  copy[idx] = { ...copy[idx], checked: !copy[idx].checked };
                  setAnalysisResult(copy);
                }}
                onAddItems={addAnalyzedItems}
                onClose={() => { setShowAnalysis(false); setAnalysisResult(null); setAnalysisPhotoIdx(null); }}
              />
            )}
          </>
        )}
        {step === 3 && (
          <StepRooms
            rooms={rooms} addRoom={addRoom} removeRoom={removeRoom} updateRoomName={updateRoomName}
            addItem={addItem} removeItem={removeItem} updateItem={updateItem}
          />
        )}
        {step === 4 && <StepOptions options={options} setOptions={setOptions} />}
        {step === 5 && !result && (
          <StepReview customer={customer} photos={photos} rooms={rooms} options={options} totalItems={totalItems} />
        )}
        {step === 5 && result && <ResultView result={result} />}
        {error && <div style={{ marginTop: 16, padding: '12px 16px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 13 }}>{error}</div>}
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between mt-5">
        <button onClick={() => setStep(s => Math.max(1, s - 1))} disabled={step === 1}
          className="flex items-center gap-1.5 cursor-pointer disabled:opacity-30 transition-all hover:text-[#b8960c]"
          style={{ height: 40, padding: '0 18px', borderRadius: 10, border: '1.5px solid #ece8e0', background: '#faf9f7', fontSize: 13, fontWeight: 600, color: '#555' }}>
          <ArrowLeft size={16} /> Previous
        </button>
        <div style={{ fontSize: 12, color: '#aaa' }}>Step {step} of 5</div>
        {step < 5 ? (
          <button onClick={() => setStep(s => Math.min(5, s + 1))} disabled={!canAdvance()}
            className="flex items-center gap-1.5 cursor-pointer disabled:opacity-40 transition-all hover:bg-[#a08509]"
            style={{ height: 40, padding: '0 18px', borderRadius: 10, border: 'none', background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700 }}>
            Next <ArrowRight size={16} />
          </button>
        ) : !result ? (
          <button onClick={handleSubmit} disabled={submitting}
            className="flex items-center gap-1.5 cursor-pointer disabled:opacity-60 transition-all hover:bg-[#a08509]"
            style={{ height: 44, padding: '0 24px', borderRadius: 12, border: 'none', background: '#b8960c', color: '#fff', fontSize: 14, fontWeight: 700, boxShadow: '0 2px 10px rgba(184,150,12,0.3)' }}>
            {submitting ? <><Loader2 size={18} className="animate-spin" /> Generating...</> : <><FileText size={18} /> Generate Quote</>}
          </button>
        ) : (
          <button onClick={onBack}
            className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#15803d]"
            style={{ height: 40, padding: '0 18px', borderRadius: 10, border: 'none', background: '#16a34a', color: '#fff', fontSize: 13, fontWeight: 700 }}>
            <Check size={16} /> Done
          </button>
        )}
      </div>
    </div>
  );
}

// ============ Step Components ============

function StepCustomer({ customer, setCustomer }: { customer: CustomerInfo; setCustomer: (c: CustomerInfo) => void }) {
  const update = (field: keyof CustomerInfo, value: string) => setCustomer({ ...customer, [field]: value });
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [allCustomers, setAllCustomers] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API}/crm/customers`).then(r => r.json())
      .then(data => setAllCustomers(data.customers || data || []))
      .catch(() => {});
  }, []);

  const handleNameChange = (value: string) => {
    update('name', value);
    setSelectedId(null);
    if (value.length >= 2 && allCustomers.length > 0) {
      const q = value.toLowerCase();
      const matches = allCustomers.filter((c: any) => c.name?.toLowerCase().includes(q)).slice(0, 6);
      setSuggestions(matches);
      setShowSuggestions(matches.length > 0);
    } else {
      setShowSuggestions(false);
    }
  };

  const selectCustomer = (c: any) => {
    setCustomer({ name: c.name || '', email: c.email || '', phone: c.phone || '', address: c.address || '' });
    setSelectedId(c.id);
    setShowSuggestions(false);
  };

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
        Customer Information
      </div>
      {selectedId && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, padding: '8px 12px', background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0' }}>
          <Check size={14} className="text-green-600" />
          <span style={{ fontSize: 12, color: '#15803d', fontWeight: 500 }}>Loaded from CRM</span>
          <button onClick={() => { setSelectedId(null); setCustomer({ name: '', email: '', phone: '', address: '' }); }} style={{ marginLeft: 'auto', fontSize: 11, color: '#999', cursor: 'pointer', background: 'none', border: 'none' }}>Clear</button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div style={{ position: 'relative' }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Full Name *</label>
          <div style={{ position: 'relative' }}>
            <input ref={nameRef} value={customer.name} onChange={e => handleNameChange(e.target.value)}
              onFocus={() => { if (suggestions.length > 0 && !selectedId) setShowSuggestions(true); }}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder="Start typing to search CRM..."
              className="form-input" style={{ width: '100%', paddingRight: 30 }} />
            <Search size={14} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: '#ccc', pointerEvents: 'none' }} />
          </div>
          {showSuggestions && (
            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50, background: '#fff', border: '1px solid #e5e0d8', borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', marginTop: 4, maxHeight: 220, overflowY: 'auto' }}>
              {suggestions.map(c => (
                <div key={c.id} onMouseDown={() => selectCustomer(c)}
                  style={{ padding: '10px 14px', cursor: 'pointer', borderBottom: '1px solid #f5f3ef', display: 'flex', alignItems: 'center', gap: 10 }}
                  className="hover:bg-[#fdf8eb]">
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#f5f0e6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#b8960c', flexShrink: 0 }}>
                    {(c.name || '?')[0].toUpperCase()}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{c.name}</div>
                    <div style={{ fontSize: 11, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {[c.email, c.phone, c.company].filter(Boolean).join(' · ') || 'No contact info'}
                    </div>
                  </div>
                  {c.total_revenue > 0 && (
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#b8960c' }}>${c.total_revenue.toLocaleString()}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Email</label>
          <input value={customer.email} onChange={e => update('email', e.target.value)} placeholder="jane@example.com" type="email"
            className="form-input" style={{ width: '100%' }} />
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Phone</label>
          <input value={customer.phone} onChange={e => update('phone', e.target.value)} placeholder="(555) 123-4567"
            className="form-input" style={{ width: '100%' }} />
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#555', display: 'block', marginBottom: 4 }}>Address</label>
          <input value={customer.address} onChange={e => update('address', e.target.value)} placeholder="123 Main St, City, ST"
            className="form-input" style={{ width: '100%' }} />
        </div>
      </div>
    </div>
  );
}

function StepPhotos({ photos, onAdd, onRemove, fileInputRef, intakeProjects, loadingIntake, selectedIntakeId, onLoadIntake, onAnalyze, analyzingPhoto, onManualItem }: {
  photos: PhotoFile[]; onAdd: (files: FileList | File[]) => void; onRemove: (i: number) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  intakeProjects: any[]; loadingIntake: boolean; selectedIntakeId: string | null;
  onLoadIntake: (project: any) => void; onAnalyze: (idx: number) => void; analyzingPhoto: number | null;
  onManualItem: (item: any) => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const [inputMethod, setInputMethod] = useState<QuoteInputMethod>('photos');

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) onAdd(e.dataTransfer.files);
  };

  const methodTabs: { key: QuoteInputMethod; label: string; icon: React.ReactNode; color: string }[] = [
    { key: 'photos', label: 'Upload Photos', icon: <Camera size={15} />, color: '#2563eb' },
    { key: '3dscan', label: '3D Scan', icon: <Box size={15} />, color: '#16a34a' },
    { key: 'manual', label: 'Manual Entry', icon: <Edit3 size={15} />, color: '#b8960c' },
    { key: 'intake', label: 'Load from Intake', icon: <FolderOpen size={15} />, color: '#7c3aed' },
  ];

  return (
    <div>
      {/* Input method selector */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 20, flexWrap: 'wrap' }}>
        {methodTabs.map(tab => {
          const active = inputMethod === tab.key;
          return (
            <button key={tab.key} onClick={() => setInputMethod(tab.key)}
              className="flex items-center gap-2 cursor-pointer transition-all"
              style={{
                padding: '10px 16px', borderRadius: 10, fontSize: 12, fontWeight: 600,
                border: `2px solid ${active ? tab.color : '#ece8e0'}`,
                background: active ? `${tab.color}10` : '#faf9f7',
                color: active ? tab.color : '#777',
                minHeight: 44,
              }}>
              {tab.icon} {tab.label}
              {tab.key === 'intake' && selectedIntakeId && (
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#16a34a', display: 'inline-block', marginLeft: 4 }} />
              )}
            </button>
          );
        })}
      </div>

      {/* ── Upload Photos ── */}
      {inputMethod === 'photos' && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            Photo Gallery
          </div>

          {photos.length > 0 && (
            <div className="flex gap-3 flex-wrap mb-4">
              {photos.map((p, i) => (
                <div key={i} style={{ position: 'relative', width: 120, height: 140, borderRadius: 12, overflow: 'hidden', border: '2px solid #ece8e0', background: '#f5f3ef' }}>
                  <img src={p.preview} alt="" style={{ width: '100%', height: 100, objectFit: 'cover' }} />
                  {p.fromIntake && (
                    <div style={{ position: 'absolute', top: 4, left: 4, fontSize: 8, fontWeight: 700, color: '#fff', background: '#b8960c', padding: '2px 5px', borderRadius: 4 }}>
                      INTAKE
                    </div>
                  )}
                  <button onClick={(e) => { e.stopPropagation(); onRemove(i); }}
                    className="cursor-pointer transition-all hover:bg-[#dc2626]"
                    style={{
                      position: 'absolute', top: 4, right: 4, width: 22, height: 22, borderRadius: 6,
                      background: 'rgba(0,0,0,0.5)', color: '#fff', border: 'none', display: 'flex',
                      alignItems: 'center', justifyContent: 'center',
                    }}>
                    <X size={12} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); onAnalyze(i); }}
                    disabled={analyzingPhoto === i}
                    className="cursor-pointer transition-all hover:bg-[#fdf8eb]"
                    style={{
                      width: '100%', height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                      background: '#faf9f7', border: 'none', borderTop: '1px solid #ece8e0',
                      fontSize: 10, fontWeight: 600, color: analyzingPhoto === i ? '#b8960c' : '#777',
                    }}>
                    {analyzingPhoto === i
                      ? <><Loader2 size={11} className="animate-spin" /> Analyzing...</>
                      : <><Sparkles size={11} /> Analyze</>}
                  </button>
                </div>
              ))}
            </div>
          )}

          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className="cursor-pointer transition-all"
            style={{
              border: `2px dashed ${dragOver ? '#b8960c' : '#ddd'}`,
              borderRadius: 14,
              padding: photos.length > 0 ? '20px 24px' : '36px 24px',
              textAlign: 'center',
              background: dragOver ? '#fdf8eb' : '#faf9f7',
            }}>
            <Upload size={photos.length > 0 ? 22 : 32} className="mx-auto mb-2" style={{ color: dragOver ? '#b8960c' : '#ccc' }} />
            <div style={{ fontSize: 13, fontWeight: 600, color: '#555' }}>
              {photos.length > 0 ? 'Add more photos' : 'Drop photos here or click to browse'}
            </div>
            <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>JPG, PNG, HEIC accepted</div>
            <input ref={fileInputRef} type="file" accept="image/*" multiple hidden
              onChange={e => { if (e.target.files?.length) onAdd(e.target.files); e.target.value = ''; }} />
          </div>
        </div>
      )}

      {/* ── 3D Scan ── */}
      {inputMethod === '3dscan' && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            3D Scan Upload
          </div>
          <div style={{
            border: '2px dashed #bbf7d0', borderRadius: 14, padding: '40px 24px', textAlign: 'center',
            background: '#f0fdf4',
          }}>
            <Box size={36} className="mx-auto mb-3" style={{ color: '#16a34a' }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: '#333', marginBottom: 4 }}>
              Upload a 3D Scan
            </div>
            <div style={{ fontSize: 12, color: '#777', marginBottom: 16 }}>
              Supports GLB, GLTF, OBJ, PLY, USDZ from Polycam, LiDAR, or RealityScan
            </div>
            <button
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.glb,.gltf,.obj,.ply,.usdz';
                input.onchange = (e: any) => {
                  const file = e.target?.files?.[0];
                  if (file) {
                    onManualItem({
                      type: '3d_scan',
                      description: `3D Scan: ${file.name}`,
                      measurements: {},
                      _file: file,
                    });
                  }
                };
                input.click();
              }}
              className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110 mx-auto"
              style={{ padding: '12px 24px', borderRadius: 10, background: '#16a34a', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <Upload size={16} /> Choose 3D File
            </button>
            <div style={{ fontSize: 11, color: '#aaa', marginTop: 12 }}>
              Scan rooms with your phone&apos;s LiDAR sensor, then upload the exported model
            </div>
          </div>
        </div>
      )}

      {/* ── Manual Entry ── */}
      {inputMethod === 'manual' && (
        <QuoteManualEntry onAddItem={onManualItem} />
      )}

      {/* ── Load from Intake ── */}
      {inputMethod === 'intake' && (
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
            Load from Intake Submission
          </div>
          {selectedIntakeId && (
            <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#f0fdf4', border: '1px solid #bbf7d0', fontSize: 12, fontWeight: 600, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Check size={14} /> Intake loaded — photos added to gallery
            </div>
          )}
          <div style={{ border: '1.5px solid #ece8e0', borderRadius: 12, background: '#faf9f7', overflow: 'hidden' }}>
            {loadingIntake ? (
              <div style={{ padding: '20px', textAlign: 'center' }}>
                <Loader2 size={18} className="animate-spin mx-auto" style={{ color: '#b8960c' }} />
                <div style={{ fontSize: 11, color: '#999', marginTop: 6 }}>Loading intake projects...</div>
              </div>
            ) : intakeProjects.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', fontSize: 12, color: '#bbb' }}>
                <ImageIcon size={20} className="mx-auto mb-2" style={{ color: '#ddd' }} />
                No intake projects with photos found
              </div>
            ) : (
              <div style={{ maxHeight: 280, overflowY: 'auto' }}>
                {intakeProjects.map((proj: any) => {
                  const isSelected = selectedIntakeId === proj.id;
                  return (
                    <div
                      key={proj.id}
                      onClick={() => onLoadIntake(proj)}
                      className="cursor-pointer transition-all hover:bg-[#fdf8eb]"
                      style={{
                        padding: '10px 14px',
                        borderBottom: '1px solid #f0ede8',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        background: isSelected ? '#fdf8eb' : 'transparent',
                      }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 8, background: isSelected ? '#b8960c' : '#f5f0e6',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                      }}>
                        {isSelected
                          ? <Check size={14} style={{ color: '#fff' }} />
                          : <Camera size={14} style={{ color: '#b8960c' }} />}
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>
                          {proj.customer_name || 'Unknown Customer'}
                        </div>
                        <div style={{ fontSize: 11, color: '#999', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {[proj.intake_code, proj.project_type].filter(Boolean).join(' · ')}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#b8960c' }}>
                          {(proj.photos || []).length} photo{(proj.photos || []).length !== 1 ? 's' : ''}
                        </div>
                        {proj.created_at && (
                          <div style={{ fontSize: 10, color: '#bbb' }}>
                            {new Date(proj.created_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function QuoteManualEntry({ onAddItem }: { onAddItem: (item: any) => void }) {
  const [itemType, setItemType] = useState<ManualItemType>('window');
  const [m, setM] = useState({ width_inches: 0, height_inches: 0, depth_inches: 0, sill_depth: 0, stack_space: 0 });
  const [opts, setOpts] = useState({ mount_type: 'inside', treatment: '', lining: '', notes: '' });
  const [addedCount, setAddedCount] = useState(0);
  const [showCushionBuilder, setShowCushionBuilder] = useState(false);

  const isWindow = ['window', 'cornice', 'valance', 'roman_shade'].includes(itemType);
  const isFurniture = ['sofa', 'chair'].includes(itemType);
  const isCushion = ['cushion', 'pillow'].includes(itemType);

  const updateM = (key: string, val: string) => {
    setM(prev => ({ ...prev, [key]: parseFloat(val) || 0 }));
  };

  const currentItem = {
    type: itemType,
    subtype: opts.treatment || undefined,
    measurements: { width_inches: m.width_inches, height_inches: m.height_inches, depth_inches: m.depth_inches || undefined },
    treatment: opts.treatment || itemType,
    mount_type: opts.mount_type || undefined,
    lining: opts.lining || undefined,
    description: opts.notes || undefined,
  };

  const addItem = () => {
    if (!m.width_inches && !m.height_inches) return;
    onAddItem({
      type: ITEM_TYPES.includes(itemType) ? itemType : 'sofa',
      width: m.width_inches ? `${m.width_inches}"` : '',
      height: m.height_inches ? `${m.height_inches}"` : '',
      depth: m.depth_inches ? `${m.depth_inches}"` : '',
      description: [
        MANUAL_ITEM_TYPES.find(t => t.key === itemType)?.label || itemType,
        opts.treatment ? opts.treatment.replace(/_/g, ' ') : '',
        opts.mount_type === 'outside' ? 'outside mount' : '',
        opts.lining ? `${opts.lining} lining` : '',
        opts.notes,
      ].filter(Boolean).join(' · '),
    });
    setAddedCount(c => c + 1);
    setM({ width_inches: 0, height_inches: 0, depth_inches: 0, sill_depth: 0, stack_space: 0 });
    setOpts({ mount_type: 'inside', treatment: '', lining: '', notes: '' });
  };

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>
        Manual Measurement Entry
      </div>

      {addedCount > 0 && (
        <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#f0fdf4', border: '1px solid #bbf7d0', fontSize: 12, fontWeight: 600, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6 }}>
          <CheckCircle size={14} /> {addedCount} item{addedCount !== 1 ? 's' : ''} added to Room 1
        </div>
      )}

      {/* Item type selector */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 8 }}>
          What are you measuring?
        </label>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {MANUAL_ITEM_TYPES.map(t => (
            <button key={t.key} onClick={() => setItemType(t.key)}
              className="cursor-pointer transition-all"
              style={{
                padding: '8px 14px', borderRadius: 10, fontSize: 12, fontWeight: 600,
                border: `1.5px solid ${itemType === t.key ? '#b8960c' : '#ece8e0'}`,
                background: itemType === t.key ? '#fdf8e8' : '#faf9f7',
                color: itemType === t.key ? '#b8960c' : '#777',
                minHeight: 44,
              }}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cushion Builder (full wizard) */}
      {isCushion && (
        <div style={{ marginBottom: 16 }}>
          <button
            onClick={() => setShowCushionBuilder(!showCushionBuilder)}
            className="w-full flex items-center justify-center gap-2 cursor-pointer font-bold transition-all hover:brightness-110"
            style={{
              height: 44, fontSize: 12, borderRadius: 10, marginBottom: showCushionBuilder ? 12 : 0,
              background: showCushionBuilder ? '#7c3aed' : 'linear-gradient(135deg, #7c3aed, #a855f7)',
              color: '#fff', border: 'none', boxShadow: '0 2px 8px #7c3aed30',
            }}>
            <Box size={14} /> {showCushionBuilder ? 'Hide Cushion Builder' : 'Open Cushion Builder (Detailed Specs)'}
          </button>
          {showCushionBuilder && (
            <div style={{ border: '1.5px solid #e9d5ff', borderRadius: 12, padding: 16, background: '#faf5ff' }}>
              <CushionBuilder
                onAddToQuote={(data: any) => {
                  onAddItem({
                    type: 'cushion',
                    width: data.dimensions?.width ? `${data.dimensions.width}"` : '',
                    height: data.dimensions?.height ? `${data.dimensions.height}"` : '',
                    depth: data.dimensions?.depth ? `${data.dimensions.depth}"` : '',
                    description: `${data.cushionType || 'Cushion'} — ${data.shape || ''} ${data.fill || ''} ${data.edge || ''}`.trim(),
                    quantity: data.quantity || 1,
                    cushionData: data,
                  });
                  setAddedCount(c => c + 1);
                  setShowCushionBuilder(false);
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* Quick entry heading for cushions */}
      {isCushion && !showCushionBuilder && (
        <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
          Or enter dimensions manually
        </div>
      )}

      {/* Form + live diagram side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Width (in)</span>
              <input type="number" value={m.width_inches || ''} onChange={e => updateM('width_inches', e.target.value)}
                placeholder="e.g. 72" style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Height (in)</span>
              <input type="number" value={m.height_inches || ''} onChange={e => updateM('height_inches', e.target.value)}
                placeholder="e.g. 96" style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
          </div>

          {(isFurniture || isCushion) && (
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Depth (in)</span>
              <input type="number" value={m.depth_inches || ''} onChange={e => updateM('depth_inches', e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
          )}

          {isWindow && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Mount Type</span>
                  <select value={opts.mount_type} onChange={e => setOpts(p => ({...p, mount_type: e.target.value}))}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                    <option value="inside">Inside Mount</option>
                    <option value="outside">Outside Mount</option>
                  </select>
                </label>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Treatment</span>
                  <select value={opts.treatment} onChange={e => setOpts(p => ({...p, treatment: e.target.value}))}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                    <option value="">--</option>
                    <option value="pinch_pleat">Pinch Pleat</option>
                    <option value="rod_pocket">Rod Pocket</option>
                    <option value="grommet">Grommet</option>
                    <option value="tab_top">Tab Top</option>
                    <option value="ripplefold">Ripplefold</option>
                    <option value="goblet">Goblet</option>
                  </select>
                </label>
              </div>
              <label style={{ fontSize: 12 }}>
                <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Lining</span>
                <select value={opts.lining} onChange={e => setOpts(p => ({...p, lining: e.target.value}))}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                  <option value="">None</option>
                  <option value="standard">Standard</option>
                  <option value="blackout">Blackout</option>
                  <option value="thermal">Thermal</option>
                </select>
              </label>
            </>
          )}

          <label style={{ fontSize: 12 }}>
            <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Notes</span>
            <input value={opts.notes} onChange={e => setOpts(p => ({...p, notes: e.target.value}))}
              placeholder="Additional notes..."
              style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
          </label>

          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button onClick={addItem}
              disabled={!m.width_inches && !m.height_inches}
              className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110 disabled:opacity-50"
              style={{ flex: 1, padding: '12px 20px', borderRadius: 10, background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <CheckCircle size={16} /> Add to Room 1
            </button>
            <button onClick={() => { setM({width_inches:0,height_inches:0,depth_inches:0,sill_depth:0,stack_space:0}); setOpts({mount_type:'inside',treatment:'',lining:'',notes:''}); }}
              className="cursor-pointer transition-all hover:bg-[#f0ede8]"
              style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 13, fontWeight: 600, color: '#777', minHeight: 48 }}>
              Clear
            </button>
          </div>
        </div>

        {/* Right: live SVG diagram */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          {(m.width_inches > 0 || m.height_inches > 0) ? (
            <>
              <div style={{ border: '1px solid #ece8e0', borderRadius: 12, overflow: 'hidden', background: '#fff', padding: 8, width: '100%' }}>
                <MeasurementDiagram item={currentItem as any} width={380} height={300} />
              </div>
              <span style={{ fontSize: 11, color: '#888' }}>Live preview — updates as you type</span>
            </>
          ) : (
            <div style={{ width: '100%', height: 300, borderRadius: 12, border: '2px dashed #ece8e0', background: '#faf9f7', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <Ruler size={32} style={{ color: '#ddd' }} />
              <span style={{ fontSize: 13, color: '#aaa', fontWeight: 500 }}>Enter measurements to see diagram</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function AnalysisModal({ photo, items, analyzing, onToggleItem, onAddItems, onClose }: {
  photo: PhotoFile | null; items: AnalysisItem[] | null; analyzing: boolean;
  onToggleItem: (idx: number) => void; onAddItems: () => void; onClose: () => void;
}) {
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 24,
    }} onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 16, width: '100%', maxWidth: 600,
          maxHeight: '80vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
          boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
        }}>
        {/* Header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #ece8e0', display: 'flex', alignItems: 'center', gap: 10 }}>
          <Sparkles size={16} style={{ color: '#b8960c' }} />
          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', flex: 1 }}>AI Photo Analysis</span>
          <button onClick={onClose} className="cursor-pointer" style={{ background: 'none', border: 'none', color: '#999', display: 'flex' }}>
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {/* Photo preview */}
          {photo && (
            <div style={{ marginBottom: 16, borderRadius: 10, overflow: 'hidden', border: '1.5px solid #ece8e0', maxHeight: 200 }}>
              <img src={photo.preview} alt="" style={{ width: '100%', maxHeight: 200, objectFit: 'contain', background: '#f5f3ef' }} />
            </div>
          )}

          {analyzing ? (
            <div style={{ textAlign: 'center', padding: '30px 0' }}>
              <Loader2 size={28} className="animate-spin mx-auto" style={{ color: '#b8960c' }} />
              <div style={{ fontSize: 13, fontWeight: 600, color: '#555', marginTop: 10 }}>Analyzing photo...</div>
              <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>Detecting furniture items and dimensions</div>
            </div>
          ) : items && items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '24px 0', color: '#999', fontSize: 13 }}>
              No items detected in this photo. Try another photo or add items manually.
            </div>
          ) : items && items.length > 0 ? (
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#555', marginBottom: 10 }}>
                Detected Items ({items.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {items.map((item, idx) => (
                  <div
                    key={idx}
                    onClick={() => onToggleItem(idx)}
                    className="cursor-pointer transition-all"
                    style={{
                      padding: '10px 14px', borderRadius: 10,
                      border: `1.5px solid ${item.checked ? '#b8960c' : '#ece8e0'}`,
                      background: item.checked ? '#fdf8eb' : '#faf9f7',
                      display: 'flex', alignItems: 'center', gap: 10,
                    }}>
                    <div style={{
                      width: 20, height: 20, borderRadius: 5, flexShrink: 0,
                      border: `2px solid ${item.checked ? '#b8960c' : '#ddd'}`,
                      background: item.checked ? '#b8960c' : '#fff',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      {item.checked && <Check size={12} style={{ color: '#fff' }} />}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>
                        {item.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </div>
                      <div style={{ fontSize: 11, color: '#777' }}>
                        {[
                          item.description,
                          item.condition && `Condition: ${item.condition}`,
                          (item.width || item.height || item.depth) && `${[item.width, item.height, item.depth].filter(Boolean).join(' x ')}`,
                        ].filter(Boolean).join(' · ')}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        {items && items.length > 0 && (
          <div style={{ padding: '14px 20px', borderTop: '1px solid #ece8e0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 11, color: '#999' }}>
              {items.filter(it => it.checked).length} of {items.length} selected
            </span>
            <button
              onClick={onAddItems}
              disabled={items.filter(it => it.checked).length === 0}
              className="flex items-center gap-1.5 cursor-pointer disabled:opacity-40 transition-all hover:bg-[#a08509]"
              style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: '#b8960c', color: '#fff', fontSize: 12, fontWeight: 700 }}>
              <Plus size={14} /> Add to Quote
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function StepRooms({ rooms, addRoom, removeRoom, updateRoomName, addItem, removeItem, updateItem }: {
  rooms: Room[]; addRoom: () => void; removeRoom: (id: string) => void; updateRoomName: (id: string, name: string) => void;
  addItem: (roomId: string) => void; removeItem: (roomId: string, itemId: string) => void;
  updateItem: (roomId: string, itemId: string, field: keyof RoomItem, value: any) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Rooms & Items
        </div>
        <button onClick={addRoom}
          className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#fdf8eb] hover:border-[#b8960c]"
          style={{ padding: '6px 12px', borderRadius: 8, border: '1.5px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#555' }}>
          <Plus size={13} /> Add Room
        </button>
      </div>

      <div className="flex flex-col gap-5">
        {rooms.map(room => (
          <div key={room.id} style={{ border: '1.5px solid #ece8e0', borderRadius: 14, overflow: 'hidden' }}>
            {/* Room header */}
            <div className="flex items-center gap-3" style={{ padding: '12px 16px', background: '#f5f3ef', borderBottom: '1px solid #ece8e0' }}>
              <GripVertical size={14} className="text-[#ccc]" />
              <input value={room.name} onChange={e => updateRoomName(room.id, e.target.value)}
                style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', fontSize: 14, fontWeight: 600, color: '#1a1a1a' }} />
              <button onClick={() => addItem(room.id)}
                className="flex items-center gap-1 cursor-pointer transition-all hover:bg-[#fdf8eb]"
                style={{ padding: '5px 10px', borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', fontSize: 10, fontWeight: 600, color: '#b8960c' }}>
                <Plus size={12} /> Item
              </button>
              {rooms.length > 1 && (
                <button onClick={() => removeRoom(room.id)}
                  className="cursor-pointer transition-all hover:bg-[#fef2f2] hover:text-[#dc2626]"
                  style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', color: '#ccc', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Trash2 size={13} />
                </button>
              )}
            </div>

            {/* Items */}
            <div style={{ padding: room.items.length ? '12px 16px' : '0' }}>
              {room.items.length === 0 && (
                <div style={{ padding: '20px 16px', textAlign: 'center', fontSize: 12, color: '#bbb' }}>
                  No items yet — click "+ Item" to add
                </div>
              )}
              {room.items.map((item, idx) => (
                <div key={item.id} className="flex items-start gap-2" style={{ marginBottom: idx < room.items.length - 1 ? 10 : 0, paddingBottom: idx < room.items.length - 1 ? 10 : 0, borderBottom: idx < room.items.length - 1 ? '1px solid #f0ede8' : 'none' }}>
                  <div className="flex-1 grid grid-cols-6 gap-2">
                    {/* Type */}
                    <div className="col-span-2">
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>TYPE</label>
                      <select value={item.type} onChange={e => updateItem(room.id, item.id, 'type', e.target.value)}
                        className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }}>
                        {ITEM_TYPES.map(t => (
                          <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                        ))}
                      </select>
                    </div>
                    {/* W */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>W</label>
                      <input value={item.width} onChange={e => updateItem(room.id, item.id, 'width', e.target.value)}
                        placeholder='48"' className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* H */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>H</label>
                      <input value={item.height} onChange={e => updateItem(room.id, item.id, 'height', e.target.value)}
                        placeholder='36"' className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* D */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>D</label>
                      <input value={item.depth} onChange={e => updateItem(room.id, item.id, 'depth', e.target.value)}
                        placeholder='32"' className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* Qty */}
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999', display: 'block', marginBottom: 2 }}>QTY</label>
                      <input type="number" min={1} value={item.quantity}
                        onChange={e => updateItem(room.id, item.id, 'quantity', Math.max(1, parseInt(e.target.value) || 1))}
                        className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                    {/* Notes row */}
                    <div className="col-span-5">
                      <input value={item.notes} onChange={e => updateItem(room.id, item.id, 'notes', e.target.value)}
                        placeholder="Notes (fabric preference, condition, etc.)"
                        className="form-input" style={{ width: '100%', fontSize: 11, padding: '6px 8px' }} />
                    </div>
                  </div>
                  <button onClick={() => removeItem(room.id, item.id)}
                    className="cursor-pointer transition-all hover:bg-[#fef2f2] hover:text-[#dc2626] mt-4"
                    style={{ width: 28, height: 28, borderRadius: 7, border: '1px solid #ece8e0', background: '#fff', color: '#ccc', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <Trash2 size={13} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepOptions({ options, setOptions }: { options: QuoteOptions; setOptions: (o: QuoteOptions) => void }) {
  const toggle = (key: keyof QuoteOptions) => setOptions({ ...options, [key]: !options[key] });

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
        Quote Options
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Fabric Grade */}
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#555', display: 'block', marginBottom: 8 }}>Fabric Grade</label>
          <div className="flex gap-2">
            {(['A', 'B', 'C'] as const).map(g => {
              const isActive = options.fabricGrade === g;
              const labels: Record<string, string> = { A: 'Standard', B: 'Designer', C: 'Premium' };
              const colors: Record<string, string> = { A: '#16a34a', B: '#b8960c', C: '#7c3aed' };
              return (
                <button key={g} onClick={() => setOptions({ ...options, fabricGrade: g })}
                  className="flex-1 cursor-pointer transition-all"
                  style={{
                    padding: '10px 8px', borderRadius: 10, textAlign: 'center', fontSize: 12, fontWeight: 600,
                    border: `2px solid ${isActive ? colors[g] : '#ece8e0'}`,
                    background: isActive ? `${colors[g]}10` : '#faf9f7',
                    color: isActive ? colors[g] : '#777',
                  }}>
                  Grade {g}<br /><span style={{ fontSize: 10, fontWeight: 400 }}>{labels[g]}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Lining Type */}
        <div>
          <label style={{ fontSize: 12, fontWeight: 600, color: '#555', display: 'block', marginBottom: 8 }}>Lining Type</label>
          <select value={options.liningType}
            onChange={e => setOptions({ ...options, liningType: e.target.value as any })}
            className="form-input" style={{ width: '100%', fontSize: 13, padding: '10px 12px' }}>
            <option value="none">No Lining</option>
            <option value="standard">Standard Lining</option>
            <option value="blackout">Blackout Lining</option>
            <option value="interlining">Interlining</option>
            <option value="thermal">Thermal Lining</option>
          </select>
        </div>
      </div>

      {/* Special Features */}
      <div style={{ marginTop: 24 }}>
        <label style={{ fontSize: 12, fontWeight: 600, color: '#555', display: 'block', marginBottom: 10 }}>Special Features</label>
        <div className="grid grid-cols-3 gap-2">
          {([
            { key: 'tufting', label: 'Tufting' },
            { key: 'welting', label: 'Welting / Piping' },
            { key: 'nailhead', label: 'Nailhead Trim' },
            { key: 'skirt', label: 'Skirt / Kick Pleat' },
            { key: 'contrastPiping', label: 'Contrast Piping' },
            { key: 'patternMatch', label: 'Pattern Match' },
          ] as const).map(feat => {
            const isChecked = options[feat.key] as boolean;
            return (
              <button key={feat.key} onClick={() => toggle(feat.key)}
                className="flex items-center gap-2 cursor-pointer transition-all text-left"
                style={{
                  padding: '10px 12px', borderRadius: 10,
                  border: `1.5px solid ${isChecked ? '#b8960c' : '#ece8e0'}`,
                  background: isChecked ? '#fdf8eb' : '#faf9f7',
                  fontSize: 12, fontWeight: isChecked ? 600 : 400,
                  color: isChecked ? '#b8960c' : '#777',
                }}>
                <div style={{
                  width: 18, height: 18, borderRadius: 5, flexShrink: 0,
                  border: `2px solid ${isChecked ? '#b8960c' : '#ddd'}`,
                  background: isChecked ? '#b8960c' : '#fff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {isChecked && <Check size={12} className="text-white" />}
                </div>
                {feat.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Rush / Delivery */}
      <div className="flex gap-3 mt-5">
        <button onClick={() => toggle('rushOrder')}
          className="flex-1 flex items-center gap-2 cursor-pointer transition-all"
          style={{
            padding: '12px 16px', borderRadius: 10,
            border: `1.5px solid ${options.rushOrder ? '#dc2626' : '#ece8e0'}`,
            background: options.rushOrder ? '#fef2f2' : '#faf9f7',
            fontSize: 12, fontWeight: options.rushOrder ? 600 : 400,
            color: options.rushOrder ? '#dc2626' : '#777',
          }}>
          <div style={{
            width: 18, height: 18, borderRadius: 5,
            border: `2px solid ${options.rushOrder ? '#dc2626' : '#ddd'}`,
            background: options.rushOrder ? '#dc2626' : '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {options.rushOrder && <Check size={12} className="text-white" />}
          </div>
          Rush Order (+25%)
        </button>
        <button onClick={() => toggle('delivery')}
          className="flex-1 flex items-center gap-2 cursor-pointer transition-all"
          style={{
            padding: '12px 16px', borderRadius: 10,
            border: `1.5px solid ${options.delivery ? '#2563eb' : '#ece8e0'}`,
            background: options.delivery ? '#eff6ff' : '#faf9f7',
            fontSize: 12, fontWeight: options.delivery ? 600 : 400,
            color: options.delivery ? '#2563eb' : '#777',
          }}>
          <div style={{
            width: 18, height: 18, borderRadius: 5,
            border: `2px solid ${options.delivery ? '#2563eb' : '#ddd'}`,
            background: options.delivery ? '#2563eb' : '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            {options.delivery && <Check size={12} className="text-white" />}
          </div>
          Include Delivery
        </button>
      </div>
    </div>
  );
}

function StepReview({ customer, photos, rooms, options, totalItems }: {
  customer: CustomerInfo; photos: PhotoFile[]; rooms: Room[]; options: QuoteOptions; totalItems: number;
}) {
  const features = [
    options.tufting && 'Tufting',
    options.welting && 'Welting',
    options.nailhead && 'Nailhead',
    options.skirt && 'Skirt',
    options.contrastPiping && 'Contrast Piping',
    options.patternMatch && 'Pattern Match',
  ].filter(Boolean);

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
        Review & Generate
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Customer */}
        <div style={{ padding: '14px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Customer</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>{customer.name}</div>
          {customer.email && <div style={{ fontSize: 11, color: '#777' }}>{customer.email}</div>}
          {customer.phone && <div style={{ fontSize: 11, color: '#777' }}>{customer.phone}</div>}
          {customer.address && <div style={{ fontSize: 11, color: '#777', marginTop: 4 }}>{customer.address}</div>}
        </div>

        {/* Summary */}
        <div style={{ padding: '14px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Summary</div>
          <div className="flex items-center justify-between mb-1">
            <span style={{ fontSize: 12, color: '#555' }}>Rooms</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{rooms.filter(r => r.items.length > 0).length}</span>
          </div>
          <div className="flex items-center justify-between mb-1">
            <span style={{ fontSize: 12, color: '#555' }}>Total Items</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{totalItems}</span>
          </div>
          <div className="flex items-center justify-between mb-1">
            <span style={{ fontSize: 12, color: '#555' }}>Photos</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{photos.length}</span>
          </div>
          <div className="flex items-center justify-between">
            <span style={{ fontSize: 12, color: '#555' }}>Fabric Grade</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>Grade {options.fabricGrade}</span>
          </div>
        </div>
      </div>

      {/* Items detail */}
      <div style={{ marginTop: 16, padding: '14px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Items</div>
        {rooms.filter(r => r.items.length > 0).map(room => (
          <div key={room.id} style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>{room.name}</div>
            {room.items.map(item => (
              <div key={item.id} className="flex items-center justify-between" style={{ padding: '4px 0', fontSize: 12, color: '#555' }}>
                <span>{item.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  {item.width || item.height ? ` (${[item.width, item.height, item.depth].filter(Boolean).join(' x ')})` : ''}
                </span>
                <span style={{ fontWeight: 600 }}>x{item.quantity}</span>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Options */}
      <div className="flex flex-wrap gap-2 mt-4">
        <span style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#fdf8eb', color: '#b8960c', fontWeight: 600, border: '1px solid #f5ecd0' }}>
          {options.liningType === 'none' ? 'No Lining' : `${options.liningType.charAt(0).toUpperCase() + options.liningType.slice(1)} Lining`}
        </span>
        {features.map(f => (
          <span key={f as string} style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#f5f3ef', color: '#555', fontWeight: 600, border: '1px solid #ece8e0' }}>
            {f}
          </span>
        ))}
        {options.rushOrder && (
          <span style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#fef2f2', color: '#dc2626', fontWeight: 600, border: '1px solid #fecaca' }}>
            Rush Order
          </span>
        )}
        {options.delivery && (
          <span style={{ fontSize: 10, padding: '4px 10px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', fontWeight: 600, border: '1px solid #bfdbfe' }}>
            Delivery Included
          </span>
        )}
      </div>

      {/* Photo previews */}
      {photos.length > 0 && (
        <div className="flex gap-2 mt-4">
          {photos.map((p, i) => (
            <div key={i} style={{ width: 64, height: 64, borderRadius: 8, overflow: 'hidden', border: '1.5px solid #ece8e0' }}>
              <img src={p.preview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ResultView({ result }: { result: any }) {
  const [selectedTier, setSelectedTier] = useState(1);
  const proposals = result.design_proposals || result.proposals || result.tiers || [];
  const quoteNumber = result.quote_number || result.id || 'NEW';

  return (
    <div>
      <div className="flex items-center gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg bg-[#f0fdf4] flex items-center justify-center">
          <Check size={18} className="text-[#16a34a]" />
        </div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>Quote Generated</div>
          <div style={{ fontSize: 11, color: '#777' }}>{quoteNumber}</div>
        </div>
      </div>

      {/* 3-tier pricing */}
      {proposals.length > 0 ? (
        <div className="flex gap-3">
          {TIERS.map((t, i) => {
            const p = proposals[i];
            if (!p) return null;
            const total = p.total || p.price || 0;
            const isSelected = selectedTier === i;
            return (
              <div key={t.key} onClick={() => setSelectedTier(i)}
                className="flex-1 cursor-pointer text-center transition-all"
                style={{
                  padding: 20, borderRadius: 14, minHeight: 120,
                  background: isSelected ? t.bg : '#faf9f7',
                  border: `2px solid ${isSelected ? t.color : '#ece8e0'}`,
                  borderLeftWidth: 4, borderLeftColor: t.color,
                  boxShadow: isSelected ? '0 4px 16px rgba(0,0,0,0.08)' : 'none',
                }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#777', letterSpacing: '0.03em' }}>{t.key} · {t.label}</div>
                <div style={{ fontSize: 26, fontWeight: 700, color: t.color, margin: '8px 0' }}>${total.toLocaleString()}</div>
                <div style={{ fontSize: 10, color: '#888' }}>Grade {t.key} fabric · {p.lining_type || 'Standard'} lining</div>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{ padding: '20px 16px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', marginBottom: 4 }}>Quote Created</div>
          {result.total && (
            <div style={{ fontSize: 22, fontWeight: 700, color: '#b8960c' }}>${result.total.toLocaleString()}</div>
          )}
          <div style={{ fontSize: 12, color: '#777', marginTop: 4 }}>
            {result.customer_name && `Customer: ${result.customer_name}`}
          </div>
          <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>
            Quote ID: {result.id || 'N/A'}
          </div>
        </div>
      )}
    </div>
  );
}
