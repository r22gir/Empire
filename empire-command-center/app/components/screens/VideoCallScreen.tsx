'use client';
import { Mic, Camera, Monitor, FileText, Eye, PhoneOff } from 'lucide-react';

export default function VideoCallScreen() {
  return (
    <div className="flex-1 flex flex-col" style={{ background: '#0a0a0a' }}>
      <div className="flex-1 flex items-center justify-center relative">
        {/* Main area */}
        <div className="text-center">
          <div className="flex items-center justify-center mx-auto mb-4" style={{
            width: 96, height: 96, borderRadius: 'var(--radius-lg)', background: '#1a1a1a', border: '2px solid #333',
          }}>
            <Camera size={36} style={{ color: '#555' }} />
          </div>
          <p style={{ fontSize: 15, fontWeight: 600, color: '#888' }}>Ready to start a call</p>
          <p style={{ fontSize: 13, color: '#555', marginTop: 8 }}>Share quotes · designs · documents during the call</p>
        </div>

        {/* Self-view PIP */}
        <div className="absolute flex items-center justify-center" style={{
          bottom: 20, right: 20, width: 176, height: 130, background: '#1a1a1a',
          borderRadius: 'var(--radius)', border: '2px solid #444', color: '#666',
          fontSize: 14, fontWeight: 500, boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        }}>
          <Camera size={20} style={{ marginRight: 8, color: '#555' }} /> You
        </div>

        {/* Doc share panel */}
        <div className="absolute flex flex-col gap-2" style={{
          top: 20, right: 20, background: 'rgba(17,17,17,0.9)', backdropFilter: 'blur(8px)',
          borderRadius: 'var(--radius)', padding: 16, border: '1px solid #333', minWidth: 200,
        }}>
          <div className="section-label" style={{ color: '#888', marginBottom: 4 }}>Share Document</div>
          {['EST-2026-002.pdf', 'Emily Valance Quote', 'Mockup — Designer B'].map((doc, i) => (
            <div key={i} style={{
              padding: '10px 12px', background: 'rgba(255,255,255,0.1)', borderRadius: 'var(--radius-sm)',
              cursor: 'pointer', fontSize: 13, fontWeight: 500, color: '#ccc', transition: 'background 0.15s',
            }}
              className="hover:bg-white/20">
              {doc}
            </div>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="flex justify-center gap-3.5" style={{ padding: '20px 0', background: '#111', borderTop: '1px solid #222' }}>
        <VCButton icon={<Mic size={22} />} label="Mute" bg="#333" hoverBg="#444" />
        <VCButton icon={<Camera size={22} />} label="Camera" bg="#333" hoverBg="#444" />
        <VCButton icon={<Monitor size={22} />} label="Share" bg="#333" hoverBg="#444" />
        <VCButton icon={<FileText size={22} />} label="Docs" bg="var(--blue)" hoverBg="#1d4ed8" />
        <VCButton icon={<Eye size={22} />} label="Client" bg="#16a34a" hoverBg="#15803d" />
        <VCButton icon={<PhoneOff size={22} />} label="End" bg="var(--red)" hoverBg="#b91c1c" />
      </div>
    </div>
  );
}

function VCButton({ icon, label, bg, hoverBg }: { icon: React.ReactNode; label: string; bg: string; hoverBg: string }) {
  return (
    <button style={{
      width: 56, height: 56, borderRadius: '50%', border: 'none', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', cursor: 'pointer', background: bg, color: 'white',
      transition: 'all 0.15s',
    }}
      className="active:scale-[0.88]"
      onMouseEnter={e => (e.currentTarget.style.background = hoverBg)}
      onMouseLeave={e => (e.currentTarget.style.background = bg)}>
      {icon}
      <span style={{ fontSize: 8, fontWeight: 700, marginTop: 2, opacity: 0.7 }}>{label}</span>
    </button>
  );
}
