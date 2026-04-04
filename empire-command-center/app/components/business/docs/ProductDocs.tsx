'use client';
import { useState } from 'react';
import { DOCS_REGISTRY, DOC_TYPE_COLORS, type DocEntry } from '../../../lib/docs-registry';
import { FileText, Search, ChevronDown, ChevronRight, BookOpen, Image, FileType, Download, ExternalLink } from 'lucide-react';

interface Props {
  product: string;
}

// Determine file format from path
function getFileFormat(path: string): 'md' | 'pdf' | 'docx' | 'pptx' | 'html' | 'image' | 'mermaid' | 'txt' | 'json' | 'other' {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  if (['md'].includes(ext)) return 'md';
  if (['pdf'].includes(ext)) return 'pdf';
  if (['docx', 'doc', 'odt'].includes(ext)) return 'docx';
  if (['pptx', 'ppt'].includes(ext)) return 'pptx';
  if (['html', 'htm'].includes(ext)) return 'html';
  if (['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'].includes(ext)) return 'image';
  if (['mermaid', 'mmd'].includes(ext)) return 'mermaid';
  if (['txt'].includes(ext)) return 'txt';
  if (['json'].includes(ext)) return 'json';
  return 'other';
}

const FORMAT_ICONS: Record<string, { label: string; color: string; bg: string }> = {
  md: { label: 'MD', color: '#16a34a', bg: '#f0fdf4' },
  pdf: { label: 'PDF', color: '#dc2626', bg: '#fef2f2' },
  docx: { label: 'DOCX', color: '#2563eb', bg: '#eff6ff' },
  html: { label: 'HTML', color: '#ea580c', bg: '#fff7ed' },
  image: { label: 'IMG', color: '#7c3aed', bg: '#f5f3ff' },
  mermaid: { label: 'DGM', color: '#059669', bg: '#ecfdf5' },
  txt: { label: 'TXT', color: '#737373', bg: '#f5f5f5' },
  json: { label: 'JSON', color: '#ca8a04', bg: '#fefce8' },
  pptx: { label: 'PPTX', color: '#ea580c', bg: '#fff7ed' },
  other: { label: 'FILE', color: '#737373', bg: '#f5f5f5' },
};

export default function ProductDocs({ product }: Props) {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [formatFilter, setFormatFilter] = useState<string | null>(null);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [docContent, setDocContent] = useState<Record<string, string>>({});
  const [loadingDoc, setLoadingDoc] = useState<string | null>(null);

  const docs = DOCS_REGISTRY[product] || [];

  const filtered = docs.filter(d => {
    const matchSearch = !search || d.title.toLowerCase().includes(search.toLowerCase()) || d.description.toLowerCase().includes(search.toLowerCase());
    const matchType = !typeFilter || d.type === typeFilter;
    const matchFormat = !formatFilter || getFileFormat(d.path) === formatFilter;
    return matchSearch && matchType && matchFormat;
  });

  // Get unique types and formats for filter buttons
  const types = Array.from(new Set(docs.map(d => d.type)));
  const formats = Array.from(new Set(docs.map(d => getFileFormat(d.path))));

  const handleDocClick = async (doc: DocEntry) => {
    const format = getFileFormat(doc.path);

    // Images — toggle inline preview
    if (format === 'image') {
      setExpandedDoc(expandedDoc === doc.path ? null : doc.path);
      return;
    }

    // PDFs, PPTX, DOCX, HTML — toggle download/preview panel
    if (format === 'pdf' || format === 'html' || format === 'docx' || format === 'pptx') {
      setExpandedDoc(expandedDoc === doc.path ? null : doc.path);
      return;
    }

    // MD, TXT, JSON, Mermaid — load inline
    if (docContent[doc.path]) {
      setExpandedDoc(expandedDoc === doc.path ? null : doc.path);
      return;
    }
    setLoadingDoc(doc.path);
    setExpandedDoc(doc.path);
    try {
      const res = await fetch(`/api/docs/read?path=${encodeURIComponent(doc.path)}`);
      if (res.ok) {
        const data = await res.json();
        setDocContent(prev => ({ ...prev, [doc.path]: data.content }));
      } else {
        setDocContent(prev => ({ ...prev, [doc.path]: '(Could not load file content)' }));
      }
    } catch {
      setDocContent(prev => ({ ...prev, [doc.path]: '(Could not load file content)' }));
    }
    setLoadingDoc(null);
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center gap-3">
        <BookOpen size={20} style={{ color: '#b8960c' }} />
        <span style={{ fontSize: 16, fontWeight: 700, color: '#333' }}>
          Documentation
        </span>
        <span style={{ fontSize: 13, color: '#999', fontWeight: 500 }}>
          {docs.length} files
        </span>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={15} style={{ position: 'absolute', left: 12, top: 10, color: '#999' }} />
        <input
          type="text"
          placeholder="Search documentation..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%',
            padding: '9px 14px 9px 36px',
            borderRadius: 12,
            border: '1.5px solid #ece8e0',
            fontSize: 13,
            background: '#faf9f7',
            outline: 'none',
          }}
        />
      </div>

      {/* Filter Row */}
      <div className="flex flex-wrap gap-1.5">
        {/* Type filters */}
        <button
          onClick={() => { setTypeFilter(null); setFormatFilter(null); }}
          style={{
            padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: 'pointer',
            border: !typeFilter && !formatFilter ? '1.5px solid #b8960c' : '1.5px solid #ece8e0',
            background: !typeFilter && !formatFilter ? '#fdf8eb' : '#faf9f7',
            color: !typeFilter && !formatFilter ? '#96750a' : '#888',
          }}
        >All</button>

        {/* Format filters */}
        {formats.map(f => {
          const fi = FORMAT_ICONS[f];
          return (
            <button
              key={`fmt-${f}`}
              onClick={() => { setFormatFilter(formatFilter === f ? null : f); setTypeFilter(null); }}
              style={{
                padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                border: formatFilter === f ? `1.5px solid ${fi.color}` : '1.5px solid #ece8e0',
                background: formatFilter === f ? fi.bg : '#faf9f7',
                color: formatFilter === f ? fi.color : '#888',
              }}
            >{fi.label}</button>
          );
        })}

        <span style={{ width: 1, height: 20, background: '#ece8e0', margin: '0 4px' }} />

        {/* Category type filters */}
        {types.map(t => {
          const c = DOC_TYPE_COLORS[t] || { bg: '#f5f5f5', text: '#666' };
          return (
            <button
              key={`type-${t}`}
              onClick={() => { setTypeFilter(typeFilter === t ? null : t); setFormatFilter(null); }}
              style={{
                padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                border: typeFilter === t ? `1.5px solid ${c.text}` : '1.5px solid #ece8e0',
                background: typeFilter === t ? c.bg : '#faf9f7',
                color: typeFilter === t ? c.text : '#888',
                textTransform: 'capitalize',
              }}
            >{t}</button>
          );
        })}
      </div>

      {/* Doc List */}
      <div className="flex flex-col gap-2">
        {filtered.length === 0 && (
          <div style={{ padding: 24, textAlign: 'center', color: '#999', fontSize: 14 }}>
            No documents found
          </div>
        )}
        {filtered.map(doc => {
          const c = DOC_TYPE_COLORS[doc.type] || { bg: '#f5f5f5', text: '#666' };
          const format = getFileFormat(doc.path);
          const fi = FORMAT_ICONS[format];
          const isExpanded = expandedDoc === doc.path;
          const isLoading = loadingDoc === doc.path;
          const isOpenable = format === 'pdf' || format === 'html' || format === 'docx';

          return (
            <div key={doc.path} style={{ borderRadius: 12, border: '1.5px solid #ece8e0', overflow: 'hidden' }}>
              {/* Doc row */}
              <button
                onClick={() => handleDocClick(doc)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                  padding: '12px 16px',
                  background: isExpanded ? '#fdf8eb' : '#fff',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => { if (!isExpanded) e.currentTarget.style.background = '#faf9f7'; }}
                onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = '#fff'; }}
              >
                {/* Format badge */}
                <span style={{
                  padding: '4px 8px', borderRadius: 6, fontSize: 10, fontWeight: 800,
                  background: fi.bg, color: fi.color, flexShrink: 0, marginTop: 1,
                  letterSpacing: 0.5,
                }}>{fi.label}</span>

                {/* Title & description */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#222', lineHeight: 1.4 }}>
                    {doc.title}
                  </div>
                  <div style={{ fontSize: 12, color: '#777', marginTop: 3, lineHeight: 1.4 }}>
                    {doc.description}
                  </div>
                  <div style={{ fontSize: 10, color: '#bbb', marginTop: 4, fontFamily: 'monospace' }}>
                    {doc.path}
                  </div>
                </div>

                {/* Category badge */}
                <span style={{
                  padding: '3px 10px', borderRadius: 6, fontSize: 10, fontWeight: 700,
                  background: c.bg, color: c.text, textTransform: 'uppercase', flexShrink: 0,
                }}>{doc.type}</span>

                {/* Action icon */}
                {isExpanded
                  ? <ChevronDown size={14} style={{ color: '#b8960c', flexShrink: 0, marginTop: 2 }} />
                  : <ChevronRight size={14} style={{ color: '#ccc', flexShrink: 0, marginTop: 2 }} />
                }
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div style={{ borderTop: '1px solid #ece8e0', background: '#fefefe' }}>
                  {format === 'image' ? (
                    <div style={{ padding: 16, textAlign: 'center' }}>
                      <img
                        src={`/api/docs/serve?path=${encodeURIComponent(doc.path)}`}
                        alt={doc.title}
                        style={{ maxWidth: '100%', maxHeight: 500, borderRadius: 8, border: '1px solid #ece8e0' }}
                      />
                    </div>
                  ) : format === 'pdf' ? (
                    <div style={{ padding: 0 }}>
                      <iframe
                        src={`/api/docs/serve?path=${encodeURIComponent(doc.path)}`}
                        style={{ width: '100%', height: 600, border: 'none' }}
                        title={doc.title}
                      />
                      <div style={{ padding: '8px 16px', borderTop: '1px solid #ece8e0', display: 'flex', gap: 8 }}>
                        <a
                          href={`/api/docs/serve?path=${encodeURIComponent(doc.path)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                            borderRadius: 8, fontSize: 12, fontWeight: 600, color: '#dc2626',
                            border: '1px solid #fecaca', background: '#fef2f2', textDecoration: 'none',
                          }}
                        >
                          <ExternalLink size={12} /> Open Full Screen
                        </a>
                        <a
                          href={`/api/docs/serve?path=${encodeURIComponent(doc.path)}`}
                          download
                          style={{
                            display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px',
                            borderRadius: 8, fontSize: 12, fontWeight: 600, color: '#555',
                            border: '1px solid #ece8e0', background: '#faf9f7', textDecoration: 'none',
                          }}
                        >
                          <Download size={12} /> Download
                        </a>
                      </div>
                    </div>
                  ) : (format === 'docx' || format === 'pptx' || format === 'html') ? (
                    <div style={{ padding: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 20px', background: '#faf9f7', borderRadius: 10, border: '1px solid #ece8e0' }}>
                        <FileText size={24} style={{ color: fi.color }} />
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 14, fontWeight: 600, color: '#333' }}>{doc.title}</div>
                          <div style={{ fontSize: 11, color: '#999', marginTop: 2, fontFamily: 'monospace' }}>{doc.path}</div>
                        </div>
                        <a
                          href={`/api/docs/serve?path=${encodeURIComponent(doc.path)}`}
                          target={format === 'html' ? '_blank' : undefined}
                          download={format !== 'html' ? true : undefined}
                          rel="noopener noreferrer"
                          style={{
                            display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 18px',
                            borderRadius: 8, fontSize: 13, fontWeight: 700, color: '#fff',
                            background: fi.color, textDecoration: 'none',
                          }}
                        >
                          <Download size={14} /> {format === 'html' ? 'Open' : 'Download'}
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div style={{ padding: '14px 18px', maxHeight: 500, overflowY: 'auto' }}>
                        {isLoading ? (
                          <div style={{ fontSize: 13, color: '#999', padding: 20, textAlign: 'center' }}>Loading document...</div>
                        ) : (
                          <pre style={{
                            fontSize: 12,
                            lineHeight: 1.7,
                            color: '#444',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            fontFamily: 'ui-monospace, SFMono-Regular, monospace',
                            margin: 0,
                          }}>
                            {docContent[doc.path] || ''}
                          </pre>
                        )}
                      </div>
                      {/* PDF download button for docs with PDF companions */}
                      {doc.path.startsWith('docs/relist/') && doc.path.endsWith('.md') && (() => {
                        const basename = doc.path.split('/').pop()?.replace('.md', '') || '';
                        const num = doc.title.match(/[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓]/)?.[0];
                        const numMap: Record<string, string> = {'①':'01','②':'02','③':'03','④':'04','⑤':'05','⑥':'06','⑦':'07','⑧':'08','⑨':'09','⑩':'10','⑪':'11','⑫':'12','⑬':'13','⑭':'14','⑮':'15','⑯':'16','⑰':'17','⑱':'18','⑲':'19','⑳':'20','㉑':'21','㉒':'22','㉓':'23'};
                        const prefix = num ? numMap[num] : '';
                        const pdfPath = prefix ? `docs/relist/pdf/${prefix}_${basename}.pdf` : '';
                        if (!pdfPath) return null;
                        return (
                          <div style={{ padding: '8px 18px', borderTop: '1px solid #ece8e0', display: 'flex', gap: 8 }}>
                            <a href={`/api/docs/serve?path=${encodeURIComponent(pdfPath)}`} target="_blank" rel="noopener noreferrer"
                              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, color: '#dc2626', border: '1px solid #fecaca', background: '#fef2f2', textDecoration: 'none' }}>
                              <Download size={12} /> View PDF
                            </a>
                            <a href={`/api/docs/serve?path=${encodeURIComponent(pdfPath)}`} download
                              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600, color: '#555', border: '1px solid #ece8e0', background: '#faf9f7', textDecoration: 'none' }}>
                              <Download size={12} /> Download PDF
                            </a>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
