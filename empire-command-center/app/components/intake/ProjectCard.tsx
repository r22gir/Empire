'use client';
import { MapPin, Camera, Calendar, ChevronRight } from 'lucide-react';
import Link from 'next/link';

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  draft: { label: 'Draft', color: '#777', bg: '#f5f3ef' },
  submitted: { label: 'Submitted', color: '#2563eb', bg: '#dbeafe' },
  'quote-ready': { label: 'Quote Ready', color: '#c9a84c', bg: '#fdf8eb' },
  approved: { label: 'Approved', color: '#16a34a', bg: '#dcfce7' },
  'in-production': { label: 'In Production', color: '#7c3aed', bg: '#ede9fe' },
  installed: { label: 'Installed', color: '#16a34a', bg: '#dcfce7' },
};

export default function ProjectCard({ project }: { project: any }) {
  const status = statusConfig[project.status] || statusConfig.draft;
  const photos = project.photos || [];
  const rooms = project.rooms || [];
  const date = new Date(project.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <Link href={`/intake/project/${project.id}`}>
      <div className="bg-white border border-[#e5e0d8] rounded-xl p-4 hover:border-[#c9a84c] hover:shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all cursor-pointer group">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded" style={{ color: status.color, background: status.bg }}>
                {status.label}
              </span>
              <span className="text-[10px] text-[#aaa]">{project.intake_code}</span>
            </div>
            <h3 className="text-sm font-semibold text-[#1a1a1a] truncate">{project.name}</h3>
            {project.address && (
              <div className="flex items-center gap-1 text-[11px] text-[#777] mt-1">
                <MapPin size={12} /> {project.address}
              </div>
            )}
            <div className="flex items-center gap-3 mt-2 text-[10px] text-[#aaa]">
              {photos.length > 0 && (
                <span className="flex items-center gap-1"><Camera size={11} /> {photos.length} photos</span>
              )}
              {project.treatment && <span>{project.treatment}</span>}
              <span className="flex items-center gap-1"><Calendar size={11} /> {date}</span>
            </div>
          </div>
          <ChevronRight size={16} className="text-[#ccc] group-hover:text-[#c9a84c] transition-colors mt-1 flex-shrink-0" />
        </div>
      </div>
    </Link>
  );
}
