'use client';
import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft, MapPin, Camera, Ruler, FileText, MessageSquare,
  Send, Download, CheckCircle, Clock, Scissors, Link2, ExternalLink, Plus,
} from 'lucide-react';
import IntakeNav from '../../../components/intake/IntakeNav';
import PhotoUploader from '../../../components/intake/PhotoUploader';
import FabricInfoSection, { FabricInfo } from '../../../components/intake/FabricInfoSection';
import { intakeFetch, getToken } from '../../../lib/intake-auth';

const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store'
  : 'http://localhost:8000';

const statusConfig: Record<string, { label: string; color: string; bg: string; icon: any }> = {
  draft: { label: 'Draft', color: '#888', bg: '#f5f3ef', icon: Clock },
  submitted: { label: 'Submitted — Under Review', color: '#2563eb', bg: '#dbeafe', icon: Clock },
  'quote-ready': { label: 'Quote Ready', color: '#b8960c', bg: '#fdf8eb', icon: FileText },
  approved: { label: 'Approved', color: '#16a34a', bg: '#dcfce7', icon: CheckCircle },
  'in-production': { label: 'In Production', color: '#7c3aed', bg: '#ede9fe', icon: Clock },
  installed: { label: 'Installed', color: '#16a34a', bg: '#dcfce7', icon: CheckCircle },
};

export default function ProjectDetail() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;

  const [user, setUser] = useState<any>(null);
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [showAddMeasurement, setShowAddMeasurement] = useState(false);
  const [newMeasurement, setNewMeasurement] = useState({ room: '', width: '', height: '', reference: '' });
  const [savingMeasurement, setSavingMeasurement] = useState(false);
  const [fabricEntries, setFabricEntries] = useState<any[]>([]);
  const [showAddFabric, setShowAddFabric] = useState(false);
  const [newFabric, setNewFabric] = useState<FabricInfo>({
    scope: 'room',
    fabric_preference: 'not_sure',
  });
  const [savingFabric, setSavingFabric] = useState(false);

  const loadFabrics = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/fabrics/intake-project/${projectId}/fabrics`);
      if (res.ok) {
        const data = await res.json();
        setFabricEntries(Array.isArray(data) ? data : []);
      }
    } catch { /* best effort */ }
  };

  const loadProject = async () => {
    try {
      const proj = await intakeFetch(`/projects/${projectId}`);
      setProject(proj);
    } catch (_err) {
      router.push('/intake/dashboard');
    }
  };

  useEffect(() => {
    if (!getToken()) { router.push('/intake/login'); return; }
    const init = async () => {
      try {
        const me = await intakeFetch('/me');
        setUser(me);
        await loadProject();
        await loadFabrics();
      } catch (_err) {
        router.push('/intake/login');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [projectId, router]);

  const sendMessage = async () => {
    if (!message.trim()) return;
    setSending(true);
    try {
      await intakeFetch(`/projects/${projectId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: message }),
      });
      setMessage('');
      await loadProject();
    } catch (_err) {
      // ignore
    } finally {
      setSending(false);
    }
  };

  const canEdit = ['draft', 'submitted', 'quote-ready'].includes(project?.status || '');

  const addMeasurement = async () => {
    if (!newMeasurement.width || !newMeasurement.height) return;
    setSavingMeasurement(true);
    try {
      const updated = [...measurements, {
        room: newMeasurement.room || `Window ${measurements.length + 1}`,
        width: newMeasurement.width,
        height: newMeasurement.height,
        reference: newMeasurement.reference || 'none',
      }];
      await intakeFetch(`/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ measurements: updated }),
      });
      setNewMeasurement({ room: '', width: '', height: '', reference: '' });
      setShowAddMeasurement(false);
      await loadProject();
    } catch (_err) { /* ignore */ }
    setSavingMeasurement(false);
  };

  const removeMeasurement = async (index: number) => {
    const updated = measurements.filter((_: any, i: number) => i !== index);
    try {
      await intakeFetch(`/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ measurements: updated }),
      });
      await loadProject();
    } catch (_err) { /* ignore */ }
  };

  const saveFabric = async () => {
    if (newFabric.fabric_preference === 'not_sure') return;
    setSavingFabric(true);
    try {
      const payload = {
        ...newFabric,
        room_name: newFabric.room_name || project?.name || 'Project',
        item_name: newFabric.item_name || '',
      };
      await fetch(`${API_BASE}/api/v1/fabrics/intake-project/${projectId}/fabrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setShowAddFabric(false);
      setNewFabric({ scope: 'room', fabric_preference: 'not_sure' });
      await loadFabrics();
    } catch { /* best effort */ }
    setSavingFabric(false);
  };

  const removeFabric = async (id: number) => {
    try {
      await fetch(`${API_BASE}/api/v1/fabrics/intake-project/${projectId}/fabrics/${id}`, { method: 'DELETE' });
      await loadFabrics();
    } catch { /* best effort */ }
  };

  if (loading || !project) {
    return (
      <div data-intake-page className="min-h-screen bg-[#f5f2ed] flex items-center justify-center">
        <div className="text-[12px] text-[#999]">Loading...</div>
      </div>
    );
  }

  const status = statusConfig[project.status] || statusConfig.draft;
  const StatusIcon = status.icon;
  const photos = project.photos || [];
  const measurements = project.measurements || [];
  const messages = project.messages || [];

  return (
    <div data-intake-page className="min-h-screen bg-[#f5f2ed]">
      <IntakeNav user={user} />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <button
          onClick={() => router.push('/intake/dashboard')}
          className="flex items-center gap-1.5 text-[11px] text-[#999] hover:text-[#b8960c] transition-colors mb-4"
        >
          <ArrowLeft size={13} /> Back to Projects
        </button>

        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className="inline-flex items-center gap-1 text-[9px] font-bold px-2.5 py-0.5 rounded-md"
                style={{ color: status.color, background: status.bg }}
              >
                <StatusIcon size={10} /> {status.label}
              </span>
              <span className="text-[9px] text-[#c5c0b8] font-medium">{project.intake_code}</span>
            </div>
            <h1 className="text-lg font-bold text-[#1a1a1a]">{project.name}</h1>
            {project.address && (
              <div className="flex items-center gap-1 text-[11px] text-[#888] mt-1">
                <MapPin size={11} /> {project.address}
              </div>
            )}
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {project.treatment && (
            <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[10px] p-3">
              <div className="text-[9px] text-[#c5c0b8] font-semibold uppercase tracking-[0.5px] mb-0.5">Treatment</div>
              <div className="text-[12px] font-semibold text-[#1a1a1a] capitalize">{project.treatment}</div>
            </div>
          )}
          {project.style && (
            <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[10px] p-3">
              <div className="text-[9px] text-[#c5c0b8] font-semibold uppercase tracking-[0.5px] mb-0.5">Style</div>
              <div className="text-[12px] font-semibold text-[#1a1a1a] capitalize">{project.style}</div>
            </div>
          )}
          {project.scope && (
            <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[10px] p-3">
              <div className="text-[9px] text-[#c5c0b8] font-semibold uppercase tracking-[0.5px] mb-0.5">Scope</div>
              <div className="text-[12px] font-semibold text-[#1a1a1a] capitalize">{project.scope.replace(/-/g, ' ')}</div>
            </div>
          )}
          <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[10px] p-3">
            <div className="text-[9px] text-[#c5c0b8] font-semibold uppercase tracking-[0.5px] mb-0.5">Photos</div>
            <div className="text-[12px] font-semibold text-[#1a1a1a]">{photos.length}</div>
          </div>
        </div>

        {/* Quote PDF */}
        {project.quote_pdf && (
          <div className="bg-[#fdf8eb] border border-[#b8960c]/20 rounded-[14px] p-4 mb-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <FileText size={16} className="text-[#b8960c]" />
                <div>
                  <div className="text-[13px] font-semibold text-[#1a1a1a]">Your Quote is Ready</div>
                  <div className="text-[10px] text-[#888]">Review your 3-tier proposal and choose an option</div>
                </div>
              </div>
              <a
                href={`${API_BASE}${project.quote_pdf}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2.5 min-h-[44px] text-sm font-bold bg-[#b8960c] text-white rounded-[10px] hover:bg-[#a3850b] transition-colors flex items-center gap-1.5"
              >
                <Download size={13} /> View Quote
              </a>
            </div>
          </div>
        )}

        {/* Photos section */}
        <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-5 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <Camera size={14} className="text-[#b8960c]" />
            <h2 className="text-[13px] font-bold text-[#1a1a1a]">Photos</h2>
          </div>
          {canEdit ? (
            <PhotoUploader projectId={projectId} photos={photos} onUpload={loadProject} />
          ) : photos.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {photos.map((p: any, i: number) => (
                <div key={i} className="relative aspect-square rounded-[10px] overflow-hidden bg-[#f5f2ed] border border-[#ece8e0]">
                  <img
                    src={`${API_BASE}${p.path}`}
                    alt={p.original_name}
                    className="w-full h-full object-cover"
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-[#c5c0b8]">No photos uploaded.</p>
          )}
        </div>

        {/* Measurements / Dimensions section */}
        <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-5 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Ruler size={14} className="text-[#b8960c]" />
              <h2 className="text-[13px] font-bold text-[#1a1a1a]">Dimensions</h2>
              {measurements.length > 0 && (
                <span className="text-[9px] font-bold text-[#b8960c] bg-[#fdf8eb] px-2 py-0.5 rounded-md">
                  {measurements.length}
                </span>
              )}
            </div>
            {canEdit && !showAddMeasurement && (
              <button
                onClick={() => setShowAddMeasurement(true)}
                className="text-[10px] font-bold text-[#b8960c] hover:text-[#a3850b] transition-colors"
              >
                + Add Window
              </button>
            )}
          </div>

          {measurements.length > 0 && (
            <div className="space-y-2 mb-3">
              {measurements.map((m: any, i: number) => (
                <div key={i} className="flex items-center gap-3 text-[12px] p-2.5 rounded-[10px] bg-[#f5f2ed] border border-[#ece8e0]">
                  <span className="font-semibold text-[#1a1a1a] min-w-[100px]">{m.room || `Window ${i + 1}`}</span>
                  <span className="text-[#888]">{m.width}&quot; W &times; {m.height}&quot; H</span>
                  {m.reference && m.reference !== 'none' && (
                    <span className="text-[9px] text-[#c5c0b8] px-1.5 py-0.5 bg-[#faf9f7] rounded-md border border-[#ece8e0] font-medium">
                      ref: {m.reference}
                    </span>
                  )}
                  {canEdit && (
                    <button
                      onClick={() => removeMeasurement(i)}
                      className="ml-auto text-[9px] text-[#ccc] hover:text-[#dc2626] transition-colors"
                    >
                      remove
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {measurements.length === 0 && !showAddMeasurement && (
            <p className="text-[11px] text-[#c5c0b8] mb-2">
              No dimensions added yet.{canEdit ? ' Add window measurements for an accurate quote.' : ''}
            </p>
          )}

          {showAddMeasurement && (
            <div className="bg-[#f5f2ed] border border-[#ece8e0] rounded-[10px] p-4">
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-[9px] text-[#999] font-semibold uppercase tracking-[0.5px] block mb-1">Room / Location</label>
                  <input
                    type="text"
                    value={newMeasurement.room}
                    onChange={e => setNewMeasurement(p => ({ ...p, room: e.target.value }))}
                    placeholder="e.g. Living Room"
                    className="form-input w-full text-[12px]"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-[#999] font-semibold uppercase tracking-[0.5px] block mb-1">Reference</label>
                  <input
                    type="text"
                    value={newMeasurement.reference}
                    onChange={e => setNewMeasurement(p => ({ ...p, reference: e.target.value }))}
                    placeholder="e.g. Bay window left"
                    className="form-input w-full text-[12px]"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="text-[9px] text-[#999] font-semibold uppercase tracking-[0.5px] block mb-1">Width (inches)</label>
                  <input
                    type="number"
                    value={newMeasurement.width}
                    onChange={e => setNewMeasurement(p => ({ ...p, width: e.target.value }))}
                    placeholder='72'
                    className="form-input w-full text-[12px]"
                    min="1"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-[#999] font-semibold uppercase tracking-[0.5px] block mb-1">Height (inches)</label>
                  <input
                    type="number"
                    value={newMeasurement.height}
                    onChange={e => setNewMeasurement(p => ({ ...p, height: e.target.value }))}
                    placeholder='84'
                    className="form-input w-full text-[12px]"
                    min="1"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={addMeasurement}
                  disabled={savingMeasurement || !newMeasurement.width || !newMeasurement.height}
                  className="px-4 py-2.5 min-h-[44px] text-sm font-bold bg-[#b8960c] text-white rounded-[10px] hover:bg-[#a3850b] transition-colors disabled:opacity-50"
                >
                  {savingMeasurement ? 'Saving...' : 'Add Dimension'}
                </button>
                <button
                  onClick={() => { setShowAddMeasurement(false); setNewMeasurement({ room: '', width: '', height: '', reference: '' }); }}
                  className="px-4 py-2.5 min-h-[44px] text-sm text-[#888] hover:text-[#555] transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Fabric Selections — always visible */}
        <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-5 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Scissors size={14} className="text-[#b8960c]" />
              <h2 className="text-[13px] font-bold text-[#1a1a1a]">Fabric Info</h2>
              {fabricEntries.length > 0 && (
                <span className="text-[9px] font-bold text-[#b8960c] bg-[#fdf8eb] px-2 py-0.5 rounded-md">
                  {fabricEntries.length}
                </span>
              )}
            </div>
            {canEdit && !showAddFabric && (
              <button
                onClick={() => setShowAddFabric(true)}
                className="text-[10px] font-bold text-[#b8960c] hover:text-[#a3850b] transition-colors cursor-pointer"
                style={{ background: 'none', border: 'none', padding: 0 }}
              >
                + Add Fabric
              </button>
            )}
          </div>

          {/* Existing fabric entries */}
          {fabricEntries.length > 0 && (
            <div className="space-y-3 mb-3">
              {fabricEntries.map((f: any) => (
                <div key={f.id} className="p-3 rounded-[10px] bg-[#f5f2ed] border border-[#ece8e0]">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-[#b8960c] uppercase">
                        {f.room_name}{f.item_name ? ` — ${f.item_name}` : ''}
                      </span>
                      <span className="text-[9px] px-2 py-0.5 rounded-md font-semibold" style={{
                        background: f.fabric_preference === 'com' ? '#fef3c7' : f.fabric_preference === 'picked_out' ? '#dcfce7' : '#f5f2ed',
                        color: f.fabric_preference === 'com' ? '#92400e' : f.fabric_preference === 'picked_out' ? '#166534' : '#888',
                      }}>
                        {f.fabric_preference === 'picked_out' ? 'Client Selected' : f.fabric_preference === 'com' ? 'COM' : f.fabric_preference === 'recommend' ? 'Needs Recommendation' : 'Not Sure'}
                      </span>
                    </div>
                    {canEdit && (
                      <button
                        onClick={() => removeFabric(f.id)}
                        className="text-[9px] text-[#ccc] hover:text-[#dc2626] transition-colors cursor-pointer"
                        style={{ background: 'none', border: 'none', padding: 0 }}
                      >
                        remove
                      </button>
                    )}
                  </div>
                  {f.fabric_name && (
                    <div className="text-[12px] font-semibold text-[#333]">{f.fabric_name}</div>
                  )}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-[11px] text-[#888]">
                    {f.color_pattern && <span>Color: {f.color_pattern}</span>}
                    {f.fabric_code && <span>Code: {f.fabric_code}</span>}
                    {f.material_type && <span>Type: {f.material_type}</span>}
                    {f.fabric_width && <span>Width: {f.fabric_width}&quot;</span>}
                    {f.vertical_repeat && <span>V-Repeat: {f.vertical_repeat}&quot;</span>}
                    {f.horizontal_repeat && <span>H-Repeat: {f.horizontal_repeat}&quot;</span>}
                    {f.yards_available && <span>Yards on hand: {f.yards_available}</span>}
                  </div>
                  {f.supplier_url && (
                    <a
                      href={f.supplier_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 mt-1.5 text-[11px] font-semibold text-[#b8960c] hover:text-[#a3850b] transition-colors"
                    >
                      <ExternalLink size={10} /> Open supplier page
                    </a>
                  )}
                  {f.swatch_photo_path && (
                    <img
                      src={f.swatch_photo_path.startsWith('http') ? f.swatch_photo_path : `${API_BASE}${f.swatch_photo_path}`}
                      alt="Swatch"
                      className="mt-2 rounded-[8px] border border-[#ece8e0]"
                      style={{ width: 80, height: 80, objectFit: 'cover' }}
                    />
                  )}
                  {f.client_notes && (
                    <p className="mt-1.5 text-[11px] text-[#888] italic">{f.client_notes}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Add fabric form */}
          {showAddFabric && canEdit && (
            <div className="mt-3">
              <div className="grid grid-cols-2 gap-2.5 mb-3">
                <div>
                  <label className="text-[9px] text-[#999] font-semibold uppercase tracking-[0.5px] block mb-1">Room / Area</label>
                  <input
                    type="text"
                    value={newFabric.room_name || ''}
                    onChange={e => setNewFabric(f => ({ ...f, room_name: e.target.value }))}
                    placeholder="e.g. Living Room"
                    className="form-input w-full text-[12px]"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-[#999] font-semibold uppercase tracking-[0.5px] block mb-1">Item</label>
                  <input
                    type="text"
                    value={newFabric.item_name || ''}
                    onChange={e => setNewFabric(f => ({ ...f, item_name: e.target.value }))}
                    placeholder="e.g. Sofa, Drapes"
                    className="form-input w-full text-[12px]"
                  />
                </div>
              </div>
              <FabricInfoSection
                label="Fabric Details"
                fabric={newFabric}
                onChange={setNewFabric}
                projectId={projectId}
              />
              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={saveFabric}
                  disabled={savingFabric || newFabric.fabric_preference === 'not_sure'}
                  className="px-4 py-2.5 min-h-[44px] text-sm font-bold bg-[#b8960c] text-white rounded-[10px] hover:bg-[#a3850b] transition-colors disabled:opacity-50 cursor-pointer"
                >
                  {savingFabric ? 'Saving...' : 'Save Fabric'}
                </button>
                <button
                  onClick={() => { setShowAddFabric(false); setNewFabric({ scope: 'room', fabric_preference: 'not_sure' }); }}
                  className="px-4 py-2.5 min-h-[44px] text-sm text-[#888] hover:text-[#555] transition-colors cursor-pointer"
                  style={{ background: 'none', border: 'none' }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Empty state with big add button */}
          {fabricEntries.length === 0 && !showAddFabric && (
            <div>
              <p className="text-[11px] text-[#c5c0b8] mb-3">
                No fabric info added yet.{canEdit ? ' Tell us about your fabric preferences.' : ''}
              </p>
              {canEdit && (
                <button
                  onClick={() => setShowAddFabric(true)}
                  className="flex items-center justify-center gap-2 w-full text-[12px] font-bold text-[#b8960c] cursor-pointer rounded-[8px] hover:bg-[#fdf8eb] active:bg-[#fdf8eb] transition-colors"
                  style={{ background: '#fdf8eb', border: '1.5px dashed #b8960c', padding: '12px 16px', minHeight: 48 }}
                >
                  <Plus size={14} strokeWidth={2.5} /> Add Fabric Info
                </button>
              )}
            </div>
          )}
        </div>

        {/* Notes */}
        {project.notes && (
          <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-5 mb-4">
            <h2 className="text-[13px] font-bold text-[#1a1a1a] mb-2">Notes</h2>
            <p className="text-[12px] text-[#888] whitespace-pre-wrap leading-relaxed">{project.notes}</p>
          </div>
        )}

        {/* Messages */}
        <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-5">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare size={14} className="text-[#b8960c]" />
            <h2 className="text-[13px] font-bold text-[#1a1a1a]">Messages</h2>
          </div>

          {messages.length > 0 ? (
            <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
              {messages.map((msg: any, i: number) => (
                <div
                  key={i}
                  className={`p-3 rounded-[10px] text-[12px] ${
                    msg.from === 'client'
                      ? 'bg-[#fdf8eb] border border-[#b8960c]/15 ml-8'
                      : 'bg-[#f5f2ed] border border-[#ece8e0] mr-8'
                  }`}
                >
                  <div className="font-semibold text-[#1a1a1a] mb-1">
                    {msg.from === 'client' ? 'You' : 'Empire Team'}
                  </div>
                  <div className="text-[#555]">{msg.text}</div>
                  {msg.timestamp && (
                    <div className="text-[9px] text-[#c5c0b8] mt-1">
                      {new Date(msg.timestamp).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-[#c5c0b8] mb-4">No messages yet. Send one to start the conversation.</p>
          )}

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Type a message..."
              className="form-input flex-1"
            />
            <button
              onClick={sendMessage}
              disabled={sending || !message.trim()}
              className="px-3.5 py-2 bg-[#1a1a1a] text-white rounded-[10px] hover:bg-[#333] transition-colors disabled:opacity-50"
            >
              <Send size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
