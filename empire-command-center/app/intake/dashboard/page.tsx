'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, FolderOpen, Camera, Clock, CheckCircle2, Truck, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import IntakeNav from '../../components/intake/IntakeNav';
import ProjectCard from '../../components/intake/ProjectCard';
import { intakeFetch, getToken } from '../../lib/intake-auth';

const STATUS_STEPS = [
  { key: 'draft', label: 'Draft', icon: FolderOpen, color: '#888' },
  { key: 'submitted', label: 'Submitted', icon: Clock, color: '#2563eb' },
  { key: 'quote-ready', label: 'Quote Ready', icon: Camera, color: '#b8960c' },
  { key: 'approved', label: 'Approved', icon: CheckCircle2, color: '#16a34a' },
  { key: 'in-production', label: 'In Production', icon: Truck, color: '#7c3aed' },
  { key: 'installed', label: 'Installed', icon: CheckCircle2, color: '#059669' },
];

export default function IntakeDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const [me, proj] = await Promise.all([
        intakeFetch('/me'),
        intakeFetch('/projects'),
      ]);
      setUser(me);
      const projList = proj?.projects || proj;
      setProjects(Array.isArray(projList) ? projList : []);
    } catch (_err) {
      router.push('/intake/login');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (!getToken()) { router.push('/intake/login'); return; }
    load();
  }, [router]);

  const refresh = () => { setRefreshing(true); load(); };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f2ed] flex items-center justify-center">
        <div className="text-[12px] text-[#999]">Loading...</div>
      </div>
    );
  }

  const totalPhotos = projects.reduce((sum, p) => sum + (Array.isArray(p.photos) ? p.photos.length : 0), 0);

  return (
    <div className="min-h-screen bg-[#f5f2ed]">
      <IntakeNav user={user} />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-lg font-bold text-[#1a1a1a]">My Projects</h1>
            {user && (
              <p className="text-[11px] text-[#999] mt-0.5">
                Welcome back, {user.name || user.email}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              disabled={refreshing}
              className="px-3 py-2.5 min-h-[44px] text-sm font-medium text-[#888] border border-[#ece8e0] bg-[#faf9f7] rounded-[10px] hover:bg-[#f0ede8] transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} /> <span className="hidden sm:inline">Refresh</span>
            </button>
            <Link
              href="/intake/project/new"
              className="px-4 py-2.5 min-h-[44px] text-sm font-bold bg-[#1a1a1a] text-white rounded-[10px] hover:bg-[#333] transition-colors flex items-center gap-1.5"
            >
              <Plus size={14} /> New Project
            </Link>
          </div>
        </div>

        {/* Stats row */}
        {projects.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[12px] p-3.5 text-center">
              <div className="text-[20px] font-bold text-[#1a1a1a]">{projects.length}</div>
              <div className="text-xs text-[#999] font-medium mt-0.5">Projects</div>
            </div>
            <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[12px] p-3.5 text-center">
              <div className="text-[20px] font-bold text-[#2563eb]">
                {projects.filter(p => p.status === 'submitted').length}
              </div>
              <div className="text-xs text-[#999] font-medium mt-0.5">Pending</div>
            </div>
            <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[12px] p-3.5 text-center">
              <div className="text-[20px] font-bold text-[#b8960c]">
                {projects.filter(p => p.status === 'quote-ready').length}
              </div>
              <div className="text-xs text-[#999] font-medium mt-0.5">Quotes Ready</div>
            </div>
            <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[12px] p-3.5 text-center">
              <div className="text-[20px] font-bold text-[#7c3aed]">{totalPhotos}</div>
              <div className="text-xs text-[#999] font-medium mt-0.5">Photos</div>
            </div>
          </div>
        )}

        {/* Projects */}
        {projects.length === 0 ? (
          <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-12 text-center">
            <FolderOpen size={36} className="mx-auto text-[#d5d0c8] mb-3" />
            <h3 className="text-[13px] font-semibold text-[#1a1a1a] mb-1">No projects yet</h3>
            <p className="text-[11px] text-[#888] mb-5">Submit your first project to get a custom quote in 24 hours.</p>
            <Link
              href="/intake/project/new"
              className="inline-flex items-center gap-1.5 px-6 py-2.5 text-[11px] font-bold bg-[#b8960c] text-white rounded-[10px] hover:bg-[#a3850b] transition-colors"
            >
              <Plus size={13} /> Start Your First Project
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((p: any) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
