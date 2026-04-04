'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import {
  Gem, RefreshCw, Users, FolderOpen, Camera, Ruler, Clock,
  CheckCircle2, FileText, MessageSquare, ChevronDown, ChevronUp,
  ExternalLink, Image, Maximize2, Send, AlertCircle, Eye, Scissors, Loader2, TreePine,
  Pencil, Trash2, X, Save, BookOpen, Download, Archive, RotateCcw,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';

interface IntakeUser {
  id: string;
  name: string;
  email: string;
  phone?: string;
  company?: string;
  role: string;
  created_at: string;
  deleted_at?: string;
}

interface IntakeProject {
  id: string;
  user_id: string;
  intake_code: string;
  name: string;
  address?: string;
  status: string;
  rooms?: string;
  photos?: string;
  scans?: string;
  measurements?: string;
  treatment?: string;
  style?: string;
  scope?: string;
  notes?: string;
  quote_pdf?: string;
  selected_proposal?: string;
  messages?: string;
  created_at: string;
  updated_at?: string;
  deleted_at?: string;
  // Joined from user
  user_name?: string;
  user_email?: string;
  user_company?: string;
  user_role?: string;
}

const STATUS_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  draft: { bg: '#f3f4f6', color: '#6b7280', label: 'Draft' },
  submitted: { bg: '#dbeafe', color: '#2563eb', label: 'Submitted' },
  'quote-ready': { bg: '#fef3c7', color: '#d97706', label: 'Quote Ready' },
  approved: { bg: '#dcfce7', color: '#16a34a', label: 'Approved' },
  'in-production': { bg: '#ede9fe', color: '#7c3aed', label: 'In Production' },
  installed: { bg: '#d1fae5', color: '#059669', label: 'Installed' },
};

const TREATMENT_LABELS: Record<string, string> = {
  drapery: 'Drapery',
  blinds: 'Blinds',
  shades: 'Shades',
  shutters: 'Shutters',
  upholstery: 'Upholstery',
  bedding: 'Bedding',
  other: 'Other',
};

interface LuxeForgePageProps {
  onNavigate?: (product: string, screen: string, section?: string) => void;
}

export default function LuxeForgePage({ onNavigate }: LuxeForgePageProps) {
  const [projects, setProjects] = useState<IntakeProject[]>([]);
  const [users, setUsers] = useState<IntakeUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [refreshing, setRefreshing] = useState(false);
  const [sendingToWorkroom, setSendingToWorkroom] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<string | null>(null);
  const [editUserData, setEditUserData] = useState<Partial<IntakeUser>>({});
  const [activeTab, setActiveTab] = useState<'projects' | 'docs' | 'archived'>('projects');
  const [viewingPhoto, setViewingPhoto] = useState<{ url: string; name: string; projectName: string } | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [archivedUsers, setArchivedUsers] = useState<IntakeUser[]>([]);
  const [archivedProjects, setArchivedProjects] = useState<IntakeProject[]>([]);
  const [restoringId, setRestoringId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const [projRes, usersRes] = await Promise.all([
        fetch(`${API}/intake/admin/projects`).then(r => r.ok ? r.json() : []),
        fetch(`${API}/intake/admin/users`).then(r => r.ok ? r.json() : []),
      ]);
      setProjects(Array.isArray(projRes) ? projRes : []);
      setUsers(Array.isArray(usersRes) ? usersRes : []);
    } catch (e: any) {
      setError('Could not load intake data. Backend may not have admin endpoints yet.');
      // Try individual project fetch as fallback
      try {
        const res = await fetch(`${API}/intake/projects`);
        if (res.ok) {
          const data = await res.json();
          setProjects(Array.isArray(data) ? data : []);
        }
      } catch {}
    }
    setLoading(false);
    setRefreshing(false);
  }, []);

  const fetchArchived = useCallback(async () => {
    try {
      const res = await fetch(`${API}/intake/admin/archived`);
      if (res.ok) {
        const data = await res.json();
        setArchivedUsers(Array.isArray(data.users) ? data.users : []);
        setArchivedProjects(Array.isArray(data.projects) ? data.projects : []);
      }
    } catch {}
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { if (activeTab === 'archived') fetchArchived(); }, [activeTab, fetchArchived]);

  const parseJSON = (str?: string): any[] => {
    if (!str) return [];
    try { return JSON.parse(str); } catch { return []; }
  };

  const filteredProjects = filter === 'all'
    ? projects
    : projects.filter(p => p.status === filter);

  // KPI calculations
  const totalProjects = projects.length;
  const submitted = projects.filter(p => p.status === 'submitted').length;
  const approved = projects.filter(p => ['approved', 'in-production', 'installed'].includes(p.status)).length;
  const totalPhotos = projects.reduce((sum, p) => sum + parseJSON(p.photos).length, 0);

  const toggleProject = (id: string) => {
    setExpandedProject(prev => prev === id ? null : id);
  };

  const sendToWorkroom = async (projectId: string, businessUnit: string = 'workroom') => {
    setSendingToWorkroom(projectId);
    try {
      const res = await fetch(`${API}/intake/admin/projects/${projectId}/to-quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_unit: businessUnit }),
      });
      if (res.ok) {
        const data = await res.json();
        await fetchData();
        const quoteNum = data.quote_number || data.quote_id || '';
        const unitLabel = businessUnit === 'woodcraft' ? 'WoodCraft' : 'Workroom';
        if (confirm(`✅ Quote ${quoteNum} created for ${unitLabel}!\n\nCustomer info and photos transferred.\n\nGo to ${unitLabel} Quotes now?`)) {
          if (onNavigate) {
            onNavigate(businessUnit === 'woodcraft' ? 'craft' : 'workroom', 'dashboard', 'quotes');
          }
        }
      } else {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
        alert(`Failed: ${err.detail || 'Could not create quote'}`);
      }
    } catch (e: any) {
      alert(`Error: ${e.message}`);
    }
    setSendingToWorkroom(null);
  };

  const startEditUser = (user: IntakeUser) => {
    setEditingUser(user.id);
    setEditUserData({ name: user.name, email: user.email, phone: user.phone || '', company: user.company || '', role: user.role });
  };

  const saveUser = async (userId: string) => {
    try {
      const res = await fetch(`${API}/intake/admin/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editUserData),
      });
      if (res.ok) {
        setEditingUser(null);
        await fetchData();
      } else {
        alert('Failed to update user');
      }
    } catch { alert('Error updating user'); }
  };

  const deleteUser = async (userId: string, userName: string) => {
    if (!confirm(`Archive user "${userName}" and all their projects? They can be restored later.`)) return;
    try {
      const res = await fetch(`${API}/intake/admin/users/${userId}`, { method: 'DELETE' });
      if (res.ok) await fetchData();
      else alert('Failed to archive user');
    } catch { alert('Error archiving user'); }
  };

  const restoreUser = async (userId: string) => {
    setRestoringId(userId);
    try {
      const res = await fetch(`${API}/intake/admin/users/${userId}/restore`, { method: 'POST' });
      if (res.ok) {
        await Promise.all([fetchData(), fetchArchived()]);
      } else {
        alert('Failed to restore user');
      }
    } catch { alert('Error restoring user'); }
    setRestoringId(null);
  };

  const restoreProject = async (projectId: string) => {
    setRestoringId(projectId);
    try {
      const res = await fetch(`${API}/intake/admin/projects/${projectId}/restore`, { method: 'POST' });
      if (res.ok) {
        await Promise.all([fetchData(), fetchArchived()]);
      } else {
        alert('Failed to restore project');
      }
    } catch { alert('Error restoring project'); }
    setRestoringId(null);
  };

  return (
    <div className="flex-1 overflow-y-auto" style={{ padding: '20px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <div style={{
          width: 44, height: 44, borderRadius: 12, background: '#7c3aed18',
          border: '2px solid #7c3aed40', display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#7c3aed', flexShrink: 0,
        }}>
          <Gem size={20} />
        </div>
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
            LuxeForge — Intake Dashboard
          </h1>
          <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
            Designer & installer project submissions
          </div>
        </div>
        <button
          onClick={fetchData}
          disabled={refreshing}
          style={{
            background: 'none', border: '1px solid #ece8e0', borderRadius: 8,
            padding: '6px 12px', cursor: 'pointer', display: 'flex',
            alignItems: 'center', gap: 6, fontSize: 12, color: '#666',
          }}
        >
          <RefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          Refresh
        </button>
        <a
          href="/intake"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            background: '#7c3aed', border: 'none', borderRadius: 8,
            padding: '6px 14px', cursor: 'pointer', display: 'flex',
            alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700,
            color: '#fff', textDecoration: 'none',
          }}
        >
          <ExternalLink size={14} />
          Intake Portal
        </a>
      </div>

      {/* Tab Switcher */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[
          { id: 'projects' as const, label: 'Projects', icon: <FolderOpen size={14} /> },
          { id: 'archived' as const, label: `Archived${archivedUsers.length > 0 ? ` (${archivedUsers.length})` : ''}`, icon: <Archive size={14} /> },
          { id: 'docs' as const, label: 'Documentation', icon: <BookOpen size={14} /> },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
              borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer',
              border: activeTab === tab.id ? '1.5px solid #7c3aed' : '1.5px solid #ece8e0',
              background: activeTab === tab.id ? '#f5f0ff' : '#faf9f7',
              color: activeTab === tab.id ? '#7c3aed' : '#888',
              transition: 'all 0.15s',
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'docs' ? (
        <ProductDocs product="luxe" />
      ) : activeTab === 'archived' ? (
        /* ── Archived Tab ─────────────────────────────── */
        <div>
          {archivedUsers.length === 0 && archivedProjects.length === 0 ? (
            <div style={{
              textAlign: 'center', padding: 40, background: '#faf9f7',
              border: '1px solid #ece8e0', borderRadius: 14,
            }}>
              <Archive size={32} style={{ color: '#ccc', marginBottom: 8 }} />
              <div style={{ fontSize: 14, color: '#888' }}>No archived items</div>
              <div style={{ fontSize: 12, color: '#bbb', marginTop: 4 }}>
                Deleted users and projects will appear here for recovery
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Archived Users */}
              {archivedUsers.length > 0 && (
                <div style={{
                  background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14,
                  padding: '16px 20px',
                }}>
                  <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600, marginBottom: 12 }}>
                    Archived Users ({archivedUsers.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {archivedUsers.map(u => {
                      const userArchivedProjects = archivedProjects.filter(p => p.user_id === u.id);
                      return (
                        <div key={u.id} style={{
                          display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
                          background: '#fff', borderRadius: 10, border: '1px solid #e8e4dc',
                          opacity: 0.75,
                        }}>
                          <div style={{
                            width: 36, height: 36, borderRadius: 10, background: '#fee2e2',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                          }}>
                            <Trash2 size={16} style={{ color: '#dc2626' }} />
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ fontSize: 14, fontWeight: 700, color: '#666' }}>{u.name}</span>
                              <span style={{
                                fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                                background: '#fee2e2', color: '#dc2626', textTransform: 'uppercase',
                              }}>
                                Archived
                              </span>
                            </div>
                            <div style={{ fontSize: 12, color: '#999', marginTop: 2, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                              <span>{u.email}</span>
                              {u.phone && <span>· {u.phone}</span>}
                              {u.company && <span>· {u.company}</span>}
                            </div>
                            <div style={{ fontSize: 10, color: '#bbb', marginTop: 3 }}>
                              Deleted: {u.deleted_at ? new Date(u.deleted_at).toLocaleString() : '—'}
                              {' · '}{userArchivedProjects.length} project{userArchivedProjects.length !== 1 ? 's' : ''}
                            </div>
                          </div>
                          <button
                            onClick={() => restoreUser(u.id)}
                            disabled={restoringId === u.id}
                            style={{
                              display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                              borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700,
                              background: '#16a34a', color: '#fff',
                              opacity: restoringId === u.id ? 0.5 : 1,
                            }}
                          >
                            <RotateCcw size={13} />
                            {restoringId === u.id ? 'Restoring...' : 'Restore'}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Orphan archived projects (user not archived but project is) */}
              {(() => {
                const archivedUserIds = new Set(archivedUsers.map(u => u.id));
                const orphanProjects = archivedProjects.filter(p => !archivedUserIds.has(p.user_id));
                if (orphanProjects.length === 0) return null;
                return (
                  <div style={{
                    background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14,
                    padding: '16px 20px',
                  }}>
                    <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600, marginBottom: 12 }}>
                      Archived Projects ({orphanProjects.length})
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {orphanProjects.map(p => (
                        <div key={p.id} style={{
                          display: 'flex', alignItems: 'center', gap: 12, padding: '12px 14px',
                          background: '#fff', borderRadius: 10, border: '1px solid #e8e4dc',
                          opacity: 0.75,
                        }}>
                          <div style={{
                            width: 36, height: 36, borderRadius: 10, background: '#fee2e2',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                          }}>
                            <FolderOpen size={16} style={{ color: '#dc2626' }} />
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 14, fontWeight: 700, color: '#666' }}>{p.name || p.intake_code}</div>
                            <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
                              {p.user_name || 'Unknown user'} · {p.intake_code}
                              {p.treatment && ` · ${TREATMENT_LABELS[p.treatment] || p.treatment}`}
                            </div>
                            <div style={{ fontSize: 10, color: '#bbb', marginTop: 3 }}>
                              Deleted: {p.deleted_at ? new Date(p.deleted_at).toLocaleString() : '—'}
                            </div>
                          </div>
                          <button
                            onClick={() => restoreProject(p.id)}
                            disabled={restoringId === p.id}
                            style={{
                              display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                              borderRadius: 8, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700,
                              background: '#16a34a', color: '#fff',
                              opacity: restoringId === p.id ? 0.5 : 1,
                            }}
                          >
                            <RotateCcw size={13} />
                            {restoringId === p.id ? 'Restoring...' : 'Restore'}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      ) : (
      <>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Total Projects', value: totalProjects, icon: <FolderOpen size={16} />, color: '#7c3aed' },
          { label: 'Awaiting Review', value: submitted, icon: <Clock size={16} />, color: '#2563eb' },
          { label: 'Approved', value: approved, icon: <CheckCircle2 size={16} />, color: '#16a34a' },
          { label: 'Photos Uploaded', value: totalPhotos, icon: <Camera size={16} />, color: '#d97706' },
        ].map(kpi => (
          <div key={kpi.label} style={{
            background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 12,
            padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10, background: kpi.color + '15',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: kpi.color,
            }}>
              {kpi.icon}
            </div>
            <div>
              <div style={{ fontSize: 22, fontWeight: 700, color: kpi.color }}>{kpi.value}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{kpi.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Registered Users */}
      {users.length > 0 && (
        <div style={{
          background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14,
          padding: '16px 20px', marginBottom: 20,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600 }}>
              Registered Users ({users.length})
            </div>
            {selectedUserId && (
              <button onClick={() => setSelectedUserId(null)}
                style={{ fontSize: 11, fontWeight: 600, color: '#7c3aed', background: '#ede9fe', border: 'none', borderRadius: 6, padding: '3px 10px', cursor: 'pointer' }}>
                Show All Projects
              </button>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {users.map(u => {
              const isSelected = selectedUserId === u.id;
              const userProjects = projects.filter(p => p.user_id === u.id);
              const userPhotos = userProjects.reduce((sum, p) => sum + parseJSON(p.photos).length, 0);
              const roleCfg = u.role === 'designer' ? { bg: '#ede9fe', color: '#7c3aed' }
                : u.role === 'installer' ? { bg: '#dbeafe', color: '#2563eb' }
                : u.role === 'contractor' ? { bg: '#fef3c7', color: '#d97706' }
                : { bg: '#f3f4f6', color: '#6b7280' };

              return (
                <div key={u.id} style={{ borderRadius: 10, overflow: 'hidden', border: isSelected ? '1.5px solid #7c3aed' : '1px solid #e8e4dc' }}>
                  {/* User row */}
                  {editingUser === u.id ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 12px', background: '#fff', flexWrap: 'wrap' }}>
                      <input value={editUserData.name || ''} onChange={e => setEditUserData(d => ({ ...d, name: e.target.value }))}
                        placeholder="Name" style={{ width: 120, padding: '5px 8px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12 }} />
                      <input value={editUserData.email || ''} onChange={e => setEditUserData(d => ({ ...d, email: e.target.value }))}
                        placeholder="Email" style={{ width: 180, padding: '5px 8px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12 }} />
                      <input value={editUserData.phone || ''} onChange={e => setEditUserData(d => ({ ...d, phone: e.target.value }))}
                        placeholder="Phone" style={{ width: 120, padding: '5px 8px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12 }} />
                      <input value={editUserData.company || ''} onChange={e => setEditUserData(d => ({ ...d, company: e.target.value }))}
                        placeholder="Company" style={{ width: 130, padding: '5px 8px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12 }} />
                      <select value={editUserData.role || 'client'} onChange={e => setEditUserData(d => ({ ...d, role: e.target.value }))}
                        style={{ padding: '5px 8px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 11, fontWeight: 600 }}>
                        <option value="client">Client</option>
                        <option value="designer">Designer</option>
                        <option value="installer">Installer</option>
                        <option value="contractor">Contractor</option>
                      </select>
                      <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                        <button onClick={() => saveUser(u.id)} style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, padding: '5px 12px', cursor: 'pointer', fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Save size={12} /> Save
                        </button>
                        <button onClick={() => setEditingUser(null)} style={{ background: '#f5f3ef', border: '1px solid #ddd', borderRadius: 8, padding: '5px 8px', cursor: 'pointer' }}>
                          <X size={12} />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedUserId(isSelected ? null : u.id)}
                      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedUserId(isSelected ? null : u.id); } }}
                      style={{
                        width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
                        background: isSelected ? '#f5f0ff' : '#fff', border: 'none', cursor: 'pointer', textAlign: 'left',
                        transition: 'background 0.15s',
                      }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#faf8f5'; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = '#fff'; }}
                    >
                      <div style={{
                        width: 36, height: 36, borderRadius: 10, background: roleCfg.bg,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                      }}>
                        <Users size={16} style={{ color: roleCfg.color }} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{u.name}</span>
                          <span style={{
                            fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                            background: roleCfg.bg, color: roleCfg.color, textTransform: 'uppercase',
                          }}>
                            {u.role}
                          </span>
                        </div>
                        <div style={{ fontSize: 12, color: '#777', marginTop: 2, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          {u.email && <span>{u.email}</span>}
                          {u.phone && <span>· {u.phone}</span>}
                          {u.company && <span>· {u.company}</span>}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#333' }}>{userProjects.length} project{userProjects.length !== 1 ? 's' : ''}</div>
                        <div style={{ fontSize: 10, color: '#aaa' }}>{userPhotos} photo{userPhotos !== 1 ? 's' : ''}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                        <button onClick={(e) => { e.stopPropagation(); startEditUser(u); }} title="Edit"
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, borderRadius: 6, color: '#888' }}
                          onMouseEnter={e => e.currentTarget.style.background = '#f0ede8'}
                          onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                          <Pencil size={13} />
                        </button>
                        <button onClick={(e) => { e.stopPropagation(); deleteUser(u.id, u.name); }} title="Delete"
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 6, borderRadius: 6, color: '#dc2626' }}
                          onMouseEnter={e => e.currentTarget.style.background = '#fef2f2'}
                          onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Expanded user detail — show their projects & uploads */}
                  {isSelected && !editingUser && (
                    <div style={{ borderTop: '1px solid #ece8e0', background: '#faf8f5', padding: '14px 16px' }}>
                      {userProjects.length === 0 ? (
                        <div style={{ fontSize: 12, color: '#999', textAlign: 'center', padding: '16px 0' }}>
                          No projects submitted yet
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                          {userProjects.map(proj => {
                            const photos = parseJSON(proj.photos);
                            const measurements = parseJSON(proj.measurements);
                            const statusCfg = STATUS_COLORS[proj.status] || STATUS_COLORS.draft;
                            return (
                              <div key={proj.id} style={{ background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', overflow: 'hidden' }}>
                                {/* Project header */}
                                <div style={{ padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
                                  <FolderOpen size={16} style={{ color: '#7c3aed', flexShrink: 0 }} />
                                  <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>
                                      {proj.name || proj.intake_code}
                                    </div>
                                    <div style={{ fontSize: 11, color: '#888', marginTop: 1 }}>
                                      {proj.address || 'No address'} · {TREATMENT_LABELS[proj.treatment || ''] || proj.treatment || '—'}
                                      {proj.style && ` · ${proj.style}`}
                                    </div>
                                  </div>
                                  <span style={{
                                    fontSize: 9, fontWeight: 700, padding: '3px 8px', borderRadius: 6,
                                    background: statusCfg.bg, color: statusCfg.color,
                                  }}>{statusCfg.label}</span>
                                  <span style={{ fontSize: 10, color: '#bbb', fontFamily: 'monospace' }}>
                                    {new Date(proj.created_at).toLocaleDateString()}
                                  </span>
                                </div>

                                {/* Project details */}
                                <div style={{ padding: '0 14px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                                  {/* Notes / Scope */}
                                  {(proj.notes || proj.scope) && (
                                    <div style={{ fontSize: 12, color: '#555', lineHeight: 1.5, padding: '8px 10px', background: '#faf9f7', borderRadius: 8 }}>
                                      {proj.scope && <div><strong>Scope:</strong> {proj.scope}</div>}
                                      {proj.notes && <div><strong>Notes:</strong> {proj.notes}</div>}
                                    </div>
                                  )}

                                  {/* Measurements */}
                                  {measurements.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 4 }}>
                                        Measurements ({measurements.length})
                                      </div>
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                        {measurements.map((m: any, i: number) => (
                                          <div key={i} style={{
                                            padding: '6px 10px', background: '#eff6ff', borderRadius: 6, fontSize: 11, color: '#2563eb', fontWeight: 600,
                                          }}>
                                            <Ruler size={11} style={{ display: 'inline', marginRight: 4 }} />
                                            {m.room || m.location || `Window ${i + 1}`}: {m.width || '?'}″ × {m.height || '?'}″
                                            {m.mount_type && ` (${m.mount_type})`}
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Photos */}
                                  {photos.length > 0 && (
                                    <div>
                                      <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 4 }}>
                                        Photos ({photos.length})
                                      </div>
                                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(80px, 1fr))', gap: 6 }}>
                                        {photos.map((photo: any, i: number) => (
                                          <div
                                            key={i}
                                            onClick={() => setViewingPhoto({
                                              url: `${API.replace('/api/v1', '')}${photo.path}`,
                                              name: photo.original_name || `Photo ${i + 1}`,
                                              projectName: proj.name || proj.intake_code,
                                            })}
                                            style={{
                                              position: 'relative', aspectRatio: '1', borderRadius: 8,
                                              overflow: 'hidden', background: '#eee', cursor: 'pointer',
                                              border: '1px solid #ddd',
                                            }}
                                          >
                                            <img
                                              src={`${API.replace('/api/v1', '')}${photo.path}`}
                                              alt={photo.original_name || 'Upload'}
                                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                            />
                                            <div style={{
                                              position: 'absolute', bottom: 0, left: 0, right: 0,
                                              background: 'linear-gradient(transparent, rgba(0,0,0,0.6))',
                                              padding: '12px 4px 3px', textAlign: 'center',
                                              fontSize: 8, color: '#fff', fontWeight: 700,
                                            }}>
                                              {photo.original_name || `Photo ${i + 1}`}
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {/* Actions */}
                                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                                    <button
                                      onClick={() => setExpandedProject(expandedProject === proj.id ? null : proj.id)}
                                      style={{
                                        fontSize: 11, fontWeight: 600, padding: '5px 12px', borderRadius: 8,
                                        border: expandedProject === proj.id ? '1px solid #7c3aed' : '1px solid #ece8e0',
                                        background: expandedProject === proj.id ? '#f5f0ff' : '#fff',
                                        color: expandedProject === proj.id ? '#7c3aed' : '#555', cursor: 'pointer',
                                      }}
                                    >
                                      <Eye size={11} style={{ display: 'inline', marginRight: 4 }} />
                                      {expandedProject === proj.id ? 'Hide Details' : 'View Full Details'}
                                    </button>
                                    <button
                                      onClick={() => sendToWorkroom(proj.id, 'workroom')}
                                      disabled={sendingToWorkroom === proj.id}
                                      style={{
                                        fontSize: 11, fontWeight: 700, padding: '5px 12px', borderRadius: 8,
                                        border: 'none', background: '#16a34a', color: '#fff', cursor: 'pointer',
                                        opacity: sendingToWorkroom === proj.id ? 0.5 : 1,
                                      }}
                                    >
                                      <Scissors size={11} style={{ display: 'inline', marginRight: 4 }} />
                                      {sendingToWorkroom === proj.id ? 'Sending...' : 'Send to Workroom'}
                                    </button>
                                    <button
                                      onClick={() => sendToWorkroom(proj.id, 'woodcraft')}
                                      disabled={sendingToWorkroom === proj.id}
                                      style={{
                                        fontSize: 11, fontWeight: 700, padding: '5px 12px', borderRadius: 8,
                                        border: 'none', background: '#ca8a04', color: '#fff', cursor: 'pointer',
                                        opacity: sendingToWorkroom === proj.id ? 0.5 : 1,
                                      }}
                                    >
                                      <TreePine size={11} style={{ display: 'inline', marginRight: 4 }} />
                                      Send to WoodCraft
                                    </button>
                                  </div>

                                  {/* Expanded full details */}
                                  {expandedProject === proj.id && (() => {
                                    const rooms = parseJSON(proj.rooms);
                                    const msgs = parseJSON(proj.messages);
                                    return (
                                      <div style={{ marginTop: 8, borderTop: '1px solid #ece8e0', paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                                        {/* Quote PDF */}
                                        {proj.quote_pdf && (
                                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: '#fdf8eb', borderRadius: 8, border: '1px solid #f0e6c0' }}>
                                            <FileText size={14} style={{ color: '#b8960c' }} />
                                            <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', flex: 1 }}>Quote PDF Ready</span>
                                            <a href={`${API.replace('/api/v1', '')}${proj.quote_pdf}`} target="_blank" rel="noopener noreferrer"
                                              style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textDecoration: 'none', padding: '3px 8px', background: '#fff', borderRadius: 6, border: '1px solid #f0e6c0' }}>
                                              View PDF
                                            </a>
                                          </div>
                                        )}

                                        {/* Selected proposal */}
                                        {proj.selected_proposal && (
                                          <div style={{ padding: '6px 10px', background: '#dcfce7', borderRadius: 6, fontSize: 11, color: '#16a34a', fontWeight: 600 }}>
                                            Selected Proposal: {proj.selected_proposal}
                                          </div>
                                        )}

                                        {/* Rooms */}
                                        {rooms.length > 0 && (
                                          <div>
                                            <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 4 }}>
                                              Rooms ({rooms.length})
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                              {rooms.map((room: any, ri: number) => (
                                                <div key={ri} style={{ padding: '6px 10px', background: '#f5f3ef', borderRadius: 6, fontSize: 11, color: '#333' }}>
                                                  <strong>{room.name || `Room ${ri + 1}`}</strong>
                                                  {room.windows && ` — ${room.windows.length || 0} window(s)`}
                                                  {room.treatment_type && ` · ${room.treatment_type}`}
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}

                                        {/* Messages */}
                                        {msgs.length > 0 && (
                                          <div>
                                            <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 4 }}>
                                              Messages ({msgs.length})
                                            </div>
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 200, overflowY: 'auto' }}>
                                              {msgs.map((msg: any, mi: number) => (
                                                <div key={mi} style={{
                                                  padding: '6px 10px', borderRadius: 6, fontSize: 11, lineHeight: 1.4,
                                                  background: msg.from === 'client' ? '#fdf8eb' : '#f5f3ef',
                                                  borderLeft: msg.from === 'client' ? '3px solid #b8960c' : '3px solid #ccc',
                                                }}>
                                                  <div style={{ fontWeight: 600, color: '#333', marginBottom: 2 }}>
                                                    {msg.from === 'client' ? u.name : 'Empire Team'}
                                                    {msg.timestamp && <span style={{ fontWeight: 400, color: '#aaa', marginLeft: 6, fontSize: 9 }}>{new Date(msg.timestamp).toLocaleString()}</span>}
                                                  </div>
                                                  <div style={{ color: '#555' }}>{typeof msg.text === 'string' ? msg.text : JSON.stringify(msg.text)}</div>
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}

                                        {/* Full data dump */}
                                        <div style={{ fontSize: 10, color: '#bbb', marginTop: 4 }}>
                                          ID: {proj.id} · Code: {proj.intake_code} · Created: {new Date(proj.created_at).toLocaleString()}
                                          {proj.updated_at && ` · Updated: ${new Date(proj.updated_at).toLocaleString()}`}
                                        </div>
                                      </div>
                                    );
                                  })()}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filter Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <span style={{ fontSize: 11, color: '#999', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Filter:
        </span>
        {['all', 'draft', 'submitted', 'quote-ready', 'approved', 'in-production', 'installed'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: '4px 10px', fontSize: 11, fontWeight: filter === f ? 700 : 500,
              borderRadius: 6, border: '1px solid',
              borderColor: filter === f ? '#7c3aed' : '#ece8e0',
              background: filter === f ? '#ede9fe' : '#faf9f7',
              color: filter === f ? '#7c3aed' : '#888',
              cursor: 'pointer',
            }}
          >
            {f === 'all' ? 'All' : (STATUS_COLORS[f]?.label || f)}
          </button>
        ))}
      </div>

      {/* Loading / Error / Empty */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 40, color: '#888', fontSize: 14 }}>
          Loading intake data...
        </div>
      )}
      {error && (
        <div style={{
          background: '#fef3c7', border: '1px solid #fde68a', borderRadius: 12,
          padding: '14px 18px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <AlertCircle size={16} style={{ color: '#d97706' }} />
          <span style={{ fontSize: 13, color: '#92400e' }}>{error}</span>
        </div>
      )}
      {!loading && filteredProjects.length === 0 && !error && (
        <div style={{
          textAlign: 'center', padding: 40, background: '#faf9f7',
          border: '1px solid #ece8e0', borderRadius: 14,
        }}>
          <FolderOpen size={32} style={{ color: '#ccc', marginBottom: 8 }} />
          <div style={{ fontSize: 14, color: '#888' }}>No intake projects yet</div>
          <div style={{ fontSize: 12, color: '#bbb', marginTop: 4 }}>
            Designers and installers submit projects through the intake portal
          </div>
        </div>
      )}

      {/* Project List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {filteredProjects.map(project => {
          const photos = parseJSON(project.photos);
          const measurements = parseJSON(project.measurements);
          const messages = parseJSON(project.messages);
          const scans = parseJSON(project.scans);
          const isExpanded = expandedProject === project.id;
          const statusCfg = STATUS_COLORS[project.status] || STATUS_COLORS.draft;

          return (
            <div
              key={project.id}
              style={{
                background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14,
                overflow: 'hidden', transition: 'box-shadow 0.15s',
                boxShadow: isExpanded ? '0 4px 16px rgba(0,0,0,0.06)' : 'none',
              }}
            >
              {/* Project Header (clickable) */}
              <button
                onClick={() => toggleProject(project.id)}
                style={{
                  width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                  padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 12,
                  textAlign: 'left',
                }}
              >
                <div style={{
                  width: 36, height: 36, borderRadius: 10, background: statusCfg.bg,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: statusCfg.color, fontWeight: 800, fontSize: 13, flexShrink: 0,
                }}>
                  {project.intake_code?.split('-')[2] || '#'}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>
                      {project.name}
                    </span>
                    <span style={{
                      fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 10,
                      background: statusCfg.bg, color: statusCfg.color,
                    }}>
                      {statusCfg.label}
                    </span>
                  </div>
                  <div style={{ fontSize: 11, color: '#888', marginTop: 2, display: 'flex', gap: 12 }}>
                    <span>{project.intake_code}</span>
                    {project.user_name && <span>by {project.user_name}</span>}
                    {project.address && <span>· {project.address}</span>}
                  </div>
                </div>
                {/* Quick stats */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                  {project.treatment && (
                    <span style={{
                      fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 6,
                      background: '#f5f2ed', color: '#666',
                    }}>
                      {TREATMENT_LABELS[project.treatment] || project.treatment}
                    </span>
                  )}
                  {photos.length > 0 && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#888' }}>
                      <Image size={12} /> {photos.length}
                    </span>
                  )}
                  {measurements.length > 0 && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#888' }}>
                      <Ruler size={12} /> {measurements.length}
                    </span>
                  )}
                  {messages.length > 0 && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 11, color: '#888' }}>
                      <MessageSquare size={12} /> {messages.length}
                    </span>
                  )}
                  <span style={{ fontSize: 11, color: '#aaa' }}>
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                  {isExpanded ? <ChevronUp size={16} style={{ color: '#999' }} /> : <ChevronDown size={16} style={{ color: '#999' }} />}
                </div>
              </button>

              {/* Expanded Detail */}
              {isExpanded && (
                <div style={{ borderTop: '1px solid #ece8e0', padding: '16px 18px' }}>
                  {/* Info Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
                    {[
                      { label: 'Treatment', value: TREATMENT_LABELS[project.treatment || ''] || project.treatment || '—' },
                      { label: 'Style', value: project.style || '—' },
                      { label: 'Scope', value: project.scope?.replace('-', ' ') || '—' },
                      { label: 'Address', value: project.address || '—' },
                    ].map(item => (
                      <div key={item.label} style={{
                        padding: '10px 12px', background: '#f5f2ed', borderRadius: 8,
                      }}>
                        <div style={{ fontSize: 10, color: '#999', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 3, fontWeight: 600 }}>
                          {item.label}
                        </div>
                        <div style={{ fontSize: 13, color: '#333', fontWeight: 500, textTransform: 'capitalize' }}>
                          {item.value}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Client Info */}
                  {(project.user_name || project.user_email) && (
                    <div style={{
                      padding: '10px 14px', background: '#ede9fe', borderRadius: 8,
                      marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10,
                    }}>
                      <Users size={14} style={{ color: '#7c3aed' }} />
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#5b21b6' }}>
                        {project.user_name}
                      </span>
                      {project.user_email && (
                        <span style={{ fontSize: 12, color: '#7c3aed' }}>
                          {project.user_email}
                        </span>
                      )}
                      {project.user_company && (
                        <span style={{ fontSize: 12, color: '#8b5cf6' }}>
                          · {project.user_company}
                        </span>
                      )}
                      {project.user_role && (
                        <span style={{
                          fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                          background: '#fff', color: '#7c3aed', textTransform: 'uppercase', marginLeft: 4,
                        }}>
                          {project.user_role}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Photos */}
                  {photos.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, fontWeight: 600 }}>
                        Photos ({photos.length})
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
                        {photos.map((photo: any, i: number) => (
                          <div
                            key={i}
                            onClick={() => setViewingPhoto({
                              url: `${API.replace('/api/v1', '')}${photo.path}`,
                              name: photo.original_name || `Photo ${i + 1}`,
                              projectName: project.name || project.id,
                            })}
                            style={{
                              position: 'relative', aspectRatio: '1', borderRadius: 8,
                              overflow: 'hidden', background: '#eee', border: '1px solid #ddd',
                              cursor: 'pointer',
                            }}
                          >
                            <img
                              src={`${API.replace('/api/v1', '')}${photo.path}`}
                              alt={photo.original_name || `Photo ${i + 1}`}
                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                            />
                            <div style={{
                              position: 'absolute', bottom: 0, left: 0, right: 0,
                              background: 'linear-gradient(transparent, rgba(0,0,0,0.6))',
                              padding: '16px 6px 4px', fontSize: 9, color: '#fff',
                              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                            }}>
                              {photo.original_name || `Photo ${i + 1}`}
                            </div>
                            <div style={{
                              position: 'absolute', top: 4, right: 4,
                              background: 'rgba(0,0,0,0.5)', borderRadius: 6, padding: '2px 6px',
                              fontSize: 8, color: '#fff', fontWeight: 700,
                            }}>
                              CLICK TO VIEW
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 3D Scans */}
                  {scans.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, fontWeight: 600 }}>
                        3D Scans ({scans.length})
                      </div>
                      <div style={{ display: 'flex', gap: 8 }}>
                        {scans.map((scan: any, i: number) => (
                          <div key={i} style={{
                            padding: '8px 14px', background: '#dcfce7', borderRadius: 8,
                            fontSize: 12, color: '#16a34a', fontWeight: 600,
                            display: 'flex', alignItems: 'center', gap: 6,
                          }}>
                            <Maximize2 size={12} />
                            {scan.original_name || `Scan ${i + 1}`}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Measurements */}
                  {measurements.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, fontWeight: 600 }}>
                        Measurements ({measurements.length})
                      </div>
                      <div style={{
                        border: '1px solid #ece8e0', borderRadius: 8, overflow: 'hidden',
                      }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                          <thead>
                            <tr style={{ background: '#f5f2ed' }}>
                              <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Room / Window</th>
                              <th style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 600, color: '#666' }}>Width</th>
                              <th style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 600, color: '#666' }}>Height</th>
                              <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Reference</th>
                            </tr>
                          </thead>
                          <tbody>
                            {measurements.map((m: any, i: number) => (
                              <tr key={i} style={{ borderTop: '1px solid #ece8e0' }}>
                                <td style={{ padding: '8px 12px', color: '#333' }}>{m.room || `Window ${i + 1}`}</td>
                                <td style={{ padding: '8px 12px', textAlign: 'center', color: '#333', fontWeight: 600 }}>{m.width}&quot;</td>
                                <td style={{ padding: '8px 12px', textAlign: 'center', color: '#333', fontWeight: 600 }}>{m.height}&quot;</td>
                                <td style={{ padding: '8px 12px', color: '#888', textTransform: 'capitalize' }}>{m.reference?.replace('-', ' ') || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {project.notes && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, fontWeight: 600 }}>
                        Notes
                      </div>
                      <div style={{
                        padding: '10px 14px', background: '#f5f2ed', borderRadius: 8,
                        fontSize: 13, color: '#444', lineHeight: 1.5,
                      }}>
                        {project.notes}
                      </div>
                    </div>
                  )}

                  {/* Messages */}
                  {messages.length > 0 && (
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ fontSize: 11, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8, fontWeight: 600 }}>
                        Messages ({messages.length})
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {messages.map((msg: any, i: number) => (
                          <div key={i} style={{
                            padding: '8px 12px', background: msg.role === 'admin' ? '#ede9fe' : '#f5f2ed',
                            borderRadius: 8, fontSize: 12,
                          }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                              <span style={{ fontWeight: 700, color: msg.role === 'admin' ? '#7c3aed' : '#333' }}>
                                {msg.from || 'Unknown'}
                              </span>
                              <span style={{ fontSize: 10, color: '#aaa' }}>
                                {new Date(msg.timestamp).toLocaleString()}
                              </span>
                            </div>
                            <div style={{ color: '#555', lineHeight: 1.4 }}>{msg.content}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Quote PDF */}
                  {project.quote_pdf && (
                    <div style={{
                      padding: '10px 14px', background: '#dcfce7', borderRadius: 8,
                      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16,
                    }}>
                      <FileText size={14} style={{ color: '#16a34a' }} />
                      <span style={{ fontSize: 13, fontWeight: 600, color: '#16a34a' }}>Quote PDF Ready</span>
                      {project.selected_proposal && (
                        <span style={{ fontSize: 11, color: '#059669', marginLeft: 8 }}>
                          Selected: {project.selected_proposal}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <a
                      href={`/intake/project/${project.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding: '8px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                        background: '#7c3aed', color: '#fff', textDecoration: 'none',
                        display: 'flex', alignItems: 'center', gap: 6,
                      }}
                    >
                      <Eye size={13} /> View Full Project
                    </a>
                    {(project.status === 'submitted' || project.status === 'draft') && (
                      <>
                        <button
                          onClick={() => sendToWorkroom(project.id, 'workroom')}
                          disabled={sendingToWorkroom === project.id}
                          style={{
                            padding: '8px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                            background: '#16a34a', color: '#fff', border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 6,
                            opacity: sendingToWorkroom === project.id ? 0.6 : 1,
                          }}
                        >
                          {sendingToWorkroom === project.id
                            ? <><Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> Creating Quote...</>
                            : <><Scissors size={13} /> Send to Workroom</>
                          }
                        </button>
                        <button
                          onClick={() => sendToWorkroom(project.id, 'woodcraft')}
                          disabled={sendingToWorkroom === project.id}
                          style={{
                            padding: '8px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                            background: '#ca8a04', color: '#fff', border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 6,
                            opacity: sendingToWorkroom === project.id ? 0.6 : 1,
                          }}
                        >
                          <TreePine size={13} /> Send to WoodCraft
                        </button>
                      </>
                    )}
                    {project.status === 'quote-ready' && (
                      <button
                        onClick={() => onNavigate?.('workroom', 'dashboard', 'quotes')}
                        style={{
                          padding: '8px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8,
                          background: '#16a34a', color: '#fff', border: 'none', cursor: 'pointer',
                          display: 'flex', alignItems: 'center', gap: 6,
                        }}
                      >
                        <ExternalLink size={13} /> Open in Workroom
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      </>
      )}

      {/* Photo Lightbox Popup */}
      {viewingPhoto && (
        <div
          className="fixed inset-0 z-[400] flex items-center justify-center"
          onClick={() => setViewingPhoto(null)}
        >
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div
            onClick={e => e.stopPropagation()}
            style={{
              position: 'relative', maxWidth: '90vw', maxHeight: '90vh',
              background: '#fff', borderRadius: 16, overflow: 'hidden',
              boxShadow: '0 25px 80px rgba(0,0,0,0.4)',
              display: 'flex', flexDirection: 'column',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '12px 20px', borderBottom: '1px solid #ece8e0',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#333' }}>{viewingPhoto.name}</div>
                <div style={{ fontSize: 11, color: '#999' }}>Project: {viewingPhoto.projectName}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <a
                  href={viewingPhoto.url}
                  download
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                    borderRadius: 8, fontSize: 12, fontWeight: 600, color: '#555',
                    border: '1px solid #ece8e0', background: '#faf9f7', textDecoration: 'none',
                  }}
                >
                  <Download size={12} /> Download
                </a>
                <a
                  href={viewingPhoto.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                    borderRadius: 8, fontSize: 12, fontWeight: 600, color: '#fff',
                    background: '#7c3aed', textDecoration: 'none',
                  }}
                >
                  <Eye size={12} /> Full Size
                </a>
                <button
                  onClick={() => setViewingPhoto(null)}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    width: 32, height: 32, borderRadius: 8, border: '1px solid #ece8e0',
                    background: '#faf9f7', cursor: 'pointer',
                  }}
                >
                  <X size={16} style={{ color: '#666' }} />
                </button>
              </div>
            </div>
            {/* Image */}
            <div style={{ padding: 16, overflow: 'auto', maxHeight: 'calc(90vh - 60px)' }}>
              <img
                src={viewingPhoto.url}
                alt={viewingPhoto.name}
                style={{ maxWidth: '100%', maxHeight: '75vh', borderRadius: 8, display: 'block', margin: '0 auto' }}
              />
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
