'use client';

import { useState } from 'react';
import type { MeasureLine } from './MeasurementCanvas';

interface ReferenceCalibrationProps {
  referenceLine: MeasureLine | null;
  unit: 'inches' | 'cm';
  onUnitChange: (u: 'inches' | 'cm') => void;
  onCalibrate: (realLength: number) => void;
  pixelsPerUnit: number | null;
}

export default function ReferenceCalibration({
  referenceLine,
  unit,
  onUnitChange,
  onCalibrate,
  pixelsPerUnit,
}: ReferenceCalibrationProps) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseFloat(inputValue);
    if (!isNaN(parsed) && parsed > 0) {
      onCalibrate(parsed);
    }
  };

  return (
    <div className="bg-[#0a0a0f] border border-yellow-600/40 rounded-xl p-4 space-y-3">
      <h3 className="text-sm font-semibold text-yellow-400 flex items-center gap-2">
        <span>📏</span> Reference Calibration
      </h3>

      {!referenceLine ? (
        <p className="text-xs text-gray-400">
          Draw a <span className="text-yellow-400 font-medium">reference line</span> over a
          known object (credit card, ruler, door frame…) on the image, then enter its real-world
          length below.
        </p>
      ) : (
        <p className="text-xs text-gray-300">
          Reference line detected:{' '}
          <span className="text-yellow-400 font-bold">{Math.round(referenceLine.pixels)} px</span>
        </p>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2 items-center">
        <input
          type="number"
          min="0.01"
          step="any"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="e.g. 3.375"
          disabled={!referenceLine}
          className="flex-1 bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 disabled:opacity-40 focus:border-yellow-500 focus:outline-none"
        />
        <select
          value={unit}
          onChange={(e) => onUnitChange(e.target.value as 'inches' | 'cm')}
          className="bg-[#050508] border border-gray-700 rounded-lg px-2 py-2 text-sm text-gray-300"
        >
          <option value="inches">in</option>
          <option value="cm">cm</option>
        </select>
        <button
          type="submit"
          disabled={!referenceLine || !inputValue}
          className="px-3 py-2 rounded-lg bg-yellow-500 hover:bg-yellow-400 text-black text-sm font-semibold disabled:bg-gray-700 disabled:text-gray-500"
        >
          Set
        </button>
      </form>

      {pixelsPerUnit !== null && (
        <p className="text-xs text-green-400">
          ✓ Calibrated — {pixelsPerUnit.toFixed(2)} px / {unit}
        </p>
      )}
    </div>
  );
}
