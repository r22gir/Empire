'use client';
import { useState, useEffect, useRef } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import { getTodayAffirmation, getTodayMeditation, getTodayLesson, MOODS, PILLAR_CONFIG } from '../../lib/data';
import type { Pillar } from '../../lib/data';
import { Play, Pause, SkipForward, Share2, Flame, BookOpen, Heart } from 'lucide-react';

export default function DailyPage() {
  const affirmation = getTodayAffirmation();
  const meditation = getTodayMeditation();
  const lesson = getTodayLesson();

  const [moodToday, setMoodToday] = useState<string | null>(null);
  const [streak, setStreak] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [showLesson, setShowLesson] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('amp-streak');
    const lastVisit = localStorage.getItem('amp-last-visit');
    const today = new Date().toDateString();

    if (lastVisit === today) {
      setStreak(parseInt(saved || '0'));
    } else if (lastVisit) {
      const last = new Date(lastVisit);
      const diff = Math.floor((Date.now() - last.getTime()) / 86400000);
      if (diff === 1) {
        const newStreak = (parseInt(saved || '0')) + 1;
        setStreak(newStreak);
        localStorage.setItem('amp-streak', String(newStreak));
      } else {
        setStreak(1);
        localStorage.setItem('amp-streak', '1');
      }
    } else {
      setStreak(1);
      localStorage.setItem('amp-streak', '1');
    }
    localStorage.setItem('amp-last-visit', today);

    const todayMood = localStorage.getItem(`amp-mood-${today}`);
    if (todayMood) setMoodToday(todayMood);
  }, []);

  const handleMood = (emoji: string) => {
    setMoodToday(emoji);
    const today = new Date().toDateString();
    localStorage.setItem(`amp-mood-${today}`, emoji);
    const history = JSON.parse(localStorage.getItem('amp-mood-history') || '[]');
    const existing = history.findIndex((h: any) => h.date === today);
    const entry = { date: today, mood: emoji, timestamp: Date.now() };
    if (existing >= 0) history[existing] = entry;
    else history.push(entry);
    localStorage.setItem('amp-mood-history', JSON.stringify(history));
  };

  const togglePlay = () => {
    if (playing) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setPlaying(false);
    } else {
      setPlaying(true);
      intervalRef.current = setInterval(() => {
        setProgress(p => {
          if (p >= 100) {
            clearInterval(intervalRef.current!);
            setPlaying(false);
            return 100;
          }
          return p + 0.5;
        });
      }, 300);
    }
  };

  const pillar = PILLAR_CONFIG[meditation.pillar as Pillar];
  const lessonPillar = PILLAR_CONFIG[lesson.pillar as Pillar];

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <Navbar />

      <main className="flex-1 max-w-2xl mx-auto px-4 py-8 w-full space-y-6">
        {/* Streak */}
        <div className="text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-sunrise/10 border border-sunrise/20">
            <span className="streak-fire text-lg">🔥</span>
            <span className="font-bold text-sunrise-dark text-sm">{streak} {streak === 1 ? 'día' : 'días'} seguidos</span>
          </div>
        </div>

        {/* Affirmation */}
        <section className="bg-gradient-to-br from-gold-light/40 to-sunrise/10 rounded-3xl p-8 text-center border border-gold/20">
          <p className="text-xs font-bold text-gold tracking-[3px] mb-4">AFIRMACIÓN DEL DÍA</p>
          <p className="font-serif text-2xl md:text-3xl italic text-[#2D2A26] leading-relaxed mb-6">
            &ldquo;{affirmation}&rdquo;
          </p>
          <button className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white/80 text-gold-dark text-sm font-semibold hover:bg-white transition-all border border-gold/20">
            <Share2 size={14} /> Compartir
          </button>
        </section>

        {/* Meditation Player */}
        <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-lg">{pillar.icon}</span>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ color: pillar.color, background: pillar.color + '15' }}>
              {pillar.label}
            </span>
          </div>
          <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-1">{meditation.title}</h3>
          <p className="text-sm text-[#9B9590] mb-4">{meditation.description}</p>

          {/* Player UI */}
          <div className="bg-gradient-to-r from-sage-light to-lavender-light rounded-2xl p-5">
            <div className="flex items-center gap-4 mb-3">
              <button onClick={togglePlay}
                className="w-12 h-12 rounded-full bg-white shadow-md flex items-center justify-center hover:scale-105 transition-transform">
                {playing ? <Pause size={20} className="text-sage-dark" /> : <Play size={20} className="text-sage-dark ml-0.5" />}
              </button>
              <div className="flex-1">
                <div className="text-sm font-bold text-[#2D2A26]">{meditation.title}</div>
                <div className="text-xs text-[#9B9590]">{meditation.duration} · Meditación guiada</div>
              </div>
              <button className="p-2 text-[#9B9590] hover:text-sage-dark">
                <SkipForward size={18} />
              </button>
            </div>
            <div className="w-full h-2 rounded-full bg-white/60 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-sage to-lavender transition-all duration-300"
                style={{ width: `${progress}%` }} />
            </div>
            <div className="flex justify-between mt-1 text-[10px] text-[#9B9590] font-mono">
              <span>{Math.floor(progress * 0.15)}:{String(Math.floor((progress * 9) % 60)).padStart(2, '0')}</span>
              <span>{meditation.duration}</span>
            </div>
          </div>
        </section>

        {/* Mood Check-in */}
        <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
          <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-2">¿Cómo te sientes hoy?</h3>
          <p className="text-sm text-[#9B9590] mb-4">Tu estado de ánimo importa. Selecciona cómo te sientes.</p>

          {moodToday ? (
            <div className="text-center py-4">
              <span className="text-5xl mood-float block mb-3">{moodToday}</span>
              <p className="text-sm font-semibold text-[#5C5650]">
                {MOODS.find(m => m.emoji === moodToday)?.label || 'Registrado'}
              </p>
              <p className="text-xs text-[#9B9590] mt-1">Puedes cambiar tu ánimo tocando otro emoji</p>
            </div>
          ) : null}

          <div className="grid grid-cols-4 gap-3">
            {MOODS.map(m => (
              <button key={m.emoji} onClick={() => handleMood(m.emoji)}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-2xl transition-all hover:scale-105
                  ${moodToday === m.emoji
                    ? 'bg-gold/10 border-2 border-gold shadow-sm'
                    : 'bg-sand/50 border-2 border-transparent hover:bg-gold/5'}`}>
                <span className="text-2xl">{m.emoji}</span>
                <span className="text-[10px] font-semibold text-[#5C5650]">{m.label}</span>
              </button>
            ))}
          </div>

          {moodToday && (
            <div className="mt-4 text-center">
              <a href="/animo" className="text-sm text-gold-dark font-bold hover:text-gold no-underline">
                Ver mi historial de ánimo →
              </a>
            </div>
          )}
        </section>

        {/* Micro Lesson */}
        <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <BookOpen size={18} className="text-gold" />
              <h3 className="font-serif text-xl font-bold text-[#2D2A26]">Micro-Lección</h3>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ color: lessonPillar.color, background: lessonPillar.color + '15' }}>
              {lessonPillar.icon} {lessonPillar.label}
            </span>
          </div>

          <h4 className="font-bold text-[#2D2A26] mb-1">{lesson.title}</h4>
          <p className="text-xs text-[#9B9590] mb-3">Lectura de {lesson.read}</p>

          {showLesson ? (
            <div className="bg-cream rounded-2xl p-4 text-sm text-[#5C5650] leading-relaxed">
              {lesson.content}
            </div>
          ) : (
            <button onClick={() => setShowLesson(true)}
              className="w-full py-3 rounded-2xl border-2 border-gold/20 text-gold-dark font-bold text-sm hover:bg-gold/5 transition-all">
              Leer lección del día
            </button>
          )}
        </section>

        {/* Motivation footer */}
        <div className="text-center py-4">
          <p className="text-sm text-[#9B9590] flex items-center justify-center gap-1.5">
            <Heart size={14} className="text-sunrise" /> Tú puedes. Un día a la vez.
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
}
