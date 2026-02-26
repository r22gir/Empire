'use client';
import { TreatmentType, TREATMENT_TYPES, FabricGrade, FABRIC_GRADES } from '@/lib/deskData';

interface QuoteBuilderProps {
  windowCount: number; setWindowCount: (n: number) => void;
  treatment: TreatmentType; setTreatment: (t: TreatmentType) => void;
  fabricGrade: FabricGrade; setFabricGrade: (g: FabricGrade) => void;
  laborRate: number; setLaborRate: (r: number) => void;
  windowWidth: number; setWindowWidth: (w: number) => void;
  windowHeight: number; setWindowHeight: (h: number) => void;
  fullness: number; setFullness: (f: number) => void;
}

export default function QuoteBuilder(p: QuoteBuilderProps) {
  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <p className="text-xs font-semibold mb-3" style={{ color: 'var(--gold)' }}>Quote Builder</p>

      <div className="mb-3">
        <label className="text-[10px] block mb-1" style={{ color: 'var(--text-muted)' }}>Window Count</label>
        <input type="number" min={1} max={50} value={p.windowCount}
          onChange={e => p.setWindowCount(Math.max(1, parseInt(e.target.value) || 1))}
          className="w-full rounded-lg px-2.5 py-2 text-xs outline-none font-mono"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
        />
      </div>

      <div className="mb-3">
        <label className="text-[10px] block mb-1" style={{ color: 'var(--text-muted)' }}>Treatment Type</label>
        <select value={p.treatment} onChange={e => p.setTreatment(e.target.value as TreatmentType)}
          className="w-full rounded-lg px-2.5 py-2 text-xs outline-none cursor-pointer"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
        >
          {TREATMENT_TYPES.map(t => <option key={t.value} value={t.value}>{t.icon} {t.label}</option>)}
        </select>
      </div>

      <div className="mb-3">
        <label className="text-[10px] block mb-1" style={{ color: 'var(--text-muted)' }}>Fabric Grade</label>
        <div className="flex gap-1.5">
          {FABRIC_GRADES.map(g => (
            <button key={g.grade} onClick={() => p.setFabricGrade(g.grade)}
              className="flex-1 py-2 rounded-lg text-[10px] font-medium transition"
              style={{
                background: p.fabricGrade === g.grade ? 'var(--gold-pale)' : 'var(--raised)',
                color: p.fabricGrade === g.grade ? 'var(--gold)' : 'var(--text-secondary)',
                border: p.fabricGrade === g.grade ? '1px solid var(--gold-border)' : '1px solid var(--border)',
              }}
            >
              <span className="block">{g.grade}</span>
              <span className="block opacity-60 mt-0.5">{g.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <div>
          <label className="text-[10px] block mb-1" style={{ color: 'var(--text-muted)' }}>Width (in)</label>
          <input type="number" min={12} max={240} value={p.windowWidth}
            onChange={e => p.setWindowWidth(parseInt(e.target.value) || 72)}
            className="w-full rounded-lg px-2.5 py-2 text-xs outline-none font-mono"
            style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          />
        </div>
        <div>
          <label className="text-[10px] block mb-1" style={{ color: 'var(--text-muted)' }}>Height (in)</label>
          <input type="number" min={12} max={240} value={p.windowHeight}
            onChange={e => p.setWindowHeight(parseInt(e.target.value) || 84)}
            className="w-full rounded-lg px-2.5 py-2 text-xs outline-none font-mono"
            style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          />
        </div>
      </div>

      <div className="mb-3">
        <div className="flex justify-between mb-1">
          <label className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Fullness Multiplier</label>
          <span className="text-[10px] font-mono" style={{ color: 'var(--gold)' }}>{p.fullness}×</span>
        </div>
        <input type="range" min={1.5} max={3.5} step={0.5} value={p.fullness}
          onChange={e => p.setFullness(parseFloat(e.target.value))}
          className="w-full" style={{ accentColor: 'var(--gold)' }}
        />
      </div>

      <div>
        <div className="flex justify-between mb-1">
          <label className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Labor Rate ($/hr)</label>
          <span className="text-[10px] font-mono" style={{ color: 'var(--gold)' }}>${p.laborRate}</span>
        </div>
        <input type="range" min={45} max={120} step={5} value={p.laborRate}
          onChange={e => p.setLaborRate(parseInt(e.target.value))}
          className="w-full" style={{ accentColor: 'var(--gold)' }}
        />
      </div>
    </div>
  );
}
