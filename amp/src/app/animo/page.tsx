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
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12 md:py-20">
      {/* ── HEADER ── */}
      <div className="text-center max-w-2xl mx-auto mb-14">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Ritual Diario de Consciencia
        </div>
        <h1 className="font-serif text-3xl sm:text-5xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
          ¿Cómo te sientes hoy?
        </h1>
        <p className="text-sm sm:text-base text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
          Haz una pausa de 10 segundos. Nombra tu emoción y recibe al instante la meditación que armonizará tu frecuencia interior.
        </p>
      </div>

      {/* ── INTERACTIVE MOOD SELECTOR CARD ── */}
      <div className="glass-card p-6 sm:p-10 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] shadow-xl mb-14">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5 mb-8">
          {MOODS.map((m) => {
            const isSelected = selectedTodayMood?.key === m.key;
            return (
              <button
                key={m.key}
                onClick={() => handleLogMood(m)}
                className={`p-4 rounded-2xl border text-center transition-all flex flex-col items-center justify-center gap-2.5 ${
                  isSelected
                    ? 'border-[#E0A526] bg-[#E0A526]/15 shadow-md scale-105 ring-2 ring-[#E0A526]/20'
                    : 'border-[#EFE6D8] dark:border-[#2B254E] bg-white/70 dark:bg-white/5 hover:border-[#E0A526] hover:bg-black/5'
                }`}
              >
                <span className="text-3xl">{m.emoji}</span>
                <span className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                  {m.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Optional Reflection Note */}
        <div className="space-y-2 mb-8">
          <label className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE] flex items-center gap-1.5">
            <PenLine size={14} className="text-[#E0A526]" /> Nota de reflexión breve (opcional):
          </label>
          <input
            type="text"
            placeholder="¿Qué pensamiento o situación resalta en ti en este instante?"
            value={todayNote}
            onChange={(e) => setTodayNote(e.target.value)}
            className="w-full px-4 py-3 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-xs text-[#1E1A17] dark:text-[#F6F3EE] focus:outline-none focus:border-[#E0A526]"
          />
        </div>

        {/* Saved confirmation & recommended track */}
        {savedToday && recommendedTrack && (
          <div className="p-6 rounded-2xl bg-[#7E9F84]/15 border border-[#7E9F84]/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-up">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#7E9F84] text-white">
                  ✓ Registro Guardado
                </span>
                <span className="text-xs font-semibold text-[#5A7A60] dark:text-[#9DBFA2]">
                  Práctica recomendada para tu momento:
                </span>
              </div>
              <h4 className="font-serif font-bold text-lg text-[#1E1A17] dark:text-[#F6F3EE]">
                {recommendedTrack.title} ({recommendedTrack.durationLabel})
              </h4>
              <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5]">
                Guía: {recommendedTrack.coach} · Tema: {recommendedTrack.theme}
              </p>
            </div>

            <button
              onClick={() => playTrack(recommendedTrack)}
              className="w-full sm:w-auto px-6 py-3 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-md hover:scale-105 active:scale-95 transition-all"
            >
              <Play size={14} className="fill-current" /> Escuchar Ahora
            </button>
          </div>
        )}
      </div>

      {/* ── CALENDAR VIEW (MONTHLY EMOTIONAL JOURNEY) ── */}
      <div className="glass-card p-6 sm:p-8 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] shadow-md">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Calendar size={18} className="text-[#E0A526]" />
            <h3 className="font-serif font-bold text-lg text-[#1E1A17] dark:text-[#F6F3EE] capitalize">
              {monthName}
            </h3>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={prevMonth}
              className="p-1.5 rounded-xl hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5]"
              aria-label="Mes anterior"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              onClick={nextMonth}
              className="p-1.5 rounded-xl hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5]"
              aria-label="Mes siguiente"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>

        {/* Days of week header */}
        <div className="grid grid-cols-7 gap-2 text-center text-xs font-bold text-[#5C544D] dark:text-[#B4ACC5] mb-2">
          {['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map(day => (
            <div key={day} className="py-1">{day}</div>
          ))}
        </div>

        {/* Calendar grid */}
        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: firstDayOfWeek }).map((_, i) => (
            <div key={`empty-${i}`} className="h-12 rounded-xl bg-transparent" />
          ))}

          {calendarDays.map((item) => {
            const isToday = item.date === todayStr;
            return (
              <div
                key={item.day}
                className={`h-12 sm:h-14 rounded-2xl border flex flex-col items-center justify-center relative p-1 transition-all ${
                  isToday
                    ? 'border-[#E0A526] bg-[#E0A526]/10 font-bold'
                    : 'border-black/5 dark:border-white/5 bg-white/40 dark:bg-white/5'
                }`}
              >
                <span className="text-[10px] text-[#5C544D] dark:text-[#B4ACC5] absolute top-1 left-2">
                  {item.day}
                </span>
                {item.mood ? (
                  <span className="text-xl animate-fade-up">{item.mood}</span>
                ) : (
                  <span className="text-[10px] text-gray-300 dark:text-gray-700">•</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
