'use client';
import { ExternalLink, Play, MapPin, Share2 } from 'lucide-react';
import type { WebPreview } from './ContentAnalyzer';

interface Props {
  previews: WebPreview[];
  inline?: boolean;
}

function extractYoutubeId(url: string): string | null {
  const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '');
  } catch {
    return url;
  }
}

function PreviewCard({ preview, inline }: { preview: WebPreview; inline?: boolean }) {
  const domain = extractDomain(preview.url);

  if (preview.type === 'youtube') {
    const videoId = extractYoutubeId(preview.url);
    if (videoId) {
      return (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <div style={{ position: 'relative', paddingBottom: inline ? '40%' : '56.25%', height: 0 }}>
            <iframe
              src={`https://www.youtube-nocookie.com/embed/${videoId}`}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              title="YouTube video"
            />
          </div>
          <div className="px-3 py-1.5 flex items-center justify-between" style={{ background: 'var(--raised)' }}>
            <span className="text-[10px] font-medium flex items-center gap-1" style={{ color: '#ef4444' }}>
              <Play className="w-3 h-3" /> YouTube
            </span>
            <a
              href={preview.url}
              target="_blank"
              rel="noreferrer"
              className="text-[10px] flex items-center gap-1 hover:underline"
              style={{ color: 'var(--text-muted)' }}
            >
              Open <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      );
    }
  }

  // Standard link preview card
  const icon = preview.type === 'map' ? <MapPin className="w-4 h-4" style={{ color: '#22c55e' }} /> :
               preview.type === 'social' ? <Share2 className="w-4 h-4" style={{ color: '#3b82f6' }} /> :
               <ExternalLink className="w-4 h-4" style={{ color: 'var(--gold)' }} />;

  const typeLabel = preview.type === 'map' ? 'Map' :
                    preview.type === 'social' ? 'Social' : 'Link';

  return (
    <a
      href={preview.url}
      target="_blank"
      rel="noreferrer"
      className="flex items-center gap-3 p-3 rounded-xl transition hover:brightness-110 group"
      style={{
        background: 'var(--raised)',
        border: '1px solid var(--border)',
        textDecoration: 'none',
      }}
    >
      <div
        className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: 'var(--elevated)' }}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium truncate group-hover:underline" style={{ color: 'var(--text-primary)' }}>
          {preview.title || domain}
        </p>
        <p className="text-[10px] truncate" style={{ color: 'var(--text-muted)' }}>
          {domain}
        </p>
      </div>
      <span
        className="text-[8px] px-1.5 py-0.5 rounded-full font-medium shrink-0"
        style={{
          background: preview.type === 'youtube' ? 'rgba(239,68,68,0.1)' :
                      preview.type === 'map' ? 'rgba(34,197,94,0.1)' :
                      preview.type === 'social' ? 'rgba(59,130,246,0.1)' :
                      'var(--gold-pale)',
          color: preview.type === 'youtube' ? '#ef4444' :
                 preview.type === 'map' ? '#22c55e' :
                 preview.type === 'social' ? '#3b82f6' :
                 'var(--gold)',
        }}
      >
        {typeLabel}
      </span>
    </a>
  );
}

export default function WebPreviewCanvas({ previews, inline }: Props) {
  if (previews.length === 0) return null;

  return (
    <div className={`flex flex-col gap-2 ${inline ? 'my-2' : ''}`}>
      {previews.map((p, i) => (
        <PreviewCard key={i} preview={p} inline={inline} />
      ))}
    </div>
  );
}
