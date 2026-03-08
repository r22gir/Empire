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
      <div className="flex-1 flex items-center justify-center bg-[#eae7e2] p-6">
        {selected ? (
          <iframe src={API.replace('/api/v1', '') + '/api/v1/files/view/' + selected.name}
            className="w-[595px] h-[842px] bg-white shadow-[0_6px_24px_rgba(0,0,0,0.12)] rounded-lg border border-[#d8d3cb]" />
        ) : (
          <div className="bg-white w-[595px] h-[842px] shadow-[0_6px_24px_rgba(0,0,0,0.12)] rounded-lg border border-[#d8d3cb] flex flex-col items-center justify-center">
            <FileText size={48} className="text-[#d8d3cb] mb-3" />
            <div className="text-base font-bold text-[#1a1a1a]">Select a document</div>
            <div className="text-sm text-[#888] mt-1">Choose from the sidebar to preview</div>
          </div>
        )}
      </div>

      {/* Sidebar */}
      <div className="w-[290px] bg-white border-l border-[#e5e0d8] p-4 overflow-y-auto">
        <h4 className="text-sm font-bold mb-3 text-[#1a1a1a]">Documents</h4>
        {files.length === 0 && <div className="text-xs text-[#aaa] text-center py-4">No files found</div>}
        <div className="space-y-1.5">
          {files.slice(0, 20).map((f: any, i: number) => (
            <button key={i} onClick={() => setSelected(f)}
              className={`w-full text-left p-3 rounded-xl border text-xs cursor-pointer transition-all flex items-center gap-2.5 min-h-[48px]
                ${selected?.name === f.name
                  ? 'border-[#b8960c] bg-[#fdf8eb] shadow-[0_2px_6px_rgba(184,150,12,0.12)]'
                  : 'border-[#e5e0d8] bg-white hover:border-[#b8960c] hover:bg-[#fdf8eb]'}`}>
              <FileText size={16} className="text-[#b8960c] shrink-0" />
              <div className="truncate flex-1">
                <div className="font-semibold text-[#1a1a1a] truncate text-[12px]">{f.name || f.filename}</div>
                <div className="text-[10px] text-[#999] mt-0.5">{f.size ? `${(f.size / 1024).toFixed(0)} KB` : ''}</div>
              </div>
            </button>
          ))}
        </div>

        {selected && (
          <>
            <h4 className="text-sm font-bold mt-5 mb-3 text-[#1a1a1a]">Actions</h4>
            <div className="flex flex-col gap-2">
              <ActionBtn icon={<Send size={15} />} label="Send via Telegram" color="#2563eb" />
              <ActionBtn icon={<Mail size={15} />} label="Email to Client" color="#b8960c" />
              <ActionBtn icon={<Video size={15} />} label="Share on Video Call" color="#16a34a" />
              <ActionBtn icon={<Printer size={15} />} label="Print" color="#7c3aed" />
              <ActionBtn icon={<Download size={15} />} label="Download" color="#555" />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ActionBtn({ icon, label, color }: { icon: React.ReactNode; label: string; color: string }) {
  return (
    <button className="flex items-center gap-2.5 p-3 rounded-xl border-1.5 border-[#e5e0d8] bg-white text-[13px] font-semibold cursor-pointer text-left min-h-[46px] transition-all hover:bg-[#fdf8eb] hover:border-[#b8960c] active:scale-[0.98]"
      style={{ color }}>
      {icon}
      <span>{label}</span>
    </button>
  );
}
