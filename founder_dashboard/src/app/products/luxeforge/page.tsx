'use client';

import { useState, useCallback, useRef } from 'react';
import MeasurementCanvas, { MeasureLine } from './MeasurementCanvas';
import ReferenceCalibration from './ReferenceCalibration';
import MeasurementDisplay from './MeasurementDisplay';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type Step = 'upload' | 'calibrate' | 'measure' | 'results';

export default function LuxeForgeMeasurementPage() {
  const [step, setStep] = useState<Step>('upload');
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageId] = useState<string>(() => crypto.randomUUID());
  const [lines, setLines] = useState<MeasureLine[]>([]);
  const [referenceLineId, setReferenceLineId] = useState<string | null>(null);
  const [unit, setUnit] = useState<'inches' | 'cm'>('inches');
  const [pixelsPerUnit, setPixelsPerUnit] = useState<number | null>(null);
  const [quoteText, setQuoteText] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [calculating, setCalculating] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Image upload / capture ──────────────────────────────────────────────────

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    setImageUrl(url);
    setLines([]);
    setReferenceLineId(null);
    setPixelsPerUnit(null);
    setQuoteText('');
    setStep('calibrate');
  };

  // ── Reference calibration ───────────────────────────────────────────────────

  const referenceLine = lines.find((l) => l.id === referenceLineId) ?? null;

  /** Mark the most recently drawn line as the reference line */
  const handleMarkReference = () => {
    if (lines.length === 0) return;
    const last = lines[lines.length - 1];
    setReferenceLineId(last.id);
  };

  const handleCalibrate = async (realLength: number) => {
    if (!referenceLine) return;
    setError('');

    const ppu = referenceLine.pixels / realLength;
    setPixelsPerUnit(ppu);

    // Persist to backend (non-blocking – ignore errors gracefully)
    try {
      await fetch(`${API_URL}/api/luxeforge/measurements/calibrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: imageId,
          reference_pixels: referenceLine.pixels,
          reference_real: realLength,
          reference_unit: unit,
        }),
      });
    } catch {
      // backend may not be running in demo mode – continue anyway
    }

    setStep('measure');
  };

  // ── Measurements ────────────────────────────────────────────────────────────

  const handleCalculate = async () => {
    if (!pixelsPerUnit) return;
    setCalculating(true);
    setError('');

    const measureLines = lines.filter((l) => l.id !== referenceLineId);

    try {
      const res = await fetch(`${API_URL}/api/luxeforge/measurements/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_id: imageId,
          lines: measureLines.map((l) => ({
            label: l.label,
            start: l.start,
            end: l.end,
            pixels: l.pixels,
          })),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const updatedById: Record<string, number> = {};
        for (const l of data.lines) {
          updatedById[l.label] = l.real_length;
        }
        setLines((prev) =>
          prev.map((l) => {
            if (l.id === referenceLineId) return l;
            const rl = updatedById[l.label];
            return rl !== undefined ? { ...l, realLength: rl } : l;
          }),
        );
      } else {
        // Fallback: calculate client-side
        applyClientSideCalculation(measureLines, pixelsPerUnit);
      }
    } catch {
      // Backend not available – calculate client-side
      applyClientSideCalculation(measureLines, pixelsPerUnit);
    }

    setCalculating(false);
    setStep('results');
  };

  const applyClientSideCalculation = (measureLines: MeasureLine[], ppu: number) => {
    setLines((prev) =>
      prev.map((l) => {
        if (l.id === referenceLineId) return l;
        const found = measureLines.find((ml) => ml.id === l.id);
        if (!found) return l;
        return { ...l, realLength: Math.round((found.pixels / ppu) * 1000) / 1000 };
      }),
    );
  };

  // ── Export / Quote ──────────────────────────────────────────────────────────

  const handleAddToQuote = async () => {
    const measureLines = lines.filter((l) => l.id !== referenceLineId);
    try {
      const res = await fetch(`${API_URL}/api/luxeforge/measurements/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_id: imageId, format: 'quote' }),
      });
      if (res.ok) {
        const data = await res.json();
        setQuoteText(data.data as string);
      } else {
        throw new Error('backend unavailable');
      }
    } catch {
      // Client-side fallback
      const text = measureLines
        .filter((l) => l.realLength !== undefined)
        .map((l) =>
          unit === 'inches'
            ? `${l.label}: ${l.realLength}"`
            : `${l.label}: ${l.realLength} ${unit}`,
        )
        .join('\n');
      setQuoteText(text || 'No measurements recorded.');
    }
  };

  const handleLabelChange = (id: string, label: string) => {
    setLines((prev) => prev.map((l) => (l.id === id ? { ...l, label } : l)));
  };

  const handleDelete = (id: string) => {
    setLines((prev) => prev.filter((l) => l.id !== id));
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  const stepLabels: { id: Step; label: string }[] = [
    { id: 'upload', label: '1. Upload' },
    { id: 'calibrate', label: '2. Calibrate' },
    { id: 'measure', label: '3. Measure' },
    { id: 'results', label: '4. Results' },
  ];

  return (
    <div className="min-h-screen bg-[#050508] text-gray-200 p-4 md:p-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-purple-400">LuxeForge</h1>
        <p className="text-sm text-gray-400">In-Picture Measurement & AI Dimension Tool</p>
      </div>

      {/* Step indicator */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {stepLabels.map((s) => (
          <div
            key={s.id}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap ${
              step === s.id
                ? 'bg-purple-600 text-white'
                : 'bg-[#0a0a0f] text-gray-500 border border-gray-800'
            }`}
          >
            {s.label}
          </div>
        ))}
      </div>

      {error && (
        <div className="mb-4 bg-red-900/30 border border-red-700 rounded-lg px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Step 1 – Upload */}
      {step === 'upload' && (
        <div className="flex flex-col items-center justify-center border-2 border-dashed border-gray-700 rounded-2xl py-20 gap-4">
          <span className="text-5xl">📷</span>
          <p className="text-gray-400 text-sm">Upload or capture a photo to start measuring</p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-xl text-white font-semibold"
          >
            Choose Photo
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>
      )}

      {/* Steps 2-4 – Canvas + panels */}
      {imageUrl && step !== 'upload' && (
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Canvas */}
          <div className="flex-1 min-w-0">
            <MeasurementCanvas
              imageUrl={imageUrl}
              lines={lines}
              onLinesChange={setLines}
              referenceLineId={referenceLineId ?? undefined}
              unit={unit}
            />

            {/* Canvas actions */}
            <div className="mt-3 flex flex-wrap gap-2">
              {step === 'calibrate' && lines.length > 0 && !referenceLineId && (
                <button
                  onClick={handleMarkReference}
                  className="px-4 py-2 rounded-lg bg-yellow-500 text-black text-sm font-semibold hover:bg-yellow-400"
                >
                  Mark Last Line as Reference
                </button>
              )}
              {step === 'measure' && lines.filter((l) => l.id !== referenceLineId).length > 0 && (
                <button
                  onClick={handleCalculate}
                  disabled={calculating}
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-500 disabled:bg-gray-700"
                >
                  {calculating ? 'Calculating…' : 'Calculate Dimensions'}
                </button>
              )}
              <button
                onClick={() => {
                  setImageUrl(null);
                  setLines([]);
                  setReferenceLineId(null);
                  setPixelsPerUnit(null);
                  setQuoteText('');
                  setStep('upload');
                }}
                className="px-4 py-2 rounded-lg border border-gray-700 text-gray-400 text-sm hover:bg-[#0a0a0f]"
              >
                New Photo
              </button>
            </div>
          </div>

          {/* Side panels */}
          <div className="w-full lg:w-80 flex flex-col gap-4">
            <ReferenceCalibration
              referenceLine={referenceLine}
              unit={unit}
              onUnitChange={setUnit}
              onCalibrate={handleCalibrate}
              pixelsPerUnit={pixelsPerUnit}
            />
            <MeasurementDisplay
              lines={lines}
              referenceLineId={referenceLineId}
              unit={unit}
              calibrated={pixelsPerUnit !== null}
              onLabelChange={handleLabelChange}
              onDelete={handleDelete}
              onAddToQuote={handleAddToQuote}
            />

            {/* Quote output */}
            {quoteText && (
              <div className="bg-[#0a0a0f] border border-green-700/40 rounded-xl p-4 space-y-2">
                <h3 className="text-sm font-semibold text-green-400">📋 Quote / Order</h3>
                <pre className="text-xs text-gray-300 whitespace-pre-wrap">{quoteText}</pre>
                <button
                  onClick={() => navigator.clipboard.writeText(quoteText)}
                  className="text-xs text-blue-400 hover:underline"
                >
                  Copy to clipboard
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
