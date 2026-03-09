'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  ArrowLeft, ArrowRight, User, Camera, Layers, Settings, FileText,
  Plus, Trash2, Upload, X, Check, Loader2, ChevronDown, GripVertical, Search
} from 'lucide-react';

interface CustomerInfo {
  name: string;
  email: string;
  phone: string;
  address: string;
}

interface PhotoFile {
  file: File;
  preview: string;
  uploadedFilename?: string;
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

  const fileInputRef = useRef<HTMLInputElement>(null);

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
      URL.revokeObjectURL(copy[idx].preview);
      copy.splice(idx, 1);
      return copy;
    });
  };

  const uploadPhoto = async (photo: PhotoFile): Promise<string | null> => {
    if (photo.uploadedFilename) return photo.uploadedFilename;
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
        {step === 2 && <StepPhotos photos={photos} onAdd={handleFiles} onRemove={removePhoto} fileInputRef={fileInputRef} />}
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

function StepPhotos({ photos, onAdd, onRemove, fileInputRef }: {
  photos: PhotoFile[]; onAdd: (files: FileList | File[]) => void; onRemove: (i: number) => void; fileInputRef: React.RefObject<HTMLInputElement | null>;
}) {
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) onAdd(e.dataTransfer.files);
  };

  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 16 }}>
        Photo Upload
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="cursor-pointer transition-all"
        style={{
          border: `2px dashed ${dragOver ? '#b8960c' : '#ddd'}`,
          borderRadius: 14,
          padding: '36px 24px',
          textAlign: 'center',
          background: dragOver ? '#fdf8eb' : '#faf9f7',
        }}>
        <Upload size={32} className="mx-auto mb-3" style={{ color: dragOver ? '#b8960c' : '#ccc' }} />
        <div style={{ fontSize: 14, fontWeight: 600, color: '#555' }}>Drop photos here or click to browse</div>
        <div style={{ fontSize: 11, color: '#aaa', marginTop: 4 }}>JPG, PNG, HEIC accepted</div>
        <input ref={fileInputRef} type="file" accept="image/*" multiple hidden
          onChange={e => { if (e.target.files?.length) onAdd(e.target.files); e.target.value = ''; }} />
      </div>

      {/* Thumbnails */}
      {photos.length > 0 && (
        <div className="flex gap-3 flex-wrap mt-5">
          {photos.map((p, i) => (
            <div key={i} style={{ position: 'relative', width: 110, height: 110, borderRadius: 12, overflow: 'hidden', border: '2px solid #ece8e0' }}>
              <img src={p.preview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              <button onClick={(e) => { e.stopPropagation(); onRemove(i); }}
                className="cursor-pointer transition-all hover:bg-[#dc2626]"
                style={{
                  position: 'absolute', top: 4, right: 4, width: 22, height: 22, borderRadius: 6,
                  background: 'rgba(0,0,0,0.5)', color: '#fff', border: 'none', display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}
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
