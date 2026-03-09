'use client';
import { MapPin, Camera, Calendar, ChevronRight } from 'lucide-react';
import Link from 'next/link';

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  draft: { label: 'Draft', color: '#888', bg: '#f5f3ef' },
  submitted: { label: 'Submitted', color: '#2563eb', bg: '#dbeafe' },
  'quote-ready': { label: 'Quote Ready', color: '#b8960c', bg: '#fdf8eb' },
  approved: { label: 'Approved', color: '#16a34a', bg: '#dcfce7' },
  'in-production': { label: 'In Production', color: '#7c3aed', bg: '#ede9fe' },
  installed: { label: 'Installed', color: '#16a34a', bg: '#dcfce7' },
};

export default function ProjectCard({ project }: { project: any }) {
  const status = statusConfig[project.status] || statusConfig.draft;
  const photos = project.photos || [];
  const date = new Date(project.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <Link href={`/intake/project/${project.id}`}>
      <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-4 hover:border-[#d5d0c8] hover:shadow-[0_2px_12px_rgba(0,0,0,0.04)] hover:-translate-y-[1px] transition-all cursor-pointer group">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[9px] font-bold px-2.5 py-0.5 rounded-md" style={{ color: status.color, background: status.bg }}>
                {status.label}
              </span>
              <span className="text-[9px] text-[#c5c0b8] font-medium">{project.intake_code}</span>
            </div>
            <h3 className="text-[13px] font-semibold text-[#1a1a1a] truncate">{project.name}</h3>
            {project.address && (
              <div className="flex items-center gap-1 text-[11px] text-[#888] mt-1">
                <MapPin size={11} /> {project.address}
              </div>
            )}
            <div className="flex items-center gap-3 mt-2 text-[10px] text-[#c5c0b8]">
              {photos.length > 0 && (
                <span className="flex items-center gap-1"><Camera size={10} /> {photos.length} photos</span>
              )}
              {project.treatment && <span className="capitalize">{project.treatment}</span>}
              <span className="flex items-center gap-1"><Calendar size={10} /> {date}</span>
            </div>
          </div>
          <ChevronRight size={15} className="text-[#d5d0c8] group-hover:text-[#b8960c] transition-colors mt-1 flex-shrink-0" />
        </div>
      </div>
    </Link>
  );
}
