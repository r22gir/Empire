'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Mic, Search, X } from 'lucide-react';
import { API } from '../../lib/api';
import {
  DEBOUNCE_MS,
  flattenGroups,
  isDraftReply,
  resultForEnter,
  topResult,
  type SearchHit,
  type SearchResponse,
} from '../../lib/universal-search';
import './universal-search.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onOpen: (hit: SearchHit) => void;
  onDraftReply?: (hit: SearchHit) => void;
};

export function SearchTrigger({ onOpen, label = 'Search' }: { onOpen: () => void; label?: string }) {
  return (
    <button type="button" className="v3-search" onClick={onOpen} aria-label={`${label} (Control or Command K)`} data-testid="universal-search-trigger">
      <Search size={15} strokeWidth={1.8} aria-hidden="true" />
      <span className="us-ph">{label}</span>
      <kbd>⌘K</kbd>
    </button>
  );
}

async function transcribeBlob(blob: Blob): Promise<string> {
  const fd = new FormData();
  fd.append('file', blob, 'search.webm');
  const res = await fetch(`${API}/voice/transcribe`, { method: 'POST', body: fd });
  if (!res.ok) return '';
  const data = await res.json().catch(() => ({}));
  return String(data.text || data.transcript || '').trim();
}

export default function UniversalSearch({ open, onClose, onOpen, onDraftReply }: Props) {
  const [query, setQuery] = useState('');
  const [payload, setPayload] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [focusIdx, setFocusIdx] = useState(0);
  const [listening, setListening] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const genRef = useRef(0);

  useEffect(() => {
    if (open) {
      setQuery('');
      setPayload(null);
      setFocusIdx(0);
      setTimeout(() => inputRef.current?.focus(), 40);
    } else if (recRef.current && recRef.current.state !== 'inactive') {
      recRef.current.stop();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    const gen = ++genRef.current;
    setLoading(true);
    const t = setTimeout(() => {
      fetch(`${API}/universal-search?q=${encodeURIComponent(q)}`, { cache: 'no-store' })
        .then(r => (r.ok ? r.json() : null))
        .then(d => {
          if (gen !== genRef.current) return;
          setPayload(d);
          setFocusIdx(0);
        })
        .catch(() => {
          if (gen !== genRef.current) return;
          setPayload(null);
        })
        .finally(() => {
          if (gen === genRef.current) setLoading(false);
        });
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [query, open]);

  const flat = payload?.results?.length ? payload.results : flattenGroups(payload?.groups);
  const top = topResult(payload);

  const activate = useCallback((hit: SearchHit | null) => {
    if (!hit) return;
    if (isDraftReply(hit) && onDraftReply) {
      onDraftReply(hit);
    } else {
      onOpen(hit);
    }
    onClose();
  }, [onClose, onDraftReply, onOpen]);

  const startVoice = useCallback(async () => {
    if (listening) {
      recRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];
      rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      rec.onstop = async () => {
        setListening(false);
        stream.getTracks().forEach(t => t.stop());
        const text = await transcribeBlob(new Blob(chunks, { type: rec.mimeType || 'audio/webm' }));
        if (text) setQuery(text);
      };
      recRef.current = rec;
      rec.start();
      setListening(true);
    } catch { setListening(false); }
  }, [listening]);

  if (!open) return null;

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusIdx(i => Math.min(i + 1, Math.max(flat.length - 1, 0)));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusIdx(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      activate(resultForEnter(flat, focusIdx) || top);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  let running = 0;

  return (
    <div className="us-root" data-testid="universal-search">
      <div className="us-back" onClick={onClose} />
      <div className="us-panel" role="dialog" aria-modal="true" aria-label="Search" onClick={e => e.stopPropagation()}>
        <div className="us-bar">
          <Search size={18} className="us-icon" aria-hidden="true" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setFocusIdx(0); }}
            onKeyDown={onKey}
            placeholder="Search screens, jobs, quotes, people…"
            aria-label="Search the Command Center"
            autoComplete="off"
            enterKeyHint="search"
            inputMode="search"
          />
          <button type="button" className={`us-mic${listening ? ' on' : ''}`} onClick={startVoice}
            aria-label={listening ? 'Stop voice search' : 'Search by voice'} aria-pressed={listening}>
            <Mic size={16} />
          </button>
          <button type="button" className="us-esc" onClick={onClose} aria-label="Close search"><X size={14} /> ESC</button>
        </div>
        <div className="us-body" role="listbox" aria-label="Search results">
          {loading && <div className="us-status">Searching…</div>}
          {payload?.blocked && <div className="us-empty">Search is not available on this edition.</div>}
          {!loading && query.trim() && !payload?.blocked && !flat.length && (
            <div className="us-empty">No results for “{query.trim()}”</div>
          )}
          {(payload?.groups || []).map(g => (
            <div key={g.type}>
              <div className="us-grp">{g.label}</div>
              {g.items.map(hit => {
                const idx = running++;
                return (
                  <button
                    key={hit.id}
                    type="button"
                    role="option"
                    aria-selected={idx === focusIdx}
                    className={`us-row${idx === focusIdx ? ' on' : ''}`}
                    onMouseEnter={() => setFocusIdx(idx)}
                    onClick={() => activate(hit)}
                  >
                    <span className="ttl">
                      <b>{hit.title}</b>
                      {hit.subtitle ? <span className="sub">{hit.subtitle}</span> : null}
                    </span>
                    <span className="us-act">{hit.action?.label || 'Open'}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
        <div className="us-foot">
          <span>↑↓ Move</span>
          <span>↵ Open top result</span>
          <span>Esc Close</span>
        </div>
      </div>
    </div>
  );
}
