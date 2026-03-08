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
      <div className="flex-1 flex flex-col p-5">
        <div className="flex gap-2.5 mb-4">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#b8960c] opacity-50" />
            <input value={query} onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              className="w-full pl-10 pr-4 py-3.5 border-1.5 border-[#d8d3cb] rounded-xl text-[14px] outline-none min-h-[48px] bg-white focus:border-[#b8960c] focus:shadow-[0_0_0_3px_#f5ecd0] placeholder:text-[#bbb] font-medium"
              placeholder="Search the web, memory, knowledge base..." />
          </div>
          <button onClick={handleSearch} disabled={loading}
            className="px-7 py-3 bg-[#b8960c] text-white border-2 border-[#a08509] rounded-xl text-[14px] font-bold cursor-pointer min-h-[48px] hover:bg-[#a08509] flex items-center gap-2 disabled:opacity-50 shadow-[0_2px_8px_rgba(184,150,12,0.25)] transition-all active:scale-[0.97]">
            <Search size={16} /> Search
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-2.5">
          {loading && (
            <div className="text-center py-10">
              <div className="w-8 h-8 border-3 border-[#e5e0d8] border-t-[#b8960c] rounded-full animate-spin mx-auto mb-3" />
              <div className="text-sm text-[#888]">Searching...</div>
            </div>
          )}

          {memoryResults.map((m: any, i: number) => (
            <div key={'m' + i} className="p-4 rounded-xl border-2 border-[#7c3aed] bg-[#faf5ff] cursor-pointer hover:bg-[#f3ecff] transition-all shadow-[0_1px_4px_rgba(124,58,237,0.08)]">
              <div className="flex items-center gap-2 mb-1">
                <Brain size={14} className="text-[#7c3aed]" />
                <span className="text-sm font-bold text-[#7c3aed]">From Memory: {m.subject || m.title || 'Memory'}</span>
              </div>
              <div className="text-[10px] text-[#7c3aed] font-mono opacity-60">empire-memory</div>
              <div className="text-xs text-[#555] mt-1.5 leading-relaxed">{m.content || m.summary || JSON.stringify(m).slice(0, 200)}</div>
            </div>
          ))}

          {results.map((r: any, i: number) => (
            <div key={i} className="p-4 rounded-xl border border-[#e5e0d8] bg-white cursor-pointer hover:bg-[#fdf8eb] hover:border-[#b8960c] transition-all shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
              <div className="flex items-center gap-2 mb-1">
                <Globe size={14} className="text-[#2563eb]" />
                <span className="text-sm font-bold text-[#2563eb]">{r.title}</span>
              </div>
              <div className="text-[10px] text-[#16a34a] font-mono">{r.url}</div>
              <div className="text-xs text-[#555] mt-1.5 leading-relaxed">{r.snippet}</div>
            </div>
          ))}

          {!loading && results.length === 0 && memoryResults.length === 0 && (
            <div className="text-center py-12">
              <Search size={36} className="text-[#d8d3cb] mx-auto mb-3" />
              <div className="text-sm font-semibold text-[#aaa]">Enter a query and search</div>
              <div className="text-xs text-[#ccc] mt-1">Searches web + memory simultaneously</div>
            </div>
          )}
        </div>
      </div>

      {/* Notes panel */}
      <div className="w-[300px] bg-white border-l border-[#e5e0d8] p-4 flex flex-col">
        <div className="flex items-center gap-2 mb-3">
          <StickyNote size={15} className="text-[#b8960c]" />
          <h4 className="text-sm font-bold text-[#1a1a1a]">Research Notes</h4>
        </div>
        <textarea value={notes} onChange={e => setNotes(e.target.value)}
          className="flex-1 border-1.5 border-[#d8d3cb] rounded-xl p-3 text-sm outline-none resize-none bg-[#faf9f7] focus:border-[#b8960c] focus:shadow-[0_0_0_3px_#f5ecd0] placeholder:text-[#bbb]"
          placeholder="Type research notes here..." />
      </div>
    </div>
  );
}
