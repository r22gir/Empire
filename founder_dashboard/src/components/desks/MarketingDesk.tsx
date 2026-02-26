'use client';
import { useState } from 'react';
import { MOCK_POSTS, ContentPost, PostStatus } from '@/lib/deskData';
import { Megaphone, FileText, Calendar, Eye } from 'lucide-react';
import { StatsBar, FilterTabs, StatusBadge, TaskList, DetailPanel } from './shared';
import PostDetail from './marketing/PostDetail';

const STATUS_COLOR: Record<PostStatus, string> = {
  draft: 'var(--text-muted)',
  scheduled: '#8B5CF6',
  published: '#22c55e',
};

const PLATFORM_ICON: Record<string, string> = {
  Instagram: '📸',
  Facebook: '👤',
  Pinterest: '📌',
  TikTok: '🎵',
  Blog: '📝',
};

export default function MarketingDesk() {
  const [posts] = useState<ContentPost[]>(MOCK_POSTS);
  const [filter, setFilter] = useState<string>('all');
  const [selectedPost, setSelectedPost] = useState<ContentPost | null>(null);

  const published = posts.filter(p => p.status === 'published').length;
  const scheduled = posts.filter(p => p.status === 'scheduled').length;
  const drafts = posts.filter(p => p.status === 'draft').length;
  const totalEngagement = posts.reduce((s, p) => s + (p.engagement || 0), 0);
  const filtered = filter === 'all' ? posts : posts.filter(p => p.status === filter);

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Published', value: String(published), icon: Megaphone, color: '#22c55e' },
        { label: 'Scheduled', value: String(scheduled), icon: Calendar, color: '#8B5CF6' },
        { label: 'Drafts', value: String(drafts), icon: FileText, color: 'var(--text-muted)' },
        { label: 'Total Engagement', value: totalEngagement.toLocaleString(), icon: Eye, color: 'var(--gold)' },
      ]} />

      <FilterTabs options={['all', 'draft', 'scheduled', 'published']} active={filter} onChange={setFilter} />

      <div className="flex-1 overflow-auto p-4">
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            {filtered.map(post => (
              <div
                key={post.id}
                className="rounded-xl p-4 transition cursor-pointer"
                style={{
                  background: selectedPost?.id === post.id ? 'var(--gold-pale)' : 'var(--surface)',
                  border: selectedPost?.id === post.id ? '1px solid var(--gold-border)' : '1px solid var(--border)',
                }}
                onClick={() => setSelectedPost(post)}
                onMouseEnter={e => { if (selectedPost?.id !== post.id) e.currentTarget.style.background = 'var(--hover)'; }}
                onMouseLeave={e => { if (selectedPost?.id !== post.id) e.currentTarget.style.background = 'var(--surface)'; }}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="text-lg">{PLATFORM_ICON[post.platform] || '📄'}</span>
                  <StatusBadge label={post.status} color={STATUS_COLOR[post.status]} />
                </div>
                <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>{post.title}</p>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{post.platform}</span>
                  {post.scheduledDate && (
                    <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{post.scheduledDate}</span>
                  )}
                </div>
                {post.engagement !== undefined && (
                  <div className="mt-2 flex items-center gap-1">
                    <Eye className="w-3 h-3" style={{ color: 'var(--gold)' }} />
                    <span className="text-xs font-mono" style={{ color: 'var(--gold)' }}>{post.engagement.toLocaleString()}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
          {filtered.length === 0 && (
            <p className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>No posts match filter</p>
          )}
          <TaskList desk="marketing" compact />
        </div>
      </div>

      <DetailPanel open={!!selectedPost} onClose={() => setSelectedPost(null)} title={selectedPost?.title || ''}>
        {selectedPost && <PostDetail post={selectedPost} />}
      </DetailPanel>
    </div>
  );
}
