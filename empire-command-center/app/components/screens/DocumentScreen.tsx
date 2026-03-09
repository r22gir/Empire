'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { FileText, Send, Mail, Video, Printer, Download } from 'lucide-react';

export default function DocumentScreen() {
  const [files, setFiles] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);

  useEffect(() => {
    fetch(API + '/files').then(r => r.json()).then(data => {
      setFiles(data.files || data || []);
    }).catch(() => {});
  }, []);

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Main viewer */}
      <div className="flex-1 flex items-center justify-center p-6" style={{ background: 'var(--bg)' }}>
        {selected ? (
          <iframe src={API.replace('/api/v1', '') + '/api/v1/files/view/' + selected.name}
            style={{ width: 595, height: 842, background: 'white', borderRadius: 'var(--radius)', border: '1px solid var(--border)', boxShadow: '0 6px 24px rgba(0,0,0,0.08)' }} />
        ) : (
          <div style={{ width: 595, height: 842, background: 'white', borderRadius: 'var(--radius)', border: '1px solid var(--border)', boxShadow: '0 6px 24px rgba(0,0,0,0.08)' }}
            className="flex flex-col items-center justify-center">
            <FileText size={48} style={{ color: 'var(--faint)' }} className="mb-3" />
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>Select a document</div>
            <div style={{ fontSize: 13, color: 'var(--muted)', marginTop: 4 }}>Choose from the sidebar to preview</div>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <div style={{ width: 290, background: 'var(--panel)', borderLeft: '1px solid var(--border)', padding: '20px 16px' }} className="overflow-y-auto">
        <div className="section-label" style={{ marginBottom: 12 }}>Documents</div>
        {files.length === 0 && <div style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center', padding: '16px 0' }}>No files found</div>}
        <div className="space-y-1.5">
          {files.slice(0, 20).map((f: any, i: number) => (
            <button key={i} onClick={() => setSelected(f)}
              className={`empire-card ${selected?.name === f.name ? 'active' : ''}`}
              style={{ width: '100%', textAlign: 'left', display: 'flex', alignItems: 'center', gap: 10, minHeight: 48, padding: '10px 14px' }}>
              <FileText size={16} style={{ color: 'var(--gold)' }} className="shrink-0" />
              <div className="truncate flex-1">
                <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: 12 }} className="truncate">{f.name || f.filename}</div>
                <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>{f.size ? `${(f.size / 1024).toFixed(0)} KB` : ''}</div>
              </div>
            </button>
          ))}
        </div>

        {selected && (
          <>
            <div className="section-label" style={{ marginTop: 20, marginBottom: 12 }}>Actions</div>
            <div className="flex flex-col gap-2">
              <ActionBtn icon={<Send size={15} />} label="Send via Telegram" color="var(--blue)" />
              <ActionBtn icon={<Mail size={15} />} label="Email to Client" color="var(--gold)" />
              <ActionBtn icon={<Video size={15} />} label="Share on Video Call" color="var(--green)" />
              <ActionBtn icon={<Printer size={15} />} label="Print" color="var(--purple)" />
              <ActionBtn icon={<Download size={15} />} label="Download" color="var(--text-secondary)" />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ActionBtn({ icon, label, color }: { icon: React.ReactNode; label: string; color: string }) {
  return (
    <button className="empire-card"
      style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', fontSize: 13, fontWeight: 600, color, minHeight: 46, width: '100%', textAlign: 'left' }}>
      {icon}
      <span>{label}</span>
    </button>
  );
}
