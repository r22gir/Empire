'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Send, Plus, Trash2 } from 'lucide-react';
import IntakeNav from '../../../components/intake/IntakeNav';
import PhotoUploader from '../../../components/intake/PhotoUploader';
import MeasurementInput, { Measurement } from '../../../components/intake/MeasurementInput';
import FabricInfoSection, { FabricInfo } from '../../../components/intake/FabricInfoSection';
import { IntakeFooter, IntakeStepper, journeyFromFormStep } from '../../../components/intake/IntakeChrome';
import { intakeFetch, getToken, intakeAuthHeaders } from '../../../lib/intake-auth';

import { API, API_BASE } from '../../../lib/api';

const steps = ['Project Info', 'Photos, Drawings & Scans', 'Measurements', 'Notes & Submit'];

interface LineItem {
  id: string;
  treatment: string;
  room: string;
  description: string;
  style: string;
  fabric?: FabricInfo;
  showFabric?: boolean;
}

const TREATMENTS = [
  { value: 'drapery', label: 'Drapery' },
  { value: 'blinds', label: 'Blinds' },
  { value: 'shades', label: 'Shades' },
  { value: 'shutters', label: 'Shutters' },
  { value: 'upholstery', label: 'Upholstery' },
  { value: 'bedding', label: 'Bedding' },
  { value: 'other', label: 'Other' },
];

const STYLES = [
  { value: 'modern', label: 'Modern / Minimalist' },
  { value: 'traditional', label: 'Traditional / Classic' },
  { value: 'transitional', label: 'Transitional' },
  { value: 'bohemian', label: 'Bohemian' },
  { value: 'coastal', label: 'Coastal' },
  { value: 'farmhouse', label: 'Farmhouse' },
  { value: 'not-sure', label: 'Not Sure' },
];

const defaultFabric = (room: string, item: string): FabricInfo => ({
  scope: 'item',
  room_name: room,
  item_name: item,
  fabric_preference: 'not_sure',
});

export default function NewProject() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [step, setStep] = useState(0);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [photos, setPhotos] = useState<any[]>([]);
  const [scans, setScans] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [scope, setScope] = useState('');
  const [items, setItems] = useState<LineItem[]>([
    { id: crypto.randomUUID(), treatment: '', room: '', description: '', style: '' },
  ]);
  const [measurements, setMeasurements] = useState<Measurement[]>([
    { room: '', width: '', height: '', reference: 'none' },
  ]);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (!getToken()) { router.push('/intake/login'); return; }
    intakeFetch('/me').then(setUser).catch(() => router.push('/intake/login'));
  }, [router]);

  const addItem = () => {
    setItems(prev => [...prev, { id: crypto.randomUUID(), treatment: '', room: '', description: '', style: '' }]);
  };

  const removeItem = (id: string) => {
    if (items.length <= 1) return;
    setItems(prev => prev.filter(i => i.id !== id));
  };

  const updateItem = (id: string, field: keyof LineItem, value: any) => {
    setItems(prev => prev.map(i => i.id === id ? { ...i, [field]: value } : i));
  };

  // Combine items into treatment/rooms/notes for the API
  const buildProjectData = () => {
    const treatments = [...new Set(items.map(i => i.treatment).filter(Boolean))];
    const rooms = items.filter(i => i.room || i.treatment).map(i => ({
      name: i.room || 'Unspecified',
      treatment: i.treatment,
      style: i.style,
      description: i.description,
    }));
    return {
      name,
      address,
      treatment: treatments.join(', '),
      style: items[0]?.style || '',
      scope,
      rooms,
      // iX-day R1X-INT-FIX (Doctrine #4): business is required from the
      // request context. The luxe.empirebox.store public surface is the
      // Workroom intake. The default mirrors lib/intake-auth.ts:signup — the
      // only place "workroom" is named on the front-end, and it is the
      // public surface's self-identification, not a backend default.
      business: 'workroom',
    };
  };

  const createProject = async () => {
    const proj = await intakeFetch('/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildProjectData()),
    });
    setProjectId(proj.id);
    return proj.id;
  };

  // Save fabric info to backend
  const saveFabrics = async (pid: string) => {
    const fabrics = items
      .filter(i => i.fabric && i.fabric.fabric_preference !== 'not_sure')
      .map(item => ({
        ...item.fabric,
        room_name: item.room || 'Unspecified',
        item_name: item.description || item.treatment || 'Item',
      }));
    const res = await fetch(`${API_BASE}/api/v1/fabrics/intake-project/${pid}/fabrics`, {
      method: 'PUT',
      headers: intakeAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ fabrics }),
    });
    if (!res.ok) {
      throw new Error('Fabric details did not save');
    }
  };

  const ensureProject = async () => {
    if (projectId) return projectId;
    if (!name.trim()) {
      throw new Error('Enter a project name, then add the fabric photo.');
    }
    return createProject();
  };

  const saveDetails = async () => {
    if (!projectId) return;
    await intakeFetch(`/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...buildProjectData(),
        measurements: measurements.filter(m => m.room || m.width || m.height),
        notes,
      }),
    });
  };

  const handleNext = async () => {
    if (step === 0) {
      if (!name.trim()) return;
      try {
        let pid = projectId;
        if (!pid) {
          pid = await createProject();
        } else {
          await intakeFetch(`/projects/${pid}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(buildProjectData()),
          });
        }
        // Save fabric info when leaving step 0
        if (pid) await saveFabrics(pid);
      } catch (err) {
        console.error('Failed to save project:', err);
        return;
      }
    }
    setStep(s => s + 1);
  };

  const handleSubmit = async () => {
    if (!projectId) return;
    setSubmitting(true);
    try {
      await saveDetails();
      await saveFabrics(projectId);
      await intakeFetch(`/projects/${projectId}/submit`, { method: 'POST' });
      router.push(`/intake/project/${projectId}`);
    } catch (_err) {
      setSubmitting(false);
    }
  };

  const refreshPhotos = async () => {
    if (!projectId) return;
    const proj = await intakeFetch(`/projects/${projectId}`);
    setPhotos(proj.photos || []);
    setScans(proj.scans || []);
  };

  return (
    <div data-intake-page className="min-h-screen flex flex-col">
      <IntakeNav user={user} />

      <div className="intake-shell" style={{ flex: 1 }}>
        <IntakeStepper current={journeyFromFormStep(step)} />
        <p className="text-sm text-center mb-5" style={{ color: '#4f4a40' }}>
          {steps[step]}
        </p>

        <div className="intake-card">
          {/* Step 1: Project Info + Line Items */}
          {step === 0 && (
            <div className="space-y-4">
              <h2 className="text-2xl font-semibold mb-4">Tell Us About Your Project</h2>
              <div>
                <label className="intake-label block mb-1.5">Project Name *</label>
                <input type="text" required value={name} onChange={e => setName(e.target.value)}
                  className="form-input" placeholder="e.g., Johnson Residence - Full Home" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="intake-label block mb-1.5">Address</label>
                  <input type="text" value={address} onChange={e => setAddress(e.target.value)}
                    className="form-input" placeholder="123 Main St, City, ST" />
                </div>
                <div>
                  <label className="intake-label block mb-1.5">Scope</label>
                  <select value={scope} onChange={e => setScope(e.target.value)} className="form-input">
                    <option value="">Select...</option>
                    <option value="single-window">Single Window</option>
                    <option value="single-room">Single Room</option>
                    <option value="multiple-rooms">Multiple Rooms</option>
                    <option value="whole-home">Whole Home</option>
                  </select>
                </div>
              </div>

              {/* Line Items */}
              <div style={{ marginTop: 20 }}>
                <div className="flex items-center justify-between mb-3">
                  <label className="intake-label">
                    Items / Rooms ({items.length})
                  </label>
                  <button
                    type="button"
                    onClick={addItem}
                    className="flex items-center gap-1 text-sm font-bold cursor-pointer"
                    style={{ background: 'none', border: 'none', padding: 0, color: '#6b5408' }}
                  >
                    <Plus size={13} /> Add Item
                  </button>
                </div>

                <div className="space-y-3">
                  {items.map((item, idx) => (
                    <div key={item.id} className="p-3.5 rounded-[12px] bg-[#f5f3ef] border border-[#e5e0d8]">
                      <div className="flex items-center justify-between mb-2.5">
                        <span className="intake-label" style={{ color: '#6b5408' }}>ITEM {idx + 1}</span>
                        {items.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeItem(item.id)}
                            className="text-[#d5d0c8] hover:text-[#dc2626] transition-colors cursor-pointer"
                            style={{ background: 'none', border: 'none', padding: 0 }}
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-2.5 mb-2.5">
                        <div>
                          <select
                            value={item.treatment}
                            onChange={e => updateItem(item.id, 'treatment', e.target.value)}
                            className="form-input"
                          >
                            <option value="">Treatment type...</option>
                            {TREATMENTS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                          </select>
                        </div>
                        <div>
                          <input
                            type="text"
                            value={item.room}
                            onChange={e => updateItem(item.id, 'room', e.target.value)}
                            className="form-input"
                            placeholder="Room (e.g., Living Room)"
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2.5">
                        <div>
                          <select
                            value={item.style}
                            onChange={e => updateItem(item.id, 'style', e.target.value)}
                            className="form-input"
                          >
                            <option value="">Style...</option>
                            {STYLES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                          </select>
                        </div>
                        <div>
                          <input
                            type="text"
                            value={item.description}
                            onChange={e => updateItem(item.id, 'description', e.target.value)}
                            className="form-input"
                            placeholder="Details (e.g., 6 dining chairs)"
                          />
                        </div>
                      </div>

                      {/* Fabric toggle + section */}
                      {!item.showFabric ? (
                        <button
                          type="button"
                          onClick={() => updateItem(item.id, 'showFabric', true)}
                          className="flex items-center justify-center gap-2 mt-3 w-full text-sm font-bold cursor-pointer rounded-[8px] transition-colors"
                          style={{ background: '#fdf8eb', border: '1.5px dashed #b8960c', color: '#6b5408', padding: '12px 16px', minHeight: 48 }}
                        >
                          <Plus size={14} strokeWidth={2.5} /> Add Fabric Info
                        </button>
                      ) : (
                        <FabricInfoSection
                          label={`Fabric for ${item.room || item.treatment || `Item ${idx + 1}`}`}
                          fabric={item.fabric || defaultFabric(item.room, item.description || item.treatment)}
                          onChange={(f) => updateItem(item.id, 'fabric', f)}
                          onRemove={() => { updateItem(item.id, 'showFabric', false); updateItem(item.id, 'fabric', undefined); }}
                          projectId={projectId || undefined}
                          ensureProject={ensureProject}
                        />
                      )}
                    </div>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={addItem}
                  className="w-full mt-3 py-3 text-sm font-semibold border border-dashed rounded-[10px] transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  style={{ background: 'none', color: '#6b5408', borderColor: '#d4af37', minHeight: 48 }}
                >
                  <Plus size={13} /> Add Another Item
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Photos, Drawings & Scans */}
          {step === 1 && projectId && (
            <div>
              <h2 className="text-2xl font-semibold mb-2">Upload Photos, Drawings &amp; Scans</h2>
              <p className="text-sm mb-4" style={{ color: '#4f4a40' }}>
                Take photos of your windows, rooms, or any inspiration images. You can also attach drawings,
                CAD files, 3D scans, PDFs, spreadsheets, and other project documents.
              </p>
              <PhotoUploader projectId={projectId} photos={photos} scans={scans} onUpload={refreshPhotos} />
            </div>
          )}

          {/* Step 3: Measurements */}
          {step === 2 && (
            <div>
              <h2 className="text-2xl font-semibold mb-2">Window Measurements</h2>
              <p className="text-sm mb-4" style={{ color: '#4f4a40' }}>
                Enter approximate measurements. Don&apos;t worry about being exact — we&apos;ll verify everything before production.
              </p>
              <MeasurementInput measurements={measurements} onChange={setMeasurements} />
            </div>
          )}

          {/* Step 4: Notes & Submit */}
          {step === 3 && (
            <div>
              <h2 className="text-2xl font-semibold mb-2">Additional Notes</h2>
              <p className="text-sm mb-4" style={{ color: '#4f4a40' }}>
                Anything else we should know? Special requests, budget range, timeline?
              </p>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                rows={5}
                className="form-input resize-none"
                placeholder="Tell us anything that helps us create the perfect proposal for you..."
              />

              {/* Summary of items + fabric */}
              {items.filter(i => i.treatment || i.room).length > 0 && (
                <div className="mt-4 p-3 rounded-[10px] bg-[#f5f2ed] border border-[#ece8e0]">
                  <div className="intake-label mb-2">Project Summary</div>
                  {items.filter(i => i.treatment || i.room).map((item, idx) => (
                    <div key={item.id} className="py-1.5">
                      <div className="flex items-center gap-2 text-[12px]">
                        <span className="text-[#b8960c] font-bold">{idx + 1}.</span>
                        <span className="font-semibold text-[#333] capitalize">{item.treatment || 'TBD'}</span>
                        {item.room && <span className="text-[#888]">— {item.room}</span>}
                        {item.description && <span className="text-[#aaa]">({item.description})</span>}
                      </div>
                      {item.fabric && item.fabric.fabric_preference !== 'not_sure' && (
                        <div className="ml-5 mt-0.5 text-[11px] text-[#b8960c]">
                          Fabric: {item.fabric.fabric_preference === 'com' ? 'COM — ' : ''}
                          {item.fabric.fabric_name || item.fabric.color_pattern || 'Selected'}
                          {item.fabric.supplier_url && ' (link provided)'}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 p-4 rounded-[12px] bg-[#fdf8eb] border border-[#ead9a0]">
                <h3 className="text-base font-semibold mb-1">Ready to submit?</h3>
                <p className="text-sm" style={{ color: '#4f4a40' }}>
                  We&apos;ll review your project and send you a 3-tier proposal within 24 hours. You can always add more photos or details later.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        <div className="flex items-center justify-between mt-6 gap-3">
          {step > 0 ? (
            <button
              onClick={() => setStep(s => s - 1)}
              className="intake-btn intake-btn-ghost"
            >
              <ArrowLeft size={14} /> Back
            </button>
          ) : (
            <button
              onClick={() => router.push('/intake/dashboard')}
              className="intake-btn intake-btn-ghost"
            >
              <ArrowLeft size={14} /> Dashboard
            </button>
          )}

          {step < 3 ? (
            <button
              onClick={handleNext}
              disabled={step === 0 && !name.trim()}
              className="intake-btn intake-btn-charcoal flex-1 sm:flex-none"
            >
              Next <ArrowRight size={14} />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="intake-btn intake-btn-success flex-1 sm:flex-none"
            >
              {submitting ? 'Submitting...' : (<><Send size={14} /> Submit Project</>)}
            </button>
          )}
        </div>
      </div>
      <IntakeFooter />
    </div>
  );
}
