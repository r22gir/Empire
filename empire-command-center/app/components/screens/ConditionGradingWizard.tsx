/**
 * ConditionGradingWizard
 * Phase 1 Prototype — multi-step condition grading wizard
 */

'use client';

import { useState } from 'react';
import { useConditionGrade } from '../../hooks/useArchiveForgePrototype';
import { ARCHIVEFORGE_PROTOTYPE_DISCLAIMER } from '../../config/archiveforge-mock';
import type { GradingDimension } from '../../schemas/archiveforge-schemas';

type WizardPhase = 'photo' | 'wear' | 'grade' | 'result';

function PhaseIndicator({ current }: { current: WizardPhase }) {
  const phases: { key: WizardPhase; label: string }[] = [
    { key: 'photo', label: 'Photo' },
    { key: 'wear', label: 'Wear' },
    { key: 'grade', label: 'Grade' },
  ];
  const currentIdx = phases.findIndex((p) => p.key === current);

  return (
    <div className="flex items-center justify-center gap-2 mb-6">
      {phases.map((p, i) => {
        const isActive = p.key === current;
        const isPast = i < currentIdx;
        return (
          <div key={p.key} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors ${
                isActive
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : isPast
                  ? 'bg-green-600 border-green-500 text-white'
                  : 'bg-gray-800 border-gray-600 text-gray-400'
              }`}
            >
              {isPast ? '✓' : i + 1}
            </div>
            <span className={`text-xs font-medium ${isActive ? 'text-gray-100' : 'text-gray-500'}`}>
              {p.label}
            </span>
            {i < phases.length - 1 && (
              <div className={`w-8 h-0.5 ${isPast ? 'bg-green-500' : 'bg-gray-700'}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function PhotoStep({ onNext }: { onNext: () => void }) {
  return (
    <div className="space-y-4">
      <h3 className="text-gray-100 font-semibold text-center">Upload Cover Photos</h3>
      <p className="text-gray-400 text-sm text-center">
        Front and back cover photos are required for accurate condition grading.
      </p>
      <div className="border-2 border-dashed border-gray-600 rounded-xl p-8 text-center hover:border-indigo-500/50 transition-colors cursor-pointer">
        <div className="text-3xl mb-2">📷</div>
        <p className="text-gray-300 text-sm">Click or drag photos here</p>
        <p className="text-gray-500 text-xs mt-1">Front cover + back cover</p>
      </div>
      <div className="flex gap-3">
        <div className="flex-1 bg-gray-800 border border-gray-700 rounded-lg p-3 text-center">
          <span className="text-gray-500 text-xs">Front</span>
          <div className="h-16 bg-gray-700/50 rounded-lg mt-1 flex items-center justify-center text-gray-600 text-xl">📄</div>
        </div>
        <div className="flex-1 bg-gray-800 border border-gray-700 rounded-lg p-3 text-center">
          <span className="text-gray-500 text-xs">Back</span>
          <div className="h-16 bg-gray-700/50 rounded-lg mt-1 flex items-center justify-center text-gray-600 text-xl">📄</div>
        </div>
      </div>
      <button
        className="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors"
        onClick={onNext}
      >
        Continue to Wear Assessment →
      </button>
    </div>
  );
}

function WearStep({ onNext, onBack, answers, setAnswers }: {
  onNext: () => void;
  onBack: () => void;
  answers: Record<string, unknown>;
  setAnswers: (a: Record<string, unknown>) => void;
}) {
  const dimensions: { key: GradingDimension; label: string; desc: string }[] = [
    { key: 'binding', label: 'Binding', desc: 'Spine condition and structural integrity' },
    { key: 'covers', label: 'Covers', desc: 'Front and back cover condition' },
    { key: 'pages', label: 'Pages', desc: 'Page condition throughout' },
    { key: 'centerStaple', label: 'Center Staple', desc: 'Staple integrity and rust' },
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-gray-100 font-semibold text-center">Wear Assessment</h3>
      <p className="text-gray-400 text-sm text-center">
        Rate each dimension from 1 (poor) to 10 (near mint).
      </p>
      <div className="space-y-3">
        {dimensions.map((d) => (
          <div key={d.key} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-gray-100 font-medium text-sm">{d.label}</span>
                <p className="text-gray-500 text-xs">{d.desc}</p>
              </div>
              <select
                className="bg-gray-700 text-gray-100 text-sm rounded-lg px-2 py-1 border border-gray-600"
                value={(answers[d.key] as number) || ''}
                onChange={(e) => setAnswers({ ...answers, [d.key]: Number(e.target.value) })}
              >
                <option value="">—</option>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-3">
        <button
          className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm font-medium transition-colors"
          onClick={onBack}
        >
          ← Back
        </button>
        <button
          className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
          onClick={onNext}
          disabled={dimensions.some((d) => !(answers[d.key] as number))}
        >
          Calculate Grade →
        </button>
      </div>
    </div>
  );
}

function ResultDisplay({ result, onReset }: {
  result: { overallGrade: string; numericScore: number; expertNotes: string; scores: { dimension: string; score: number }[] };
  onReset: () => void;
}) {
  const gradeColor = result.numericScore >= 80 ? 'text-green-400' : result.numericScore >= 60 ? 'text-yellow-400' : 'text-red-400';
  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className={`text-6xl font-extrabold ${gradeColor}`}>{result.overallGrade}</div>
        <p className="text-gray-400 text-sm mt-2">Numeric Score: {result.numericScore}/100</p>
      </div>
      <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
        <h4 className="text-gray-300 text-sm font-medium mb-3">Dimension Breakdown</h4>
        <div className="space-y-2">
          {result.scores.map((s) => (
            <div key={s.dimension} className="flex items-center justify-between">
              <span className="text-gray-300 text-sm capitalize">{s.dimension}</span>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-gray-700 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${s.score >= 8 ? 'bg-green-500' : s.score >= 6 ? 'bg-yellow-500' : 'bg-red-500'}`}
                    style={{ width: `${s.score * 10}%` }}
                  />
                </div>
                <span className="text-gray-400 text-sm w-4 text-right">{s.score}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
        <p className="text-gray-300 text-sm italic">"{result.expertNotes}"</p>
      </div>
      <button
        className="w-full px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm font-medium transition-colors"
        onClick={onReset}
      >
        Start New Assessment
      </button>
    </div>
  );
}

export default function ConditionGradingWizard() {
  const [phase, setPhase] = useState<WizardPhase>('photo');
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const { result, loading, grade } = useConditionGrade();

  const handleWearNext = async () => {
    await grade(answers);
    setPhase('result');
  };

  return (
    <div className="space-y-4" data-max-task="condition-grading-backend-integration">
      {/* Prototype disclaimer */}
      <div className="border border-yellow-600/40 bg-yellow-900/20 rounded-lg p-3 flex items-start gap-2">
        <span className="text-yellow-400 mt-0.5">⚠</span>
        <div>
          <p className="text-yellow-300 text-sm font-medium">Prototype grading — output is not validated by a certified grader</p>
          <p className="text-yellow-400/70 text-xs mt-0.5">POST /api/v1/condition/grade not yet implemented</p>
        </div>
      </div>

      <PhaseIndicator current={phase} />

      {loading && phase === 'result' ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-48 bg-gray-700 rounded-xl flex items-center justify-center">
            <span className="text-gray-400">Calculating grade...</span>
          </div>
        </div>
      ) : (
        <>
          {phase === 'photo' && <PhotoStep onNext={() => setPhase('wear')} />}
          {phase === 'wear' && (
            <WearStep
              onNext={handleWearNext}
              onBack={() => setPhase('photo')}
              answers={answers}
              setAnswers={setAnswers}
            />
          )}
          {phase === 'result' && result && (
            <ResultDisplay
              result={{
                overallGrade: result.overallGrade,
                numericScore: result.numericScore,
                expertNotes: result.expertNotes,
                scores: result.scores,
              }}
              onReset={() => { setPhase('photo'); setAnswers({}); }}
            />
          )}
        </>
      )}
    </div>
  );
}
