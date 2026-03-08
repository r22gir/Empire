'use client';
import { Cpu, Printer } from 'lucide-react';

export default function MachineStatus({ dashboard }: { dashboard: any }) {
  const machines = dashboard?.machines || {};

  const machineCards = [
    {
      id: 'x-carve',
      name: 'Inventables X-Carve',
      type: 'CNC Router',
      icon: Cpu,
      specs: '750×750×65mm · GRBL · DeWalt 611',
      data: machines['x-carve'] || { status: 'offline', queued_jobs: 0 },
      color: '#c9a84c',
      colorBg: '#fdf8eb',
    },
    {
      id: 'elegoo-saturn',
      name: 'Elegoo Saturn',
      type: '3D Resin Printer',
      icon: Printer,
      specs: '192×120×200mm · 0.05mm XY · ChiTuBox',
      data: machines['elegoo-saturn'] || { status: 'offline', queued_jobs: 0 },
      color: '#7c3aed',
      colorBg: '#ede9fe',
    },
  ];

  const statusDot = (status: string) => {
    if (status === 'running' || status === 'printing') return 'bg-[#16a34a] animate-pulse';
    if (status === 'idle') return 'bg-[#c9a84c]';
    return 'bg-[#ccc]';
  };

  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
      <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
        <Cpu size={15} className="text-[#c9a84c]" />
        Machine Status
      </h3>

      <div className="space-y-3">
        {machineCards.map(m => (
          <div key={m.id} className="p-4 rounded-lg border border-[#ece8e1] hover:border-[#c9a84c] transition-all">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: m.colorBg, color: m.color }}>
                  <m.icon size={16} />
                </div>
                <div>
                  <div className="text-xs font-bold text-[#1a1a1a]">{m.name}</div>
                  <div className="text-[9px] text-[#aaa]">{m.type}</div>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${statusDot(m.data.status)}`} />
                <span className="text-[10px] font-medium text-[#777] capitalize">{m.data.status}</span>
              </div>
            </div>
            <div className="text-[9px] text-[#aaa] mb-2">{m.specs}</div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#777]">Queued jobs</span>
              <span className="text-xs font-bold" style={{ color: m.color }}>{m.data.queued_jobs}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
