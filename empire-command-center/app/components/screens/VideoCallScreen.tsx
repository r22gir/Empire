'use client';
import { Mic, Camera, Monitor, FileText, Eye, PhoneOff } from 'lucide-react';

export default function VideoCallScreen() {
  return (
    <div className="flex-1 flex flex-col bg-[#0a0a0a]">
      <div className="flex-1 flex items-center justify-center relative">
        {/* Main area */}
        <div className="text-center text-[#666]">
          <div className="w-24 h-24 rounded-2xl bg-[#1a1a1a] border-2 border-[#333] flex items-center justify-center mx-auto mb-4">
            <Camera size={36} className="text-[#555]" />
          </div>
          <p className="text-base font-semibold text-[#888]">Ready to start a call</p>
          <p className="text-sm text-[#555] mt-2">Share quotes · designs · documents during the call</p>
        </div>

        {/* Self-view PIP */}
        <div className="absolute bottom-5 right-5 w-44 h-[130px] bg-[#1a1a1a] rounded-xl border-2 border-[#444] flex items-center justify-center text-[#666] text-sm font-medium shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
          <Camera size={20} className="mr-2 text-[#555]" /> You
        </div>

        {/* Doc share panel */}
        <div className="absolute top-5 right-5 bg-[#111]/90 backdrop-blur rounded-xl p-4 text-[#ccc] text-sm flex flex-col gap-2 border border-[#333] min-w-[200px]">
          <div className="font-bold text-xs text-[#888] mb-1 tracking-wide">SHARE DOCUMENT</div>
          <div className="px-3 py-2.5 bg-white/10 rounded-lg cursor-pointer hover:bg-white/20 transition-colors text-sm font-medium">EST-2026-002.pdf</div>
          <div className="px-3 py-2.5 bg-white/10 rounded-lg cursor-pointer hover:bg-white/20 transition-colors text-sm font-medium">Emily Valance Quote</div>
          <div className="px-3 py-2.5 bg-white/10 rounded-lg cursor-pointer hover:bg-white/20 transition-colors text-sm font-medium">Mockup — Designer B</div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex justify-center gap-3.5 py-5 bg-[#111] border-t border-[#222]">
        <VCButton icon={<Mic size={22} />} label="Mute" className="bg-[#333] text-white hover:bg-[#444]" />
        <VCButton icon={<Camera size={22} />} label="Camera" className="bg-[#333] text-white hover:bg-[#444]" />
        <VCButton icon={<Monitor size={22} />} label="Share" className="bg-[#333] text-white hover:bg-[#444]" />
        <VCButton icon={<FileText size={22} />} label="Docs" className="bg-[#2563eb] text-white hover:bg-[#1d4ed8]" />
        <VCButton icon={<Eye size={22} />} label="Client" className="bg-[#16a34a] text-white hover:bg-[#15803d]" />
        <VCButton icon={<PhoneOff size={22} />} label="End" className="bg-[#dc2626] text-white hover:bg-[#b91c1c]" />
      </div>
    </div>
  );
}

function VCButton({ icon, label, className }: { icon: React.ReactNode; label: string; className: string }) {
  return (
    <button className={`w-[56px] h-[56px] rounded-full border-none flex flex-col items-center justify-center cursor-pointer transition-all active:scale-[0.88] ${className}`}>
      {icon}
      <span className="text-[8px] font-bold mt-0.5 opacity-70">{label}</span>
    </button>
  );
}
