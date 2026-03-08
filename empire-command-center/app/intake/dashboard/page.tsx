'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, FolderOpen } from 'lucide-react';
import Link from 'next/link';
import IntakeNav from '../../components/intake/IntakeNav';
import ProjectCard from '../../components/intake/ProjectCard';
import { intakeFetch, getToken } from '../../lib/intake-auth';

export default function IntakeDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getToken()) { router.push('/intake/login'); return; }

    const load = async () => {
      try {
        const [me, proj] = await Promise.all([
          intakeFetch('/me'),
          intakeFetch('/projects'),
        ]);
        setUser(me);
        setProjects(proj);
      } catch (_err) {
        router.push('/intake/login');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#faf9f7] flex items-center justify-center">
        <div className="text-sm text-[#aaa]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#faf9f7]">
      <IntakeNav user={user} />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold text-[#1a1a1a]">My Projects</h1>
          <Link
            href="/intake/project/new"
            className="px-4 py-2.5 text-xs font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors flex items-center gap-1.5"
          >
            <Plus size={14} /> New Project
          </Link>
        </div>

        {projects.length === 0 ? (
          <div className="bg-white border border-[#e5e0d8] rounded-xl p-12 text-center">
            <FolderOpen size={40} className="mx-auto text-[#ddd] mb-3" />
            <h3 className="text-sm font-semibold text-[#1a1a1a] mb-1">No projects yet</h3>
            <p className="text-xs text-[#777] mb-4">Submit your first project to get a custom quote in 24 hours.</p>
            <Link
              href="/intake/project/new"
              className="inline-flex items-center gap-1.5 px-6 py-2.5 text-xs font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors"
            >
              <Plus size={14} /> Start Your First Project
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
