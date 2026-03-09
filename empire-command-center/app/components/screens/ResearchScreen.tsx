'use client';
import { useState } from 'react';
import { API } from '../../lib/api';
import { Search, Brain, Globe, StickyNote } from 'lucide-react';

export default function ResearchScreen() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [memoryResults, setMemoryResults] = useState<any[]>([]);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setResults([]);
    setMemoryResults([]);

    const [webRes, memRes] = await Promise.allSettled([
      fetch(API + '/max/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: `web search: ${query}`, model: 'auto', history: [] }),
      }).then(async r => {
        const text = await r.text();
        const toolMatch = text.match(new RegExp('"tool_result".*?"result":\\s*({[^}]+})', 's'));
        return toolMatch ? JSON.parse(toolMatch[1]) : null;
      }),
      fetch(API + '/memory/search?q=' + encodeURIComponent(query))
        .then(r => r.ok ? r.json() : null),
    ]);

    if (memRes.status === 'fulfilled' && memRes.value) {
      const mems = memRes.value.results || memRes.value.memories || [];
      setMemoryResults(mems.slice(0, 5));
    }

    setLoading(false);
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 flex flex-col" style={{ padding: '24px 36px' }}>
        {/* Search bar */}
        <div className="flex gap-3 mb-5">
          <div className="flex-1 relative">
            <Search size={16} className="absolute top-1/2 -translate-y-1/2" style={{ left: 14, color: 'var(--gold)', opacity: 0.5 }} />
            <input value={query} onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              style={{
                width: '100%', paddingLeft: 40, paddingRight: 16, paddingTop: 12, paddingBottom: 12,
                border: '1px solid var(--border)', borderRadius: 'var(--radius)', fontSize: 14,
                outline: 'none', minHeight: 48, background: 'white', fontWeight: 500,
              }}
              className="focus:border-[var(--gold)] focus:shadow-[0_0_0_3px_var(--gold-light)]"
              placeholder="Search the web, memory, knowledge base..." />
          </div>
          <button onClick={handleSearch} disabled={loading}
            className="filter-tab active flex items-center gap-2"
            style={{ padding: '12px 24px', fontSize: 14, minHeight: 48, opacity: loading ? 0.5 : 1 }}>
            <Search size={16} /> Search
          </button>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto space-y-2.5">
          {loading && (
            <div className="text-center py-10">
              <div className="w-8 h-8 rounded-full animate-spin mx-auto mb-3" style={{ border: '3px solid var(--border)', borderTopColor: 'var(--gold)' }} />
              <div style={{ fontSize: 14, color: 'var(--muted)' }}>Searching...</div>
            </div>
          )}

          {memoryResults.map((m: any, i: number) => (
            <div key={'m' + i} className="empire-card" style={{ borderColor: 'var(--purple)', background: 'var(--purple-bg)' }}>
              <div className="flex items-center gap-2 mb-1">
                <Brain size={14} style={{ color: 'var(--purple)' }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--purple)' }}>From Memory: {m.subject || m.title || 'Memory'}</span>
              </div>
              <div style={{ fontSize: 10, color: 'var(--purple)', fontFamily: 'monospace', opacity: 0.6 }}>empire-memory</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.6 }}>{m.content || m.summary || JSON.stringify(m).slice(0, 200)}</div>
            </div>
          ))}

          {results.map((r: any, i: number) => (
            <div key={i} className="empire-card">
              <div className="flex items-center gap-2 mb-1">
                <Globe size={14} style={{ color: 'var(--blue)' }} />
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--blue)' }}>{r.title}</span>
              </div>
              <div style={{ fontSize: 10, color: 'var(--green)', fontFamily: 'monospace' }}>{r.url}</div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 6, lineHeight: 1.6 }}>{r.snippet}</div>
            </div>
          ))}

          {!loading && results.length === 0 && memoryResults.length === 0 && (
            <div className="text-center py-12">
              <Search size={36} style={{ color: 'var(--faint)' }} className="mx-auto mb-3" />
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--muted)' }}>Enter a query and search</div>
              <div style={{ fontSize: 12, color: 'var(--faint)', marginTop: 4 }}>Searches web + memory simultaneously</div>
            </div>
          )}
        </div>
      </div>

      {/* Notes panel */}
      <div style={{ width: 300, background: 'var(--panel)', borderLeft: '1px solid var(--border)', padding: '20px 16px' }} className="flex flex-col">
        <div className="flex items-center gap-2 mb-3">
          <StickyNote size={15} style={{ color: 'var(--gold)' }} />
          <span className="section-label">Research Notes</span>
        </div>
        <textarea value={notes} onChange={e => setNotes(e.target.value)}
          style={{
            flex: 1, border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 12,
            fontSize: 13, outline: 'none', resize: 'none', background: 'var(--card-bg)',
          }}
          className="focus:border-[var(--gold)] focus:shadow-[0_0_0_3px_var(--gold-light)]"
          placeholder="Type research notes here..." />
      </div>
    </div>
  );
}
