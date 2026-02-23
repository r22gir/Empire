'use client';

import type { MeasureLine } from './MeasurementCanvas';

interface MeasurementDisplayProps {
  lines: MeasureLine[];
  referenceLineId: string | null;
  unit: 'inches' | 'cm';
  calibrated: boolean;
  onLabelChange: (id: string, label: string) => void;
  onDelete: (id: string) => void;
  onAddToQuote: () => void;
}

export default function MeasurementDisplay({
  lines,
  referenceLineId,
  unit,
  calibrated,
  onLabelChange,
  onDelete,
  onAddToQuote,
}: MeasurementDisplayProps) {
  const measurementLines = lines.filter((l) => l.id !== referenceLineId);
  const hasResults = measurementLines.some((l) => l.realLength !== undefined);

  return (
    <div className="bg-[#0a0a0f] border border-gray-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-blue-400 flex items-center gap-2">
          <span>📐</span> Measurements
        </h3>
        {hasResults && (
          <button
            onClick={onAddToQuote}
            className="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold"
          >
            Add to Quote
          </button>
        )}
      </div>

      {measurementLines.length === 0 ? (
        <p className="text-xs text-gray-500">
          {calibrated
            ? 'Draw lines on the image to measure dimensions.'
            : 'Calibrate first, then draw measurement lines.'}
        </p>
      ) : (
        <ul className="space-y-2">
          {measurementLines.map((line) => (
            <li
              key={line.id}
              className="flex items-center gap-2 bg-[#050508] rounded-lg px-3 py-2"
            >
              <span
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: line.color }}
              />
              <input
                value={line.label}
                onChange={(e) => onLabelChange(line.id, e.target.value)}
                className="flex-1 bg-transparent text-sm text-gray-200 focus:outline-none min-w-0"
                placeholder="Label…"
              />
              <span className="text-sm font-mono text-white whitespace-nowrap">
                {line.realLength !== undefined
                  ? `${line.realLength} ${unit}`
                  : `${Math.round(line.pixels)} px`}
              </span>
              <button
                onClick={() => onDelete(line.id)}
                className="text-gray-600 hover:text-red-400 text-xs flex-shrink-0"
                title="Delete"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      {/* Confidence note */}
      {hasResults && (
        <p className="text-xs text-gray-500">
          Accuracy depends on how precisely the reference line was drawn. For best results use a
          flat, orthogonal reference object.
        </p>
      )}
    </div>
  );
}
