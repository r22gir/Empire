'use client';
import { useState, useEffect } from 'react';
import { API_URL } from '@/lib/api';
import {
  X, FileText, Download, Trash2, ExternalLink, Search,
  BookOpen, Clock, HardDrive, RefreshCw, Send, Loader2,
} from 'lucide-react';

interface Presentation {
  filename: string;
  title: string;
  size: number;
  created_at: string;
  url: string;
}

interface ResearchPanelProps {
  onClose: () => void;
  onNewResearch: (topic: string) => void;
}

export default function ResearchPanel({ onClose, onNewResearch }: ResearchPanelProps) {
  const [presentations, setPresentations] = useState<Presentation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [newTopic, setNewTopic] = useState('');
  const [generating, setGenerating] = useState(false);

  const fetchPresentations = async () => {
    setLoading(true);
    try {
      const res = await fetch(API_URL + '/max/presentations');
      const data = await res.json();
      setPresentations(data.presentations || []);
    } catch { /* */ }
    setLoading(false);
  };

  useEffect(() => { fetchPresentations(); }, []);

  const filtered = presentations.filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatSize = (b: number) =>
    b > 1_048_576 ? (b / 1_048_576).toFixed(1) + ' MB' : (b / 1_024).toFixed(0) + ' KB';

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86_400_000) {
      const hrs = Math.floor(diff / 3_600_000);
      return hrs === 0 ? 'Just now' : `${hrs}h ago`;
    }
    if (diff < 604_800_000) return d.toLocaleDateString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const handleDelete = async (filename: string) => {
    if (!confirm('Delete this report?')) return;
    try {
      await fetch(API_URL + `/max/presentations/${filename}`, { method: 'DELETE' });
      setPresentations(prev => prev.filter(p => p.filename !== filename));
    } catch { /* */ }
  };

  const handleOpen = (p: Presentation) => {
    const url = API_URL.replace('/api/v1', '') + p.url;
    window.open(url, '_blank');
  };

  const handleDownload = (p: Presentation) => {
    const url = API_URL.replace('/api/v1', '') + p.url;
    const a = document.createElement('a');
    a.href = url;
    a.download = p.filename;
    a.click();
  };

  const handleGenerate = () => {
    if (!newTopic.trim()) return;
    onNewResearch(newTopic.trim());
    setNewTopic('');
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <div
        className="rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl"
        style={{ background: 'var(--glass-bg-solid)', border: '1px solid var(--glass-border)' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="shrink-0 px-5 py-4 flex items-center justify-between"
          style={{ borderBottom: '1px solid var(--glass-border)', background: 'linear-gradient(135deg, rgba(212,175,55,0.06), rgba(139,92,246,0.06))' }}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'rgba(212,175,55,0.12)', border: '1px solid rgba(212,175,55,0.2)' }}>
              <BookOpen className="w-5 h-5" style={{ color: 'var(--gold)' }} />
            </div>
            <div>
              <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Research & Reports</h2>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{presentations.length} report{presentations.length !== 1 ? 's' : ''} saved</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchPresentations}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition"
              style={{ color: 'var(--text-secondary)' }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* New Research input */}
        <div className="shrink-0 px-5 py-3" style={{ borderBottom: '1px solid var(--glass-border)', background: 'var(--raised)' }}>
          <div className="flex gap-2">
            <input
              type="text"
              value={newTopic}
              onChange={e => setNewTopic(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleGenerate(); }}
              placeholder="Research a new topic..."
              className="flex-1 rounded-xl px-4 py-2.5 text-sm outline-none"
              style={{ background: 'var(--elevated)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}
            />
            <button
              onClick={handleGenerate}
              disabled={!newTopic.trim()}
              className="px-4 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition"
              style={{
                background: newTopic.trim() ? 'var(--gold)' : 'var(--elevated)',
                color: newTopic.trim() ? '#0a0a0a' : 'var(--text-muted)',
                border: '1px solid ' + (newTopic.trim() ? 'var(--gold)' : 'var(--glass-border)'),
              }}
            >
              <Search className="w-4 h-4" />
              Research
            </button>
          </div>
        </div>

        {/* Search existing */}
        {presentations.length > 3 && (
          <div className="shrink-0 px-5 py-2" style={{ borderBottom: '1px solid var(--glass-border)' }}>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Filter reports..."
                className="w-full rounded-lg pl-9 pr-3 py-2 text-xs outline-none"
                style={{ background: 'var(--elevated)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}
              />
            </div>
          </div>
        )}

        {/* Reports list */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-12 gap-3">
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--gold)' }} />
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading reports...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-12">
              <BookOpen className="w-12 h-12 mx-auto mb-3" style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {searchQuery ? 'No reports match your search' : 'No reports yet. Start by researching a topic above.'}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filtered.map(p => (
                <div
                  key={p.filename}
                  className="group rounded-xl p-3.5 transition cursor-pointer"
                  style={{ background: 'var(--raised)', border: '1px solid var(--glass-border)' }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)'; e.currentTarget.style.background = 'var(--elevated)'; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--glass-border)'; e.currentTarget.style.background = 'var(--raised)'; }}
                  onClick={() => handleOpen(p)}
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                      style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}
                    >
                      <FileText className="w-5 h-5" style={{ color: '#ef4444' }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                        {p.title}
                      </h3>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                          <Clock className="w-3 h-3" />
                          {formatDate(p.created_at)}
                        </span>
                        <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-muted)' }}>
                          <HardDrive className="w-3 h-3" />
                          {formatSize(p.size)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                      <button
                        onClick={e => { e.stopPropagation(); handleDownload(p); }}
                        className="w-8 h-8 rounded-lg flex items-center justify-center transition"
                        style={{ color: 'var(--cyan)' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(6,182,212,0.1)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                        title="Download"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); handleOpen(p); }}
                        className="w-8 h-8 rounded-lg flex items-center justify-center transition"
                        style={{ color: 'var(--gold)' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(212,175,55,0.1)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                        title="Open in new tab"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); handleDelete(p.filename); }}
                        className="w-8 h-8 rounded-lg flex items-center justify-center transition"
                        style={{ color: 'var(--text-muted)' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; e.currentTarget.style.color = '#ef4444'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="shrink-0 px-5 py-2.5 flex items-center justify-between"
          style={{ borderTop: '1px solid var(--glass-border)', background: 'var(--raised)' }}
        >
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Reports are auto-saved when generated via MAX
          </span>
          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
            {presentations.reduce((a, p) => a + p.size, 0) > 1_048_576
              ? (presentations.reduce((a, p) => a + p.size, 0) / 1_048_576).toFixed(1) + ' MB total'
              : (presentations.reduce((a, p) => a + p.size, 0) / 1_024).toFixed(0) + ' KB total'}
          </span>
        </div>
      </div>
    </div>
  );
}
