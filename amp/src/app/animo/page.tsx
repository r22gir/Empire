'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useAudio } from '@/context/AudioContext';
import { SAMPLE_TRACKS } from '@/lib/amp-content';
import {
  Sparkles, Calendar,
  ChevronLeft, ChevronRight, PenLine, Play
} from 'lucide-react';

interface MoodOption {
  key: string;
  emoji: string;
  label: string;
  theme: string;
}

const MOODS: MoodOption[] = [
  { key: 'feliz', emoji: '😊', label: 'Feliz & Radiante', theme: 'abundancia' },
  { key: 'en_paz', emoji: '😌', label: 'En Paz & Serena', theme: 'gratitud' },
  { key: 'neutral', emoji: '😐', label: 'Tranquilo / Neutral', theme: 'enfoque' },
  { key: 'triste', emoji: '😔', label: 'Triste / Desanimado', theme: 'duelo' },
  { key: 'ansioso', emoji: '😰', label: 'Ansioso / Con Prisa', theme: 'ansiedad' },
  { key: 'frustrado', emoji: '😤', label: 'Frustrado / Con Estrés', theme: 'ansiedad' },
  { key: 'agradecido', emoji: '🤗', label: 'Muy Agradecido', theme: 'gratitud' },
  { key: 'motivado', emoji: '💪', label: 'Con Poder & Motivado', theme: 'liderazgo' },
];

interface MoodEntry {
  date: string;
  mood: string;
  moodKey: string;
  note?: string;
  timestamp: number;
}

export default function AnimoPage() {
  const { playTrack } = useAudio();
  const [history, setHistory] = useState<MoodEntry[]>([]);
  const [selectedTodayMood, setSelectedTodayMood] = useState<MoodOption | null>(null);
  const [todayNote, setTodayNote] = useState('');
  const [savedToday, setSavedToday] = useState(false);
  const [viewMonth, setViewMonth] = useState(() => new Date());
  const [recommendedTrack, setRecommendedTrack] = useState<typeof SAMPLE_TRACKS[0] | null>(null);

  const todayStr = new Date().toDateString();

  useEffect(() => {
    const saved = localStorage.getItem('amp-mood-history');
    if (saved) {
      try {
        const parsed: MoodEntry[] = JSON.parse(saved);
        setHistory(parsed);
        const todayEntry = parsed.find(e => e.date === todayStr);
        if (todayEntry) {
          const matchOpt = MOODS.find(m => m.key === todayEntry.moodKey || m.emoji === todayEntry.mood);
          if (matchOpt) {
            setSelectedTodayMood(matchOpt);
            setSavedToday(true);
            const track = SAMPLE_TRACKS.find(t => t.theme === matchOpt.theme) || SAMPLE_TRACKS[0];
            setRecommendedTrack(track);
          }
        }
      } catch {}
    }
  }, [todayStr]);

  const handleLogMood = async (m: MoodOption) => {
    setSelectedTodayMood(m);
    const matchedTrack = SAMPLE_TRACKS.find(t => t.theme === m.theme) || SAMPLE_TRACKS[0];
    setRecommendedTrack(matchedTrack);

    const newEntry: MoodEntry = {
      date: todayStr,
      mood: m.emoji,
      moodKey: m.key,
      note: todayNote.trim() || undefined,
      timestamp: Date.now(),
    };

    const filtered = history.filter(h => h.date !== todayStr);
    const updated = [newEntry, ...filtered];
    setHistory(updated);
    localStorage.setItem('amp-mood-history', JSON.stringify(updated));
    setSavedToday(true);

    // Call existing AMP backend /api/v1/amp/moods if available
    try {
      const token = localStorage.getItem('amp_token');
      await fetch('http://localhost:8000/api/v1/amp/moods', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          mood: m.key,
          emoji: m.emoji,
          note: todayNote.trim() || undefined,
          date: new Date().toISOString().split('T')[0],
        }),
      });
    } catch {
      // Local fallback stores correctly
    }
  };

  const daysInMonth = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 0).getDate();
  const firstDayOfWeek = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1).getDay();
  const monthName = viewMonth.toLocaleDateString('es', { month: 'long', year: 'numeric' });

  const calendarDays = useMemo(() => {
    const days: { date: string; day: number; mood?: string }[] = [];
    for (let d = 1; d <= daysInMonth; d++) {
      const dateObj = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), d);
      const str = dateObj.toDateString();
      const entry = history.find(h => h.date === str);
      days.push({ date: str, day: d, mood: entry?.mood });
    }
    return days;
  }, [viewMonth, history, daysInMonth]);

  const prevMonth = () => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1));
  const nextMonth = () => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1));

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 md:py-14">
      {/* ── HEADER ── */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Ritual Diario de Consciencia
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-3">
          ¿Cómo te sientes hoy?
        </h1>
        <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
          Haz una pausa de 10 segundos. Nombra tu emoción y recibe al instante la meditación que armonizará tu frecuencia interior.
        </p>
      </div>

      {/* ── INTERACTIVE MOOD SELECTOR CARD ── */}
      <div className="bg-white dark:bg-[#1E1B3A] p-6 sm:p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm mb-12">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {MOODS.map((m) => {
            const isSelected = selectedTodayMood?.key === m.key;
            return (
              <button
                key={m.key}
                onClick={() => handleLogMood(m)}
                className={`p-4 rounded-2xl border text-center transition-all flex flex-col items-center justify-center gap-2 ${
                  isSelected
                    ? 'border-[#E0A526] bg-[#E0A526]/10 shadow-sm scale-105'
                    : 'border-[#F0E6D8] dark:border-[#2E2A54] bg-[#FFF9F1] dark:bg-[#14122B] hover:border-[#E0A526] hover:bg-black/5'
                }`}
              >
                <span className="text-3xl">{m.emoji}</span>
                <span className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                  {m.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Optional Reflection Note */}
        <div className="space-y-2 mb-6">
          <label className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8] flex items-center gap-1.5">
            <PenLine size={14} className="text-[#E0A526]" /> Nota de reflexión breve (opcional):
          </label>
          <input
            type="text"
            placeholder="¿Qué pensamiento o situación resalta en ti en este instante?"
            value={todayNote}
            onChange={(e) => setTodayNote(e.target.value)}
            className="w-full px-4 py-2.5 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-xs text-[#2B2622] dark:text-[#F4EFE8] focus:outline-none focus:border-[#E0A526]"
          />
        </div>

        {/* Saved confirmation & recommended track */}
        {savedToday && recommendedTrack && (
          <div className="p-6 rounded-2xl bg-[#E4EDE6]/50 dark:bg-[#14122B] border border-[#7E9F84]/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-up">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#7E9F84] text-white">
                  ✓ Registro Guardado
                </span>
                <span className="text-xs font-semibold text-[#5A7A60] dark:text-[#9DBFA2]">
                  Práctica recomendada para tu estado:
                </span>
              </div>
              <h4 className="font-serif font-bold text-lg text-[#2B2622] dark:text-[#F4EFE8]">
                {recommendedTrack.title} ({recommendedTrack.durationLabel})
              </h4>
              <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9]">
                Guía: {recommendedTrack.coach} · Tema: {recommendedTrack.theme}
              </p>
            </div>

            <button
              onClick={() => playTrack(recommendedTrack)}
              className="px-6 py-3 rounded-full bg-[#E0A526] hover:bg-[#B8860B] text-white font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow shrink-0"
            >
              <Play size={14} className="fill-white" /> Escuchar Ahora
            </button>
          </div>
        )}
      </div>

      {/* ── CALENDAR VIEW OF MOODS ── */}
      <div className="bg-white dark:bg-[#1E1B3A] p-6 sm:p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm mb-12">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-serif text-xl font-bold text-[#2B2622] dark:text-[#F4EFE8] flex items-center gap-2 capitalize">
            <Calendar size={18} className="text-[#E0A526]" /> {monthName}
          </h3>
          <div className="flex gap-2">
            <button onClick={prevMonth} className="p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 text-[#6B625A] dark:text-[#B9B2C9]">
              <ChevronLeft size={18} />
            </button>
            <button onClick={nextMonth} className="p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 text-[#6B625A] dark:text-[#B9B2C9]">
              <ChevronRight size={18} />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-7 gap-2 mb-2 text-center text-xs font-bold text-[#6B625A] dark:text-[#B9B2C9]">
          {['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map(d => (
            <div key={d}>{d}</div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: firstDayOfWeek }).map((_, i) => (
            <div key={`empty-${i}`} className="aspect-square" />
          ))}

          {calendarDays.map((d) => (
            <div
              key={d.day}
              className="aspect-square rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] flex flex-col items-center justify-center p-1"
            >
              <span className="text-[10px] text-[#6B625A] dark:text-[#B9B2C9] mb-0.5">{d.day}</span>
              {d.mood ? (
                <span className="text-xl">{d.mood}</span>
              ) : (
                <span className="text-[10px] text-gray-300 dark:text-gray-600">•</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
