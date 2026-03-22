'use client';
import { useState, useEffect } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import AudioPlayer from '../../components/AudioPlayer';
import ContentCard from '../../components/ContentCard';
import { getTodayAffirmation, getTodayMeditation, getTodayLesson, MOODS, PILLAR_CONFIG } from '../../lib/data';
import type { Pillar } from '../../lib/data';
import { Share2, BookOpen, Heart } from 'lucide-react';

// ── API Wiring ──
const API = 'http://localhost:8000/api/v1/amp';

const safeFetch = async (url: string) => {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
};

const MOOD_API_MAP: Record<string, string> = {
  '😊': 'happy',
  '😌': 'peaceful',
  '😐': 'neutral',
  '😔': 'sad',
  '😤': 'frustrated',
  '😰': 'anxious',
  '🤗': 'grateful',
  '💪': 'motivated',
};

// ── Types ──
interface ContentItem {
  id: string;
  type: string;
  title: string;
  description: string;
  duration_seconds?: number;
  pillar?: string;
  premium?: boolean;
  category?: string;
  audio_url?: string;
  content_text?: string;
}

export default function DailyPage() {
  // Static fallbacks
  const fallbackAffirmation = getTodayAffirmation();
  const fallbackMeditation = getTodayMeditation();
  const fallbackLesson = getTodayLesson();

  // State
  const [affirmation, setAffirmation] = useState(fallbackAffirmation);
  const [lesson, setLesson] = useState(fallbackLesson);
  const [moodToday, setMoodToday] = useState<string | null>(null);
  const [streak, setStreak] = useState(0);
  const [showLesson, setShowLesson] = useState(false);
  const [recommendations, setRecommendations] = useState<ContentItem[]>([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [activeContent, setActiveContent] = useState<ContentItem | null>(null);

  // ── Init: streak, mood restore, backend content ──
  useEffect(() => {
    // Streak logic (localStorage)
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

    // Restore saved mood
    const todayMood = localStorage.getItem(`amp-mood-${today}`);
    if (todayMood) {
      setMoodToday(todayMood);
      // Also fetch recommendations for the restored mood
      fetchRecommendations(todayMood);
    }

    // Fetch affirmation from backend
    safeFetch(`${API}/content?type=affirmation&limit=1`).then((data) => {
      if (data && Array.isArray(data) && data.length > 0) {
        setAffirmation(data[0].title || data[0].description || data[0].content_text || fallbackAffirmation);
      } else if (data && data.title) {
        setAffirmation(data.title || data.description || data.content_text || fallbackAffirmation);
      }
    });

    // Fetch lesson from backend
    safeFetch(`${API}/content?type=lesson&limit=1`).then((data) => {
      if (data && Array.isArray(data) && data.length > 0) {
        const item = data[0];
        setLesson({
          title: item.title || fallbackLesson.title,
          read: item.duration_seconds ? `${Math.ceil(item.duration_seconds / 60)} min` : fallbackLesson.read,
          pillar: item.pillar || fallbackLesson.pillar,
          content: item.content_text || item.description || fallbackLesson.content,
        });
      } else if (data && data.title) {
        setLesson({
          title: data.title || fallbackLesson.title,
          read: data.duration_seconds ? `${Math.ceil(data.duration_seconds / 60)} min` : fallbackLesson.read,
          pillar: data.pillar || fallbackLesson.pillar,
          content: data.content_text || data.description || fallbackLesson.content,
        });
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Fetch mood-based recommendations ──
  const fetchRecommendations = async (emoji: string) => {
    const moodLabel = MOOD_API_MAP[emoji];
    if (!moodLabel) return;
    setLoadingRecs(true);
    const data = await safeFetch(`${API}/recommend?mood=${moodLabel}`);
    if (data && Array.isArray(data)) {
      setRecommendations(data.slice(0, 5));
    } else if (data && Array.isArray(data?.items)) {
      setRecommendations(data.items.slice(0, 5));
    } else if (data && Array.isArray(data?.recommendations)) {
      setRecommendations(data.recommendations.slice(0, 5));
    } else {
      setRecommendations([]);
    }
    setLoadingRecs(false);
  };

  // ── Mood selection handler ──
  const handleMood = (emoji: string) => {
    setMoodToday(emoji);
    const today = new Date().toDateString();
    localStorage.setItem(`amp-mood-${today}`, emoji);
    const history = JSON.parse(localStorage.getItem('amp-mood-history') || '[]');
    const existing = history.findIndex((h: { date: string; mood: string; timestamp: number }) => h.date === today);
    const entry = { date: today, mood: emoji, timestamp: Date.now() };
    if (existing >= 0) history[existing] = entry;
    else history.push(entry);
    localStorage.setItem('amp-mood-history', JSON.stringify(history));

    // Fetch recommendations from backend
    fetchRecommendations(emoji);
  };

  // ── Play content handler ──
  const handlePlayContent = (item: ContentItem) => {
    setActiveContent(item);
  };

  const meditation = fallbackMeditation;
  const pillar = PILLAR_CONFIG[meditation.pillar as Pillar];
  const lessonPillar = PILLAR_CONFIG[lesson.pillar as Pillar];

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <Navbar />

      <main className={`flex-1 max-w-2xl mx-auto px-4 py-8 w-full space-y-6 ${activeContent ? 'pb-32' : ''}`}>
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

          {/* Play button — opens AudioPlayer */}
          <button
            onClick={() =>
              setActiveContent({
                id: meditation.id,
                type: 'meditation',
                title: meditation.title,
                description: meditation.description,
                duration_seconds: parseDuration(meditation.duration),
                pillar: meditation.pillar,
              })
            }
            className="w-full py-3 rounded-2xl bg-gradient-to-r from-sage-light to-lavender-light text-sage-dark font-bold text-sm hover:shadow-md transition-all flex items-center justify-center gap-2"
          >
            <span className="w-10 h-10 rounded-full bg-white shadow-md flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-sage-dark ml-0.5"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>
            </span>
            <span>{meditation.title} &middot; {meditation.duration}</span>
          </button>
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

        {/* Para Ti Hoy — Mood-based Recommendations */}
        {moodToday && (
          <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-lg">✨</span>
              <h3 className="font-serif text-xl font-bold text-[#2D2A26]">Para Ti Hoy</h3>
            </div>

            {loadingRecs ? (
              <div className="flex flex-col items-center justify-center py-8 gap-2">
                <div className="w-8 h-8 rounded-full border-2 border-gold border-t-transparent animate-spin" />
                <p className="text-xs text-[#9B9590]">Buscando contenido para ti...</p>
              </div>
            ) : recommendations.length > 0 ? (
              <div className="space-y-3">
                {recommendations.map((item) => (
                  <ContentCard
                    key={item.id}
                    item={item}
                    onPlay={handlePlayContent}
                    compact
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-[#9B9590] text-center py-4">
                No hay recomendaciones disponibles en este momento. Disfruta el contenido del día.
              </p>
            )}
          </section>
        )}

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

      {/* AudioPlayer — fixed at bottom when content is active */}
      {activeContent && (
        <AudioPlayer
          title={activeContent.title}
          description={activeContent.description}
          pillar={activeContent.pillar}
          audioUrl={activeContent.audio_url}
          durationSeconds={activeContent.duration_seconds ?? 300}
          contentText={activeContent.content_text}
          onClose={() => setActiveContent(null)}
        />
      )}
    </div>
  );
}

// ── Helpers ──

/** Parse "5 min" / "12 min" strings to seconds */
function parseDuration(durationStr: string): number {
  const match = durationStr.match(/(\d+)\s*min/);
  if (match) return parseInt(match[1]) * 60;
  return 300; // default 5 min
}
