'use client';
import { Plus, Trash2 } from 'lucide-react';

export type Measurement = {
  room: string;
  width: string;
  height: string;
  reference: string;
};

export default function MeasurementInput({
  measurements,
  onChange,
}: {
  measurements: Measurement[];
  onChange: (m: Measurement[]) => void;
}) {
  const addWindow = () => {
    onChange([...measurements, { room: '', width: '', height: '', reference: 'none' }]);
  };
  const removeWindow = (i: number) => {
    onChange(measurements.filter((_, idx) => idx !== i));
  };
  const update = (i: number, field: keyof Measurement, val: string) => {
    const updated = [...measurements];
    updated[i] = { ...updated[i], [field]: val };
    onChange(updated);
  };

  return (
    <div className="space-y-3">
      {measurements.map((m, i) => (
        <div key={i} className="flex items-start gap-2 p-3 rounded-[10px] bg-[#f5f2ed] border border-[#ece8e0]">
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 gap-2">
            <input
              placeholder="Room / Window"
              value={m.room}
              onChange={e => update(i, 'room', e.target.value)}
              className="form-input col-span-2 sm:col-span-1"
            />
            <input
              placeholder='Width (")'
              type="number"
              step="0.25"
              value={m.width}
              onChange={e => update(i, 'width', e.target.value)}
              className="form-input"
            />
            <input
              placeholder='Height (")'
              type="number"
              step="0.25"
              value={m.height}
              onChange={e => update(i, 'height', e.target.value)}
              className="form-input"
            />
            <select
              value={m.reference}
              onChange={e => update(i, 'reference', e.target.value)}
              className="form-input"
            >
              <option value="none">No reference</option>
              <option value="credit-card">Credit Card</option>
              <option value="dollar-bill">Dollar Bill</option>
              <option value="phone">Phone</option>
              <option value="tape-measure">Tape Measure</option>
            </select>
          </div>
          <button type="button" onClick={() => removeWindow(i)} className="mt-2 text-[#d5d0c8] hover:text-[#dc2626] transition-colors">
            <Trash2 size={13} />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={addWindow}
        className="w-full py-2 text-[11px] font-semibold text-[#b8960c] border border-dashed border-[#b8960c]/30 rounded-[10px] hover:bg-[#fdf8eb] transition-colors flex items-center justify-center gap-1.5"
      >
        <Plus size={13} /> Add Window / Area
      </button>
    </div>
  );
}
