'use client';
import { type ContentPost, type PostStatus } from '@/lib/deskData';
import { Calendar, Eye, Hash, StickyNote, Edit3, Send } from 'lucide-react';
import { StatusBadge } from '../shared';

const STATUS_COLOR: Record<PostStatus, string> = {
  draft: 'var(--text-muted)', scheduled: '#8B5CF6', published: '#22c55e',
};

const PLATFORM_ICON: Record<string, string> = {
  Instagram: '📸', Facebook: '👤', Pinterest: '📌', TikTok: '🎵', Blog: '📝',
};

interface PostDetailProps {
  post: ContentPost;
}

export default function PostDetail({ post }: PostDetailProps) {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{PLATFORM_ICON[post.platform] || '📄'}</span>
          <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{post.platform}</span>
        </div>
        <StatusBadge label={post.status} color={STATUS_COLOR[post.status]} />
      </div>

      {/* Title */}
      <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{post.title}</p>

      {/* Content preview */}
      <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
        <p className="text-[10px] font-semibold mb-1.5" style={{ color: 'var(--gold)' }}>Content</p>
        <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{post.content}</p>
      </div>

      {/* Hashtags */}
      {post.hashtags.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Hash className="w-3 h-3" style={{ color: 'var(--purple)' }} />
            <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Hashtags</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {post.hashtags.map(tag => (
              <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full"
                style={{ background: 'var(--purple-pale)', color: 'var(--purple)', border: '1px solid var(--purple-border)' }}>
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2">
        {post.scheduledDate && (
          <div className="rounded-lg p-2.5 text-center" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
            <Calendar className="w-3.5 h-3.5 mx-auto mb-1" style={{ color: 'var(--text-muted)' }} />
            <p className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{post.scheduledDate}</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Date</p>
          </div>
        )}
        {post.engagement !== undefined && (
          <div className="rounded-lg p-2.5 text-center" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
            <Eye className="w-3.5 h-3.5 mx-auto mb-1" style={{ color: 'var(--gold)' }} />
            <p className="text-xs font-mono font-bold" style={{ color: 'var(--gold)' }}>{post.engagement.toLocaleString()}</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Engagement</p>
          </div>
        )}
      </div>

      {/* Notes */}
      {post.notes && (
        <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <StickyNote className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] font-semibold" style={{ color: 'var(--gold)' }}>Notes</span>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{post.notes}</p>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        <ActionBtn label="Edit Content" icon={Edit3} />
        {post.status === 'draft' && <ActionBtn label="Schedule" icon={Calendar} />}
        {post.status === 'scheduled' && <ActionBtn label="Publish Now" icon={Send} />}
        {post.status === 'published' && <ActionBtn label="View Analytics" icon={Eye} />}
        <ActionBtn label="Duplicate" icon={Edit3} />
      </div>
    </div>
  );
}

function ActionBtn({ label, icon: Icon }: { label: string; icon?: typeof Edit3 }) {
  return (
    <button
      className="text-xs font-medium py-2 px-3 rounded-lg transition flex items-center gap-1.5 justify-center"
      style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
    >
      {Icon && <Icon className="w-3 h-3" />}
      {label}
    </button>
  );
}
