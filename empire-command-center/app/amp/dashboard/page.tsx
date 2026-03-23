'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getAmpToken, ampFetch } from '../../lib/amp-auth';
import AmpNav from '../../components/amp/AmpNav';
import {
  Flame, Sun, Heart, Brain, Crown, BookOpen, Smile, Play, Pause,
  ChevronRight, Calendar, PenLine, Target, Sparkles, Video, Star,
  Tag, ArrowRight, Clock, Search, CheckCircle, TrendingUp,
} from 'lucide-react';

const AMP_LOGO = 'https://actitudmentalpositivacom-43908122.hubspotpagebuilder.com/hubfs/main-logo-transparent-1.png';

const AFFIRMATIONS = [
  'Soy capaz de lograr todo lo que me propongo con determinacion y fe.',
  'Mi mente es poderosa y mis pensamientos crean mi realidad.',
  'Merezco amor, abundancia y felicidad en mi vida.',
  'Cada dia soy mas fuerte, mas sabio y mas resiliente.',
  'Libero todo lo que no me sirve y abro espacio para lo nuevo.',
  'Soy una fuente inagotable de creatividad y energia positiva.',
  'Mi corazon esta lleno de gratitud por las bendiciones de hoy.',
  'Confio en el proceso de la vida y me entrego al fluir.',
  'Soy luz, soy amor, soy paz. Mi presencia ilumina el mundo.',
  'Hoy elijo ser feliz, hoy elijo crecer, hoy elijo amar.',
  'Mi valor no depende de la opinion de otros, viene de mi interior.',
  'Estoy exactamente donde necesito estar en este momento.',
  'Cada desafio es una oportunidad de crecimiento y transformacion.',
  'Soy el arquitecto de mi vida y construyo con amor y proposito.',
  'La paz interior es mi superpoder y la cultivo cada dia.',
];

const MOODS = [
  { key: 'feliz', emoji: '😊', label: 'Feliz', color: '#D4A030' },
  { key: 'paz', emoji: '😌', label: 'En paz', color: '#7CB98B' },
  { key: 'neutral', emoji: '😐', label: 'Neutral', color: '#9B9590' },
  { key: 'triste', emoji: '😔', label: 'Triste', color: '#6B8EC4' },
  { key: 'frustrado', emoji: '😤', label: 'Frustrado', color: '#E07A5F' },
  { key: 'ansioso', emoji: '😰', label: 'Ansioso', color: '#9B8EC4' },
  { key: 'agradecido', emoji: '🤗', label: 'Agradecido', color: '#D4A030' },
  { key: 'motivado', emoji: '💪', label: 'Motivado', color: '#7CB98B' },
];

const MEDITATIONS = [
  { title: 'Respiracion Consciente', duration: '5 min', pillar: 'Bienestar', color: '#7CB98B' },
  { title: 'Visualizacion de Metas', duration: '10 min', pillar: 'Mentalidad', color: '#D4A030' },
  { title: 'Gratitud Profunda', duration: '7 min', pillar: 'Bienestar', color: '#7CB98B' },
  { title: 'Liderazgo Interior', duration: '12 min', pillar: 'Liderazgo', color: '#9B8EC4' },
  { title: 'Sanacion Emocional', duration: '15 min', pillar: 'Bienestar', color: '#7CB98B' },
  { title: 'Abundancia y Prosperidad', duration: '10 min', pillar: 'Mentalidad', color: '#D4A030' },
];

const MICRO_LESSONS = [
  { title: 'El Poder de la Intencion', pillar: 'Mentalidad', icon: <Brain size={16} />, color: '#D4A030', content: 'La intencion es la semilla de toda creacion. Cuando estableces una intencion clara, tu mente subconsciente comienza a trabajar para manifestarla. Hoy, escribe una intencion poderosa para tu semana.' },
  { title: 'Mindfulness en 3 Pasos', pillar: 'Bienestar', icon: <Heart size={16} />, color: '#7CB98B', content: '1. Respira profundo 3 veces. 2. Observa tus pensamientos sin juzgar. 3. Regresa al momento presente con gratitud. Practica esto cada hora hoy.' },
  { title: 'Liderazgo Consciente', pillar: 'Liderazgo', icon: <Crown size={16} />, color: '#9B8EC4', content: 'Un lider consciente primero se lidera a si mismo. Antes de tomar decisiones hoy, preguntate: Esta accion refleja mis valores mas profundos?' },
];

const BLOG_POSTS = [
  { title: 'El poder de las afirmaciones positivas en tu vida diaria', tag: 'AmorPropio', date: '5 Mar 2026', excerpt: 'Las afirmaciones positivas reprograman tu mente subconsciente. Descubre como integrarlas en tu rutina matutina.', color: '#D4A030' },
  { title: 'Como la actitud mental positiva transforma tus relaciones', tag: 'Transformacion', date: '28 Feb 2026', excerpt: 'Cuando cambias la forma en que ves el mundo, el mundo que ves cambia.', color: '#9B8EC4' },
  { title: 'Crianza consciente: 5 claves para educar hijos emocionalmente inteligentes', tag: 'Educacion Hijos', date: '20 Feb 2026', excerpt: 'La educacion emocional comienza en casa. Cinco practicas fundamentales para criar hijos resilientes.', color: '#7CB98B' },
  { title: 'De la frustracion a la motivacion: cambia tu perspectiva hoy', tag: 'Actitud', date: '15 Feb 2026', excerpt: 'La frustracion no es tu enemiga, es una senal de que algo necesita cambiar.', color: '#E07A5F' },
];

const TAG_COLORS: Record<string, string> = {
  AmorPropio: '#D4A030',
  Transformacion: '#9B8EC4',
  'Educacion Hijos': '#7CB98B',
  Actitud: '#E07A5F',
};

export default function AmpDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [moodNote, setMoodNote] = useState('');
  const [moodSaved, setMoodSaved] = useState(false);
  const [journalText, setJournalText] = useState('');
  const [gratitudeText, setGratitudeText] = useState('');
  const [journalSaved, setJournalSaved] = useState(false);
  const [expandedLesson, setExpandedLesson] = useState<number | null>(null);
  const [apiAffirmation, setApiAffirmation] = useState<string | null>(null);
  const [progressStats, setProgressStats] = useState({ lessons: 0, courses: 0 });
  const [contentSearch, setContentSearch] = useState('');
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [searching, setSearching] = useState(false);

  const dayOfYear = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86400000);
  const todayAffirmation = apiAffirmation || AFFIRMATIONS[dayOfYear % AFFIRMATIONS.length];
  const todayLesson = MICRO_LESSONS[dayOfYear % MICRO_LESSONS.length];

  useEffect(() => {
    if (!getAmpToken()) { router.push('/amp/login'); return; }
    Promise.all([
      ampFetch('/me'),
      ampFetch('/content?type=affirmation&limit=100').catch(() => []),
      ampFetch('/progress').catch(() => []),
      ampFetch('/courses').catch(() => []),
    ]).then(([u, affirmations, progress, courses]) => {
      setUser(u);
      // Pick today's affirmation from API content
      if (Array.isArray(affirmations) && affirmations.length > 0) {
        const idx = dayOfYear % affirmations.length;
        setApiAffirmation(affirmations[idx]?.content_text || affirmations[idx]?.title || null);
      }
      // Compute progress stats
      if (Array.isArray(progress)) {
        const courseIds = new Set(progress.map((p: any) => p.course_id));
        const completedCourses = Array.isArray(courses)
          ? courses.filter((c: any) => {
              const done = progress.filter((p: any) => p.course_id === c.id).length;
              return done >= (c.lesson_count || Infinity);
            }).length
          : 0;
        setProgressStats({ lessons: progress.length, courses: completedCourses });
      }
      setLoading(false);
    }).catch(() => router.push('/amp/login'));
  }, [router]);

  const searchContent = async () => {
    if (!contentSearch.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const results = await ampFetch(`/content?limit=10`);
      const filtered = Array.isArray(results)
        ? results.filter((c: any) =>
            c.title?.toLowerCase().includes(contentSearch.toLowerCase()) ||
            c.description?.toLowerCase().includes(contentSearch.toLowerCase()) ||
            c.pillar?.toLowerCase().includes(contentSearch.toLowerCase()) ||
            c.type?.toLowerCase().includes(contentSearch.toLowerCase())
          )
        : [];
      setSearchResults(filtered);
    } catch { setSearchResults([]); }
    setSearching(false);
  };

  const saveMood = async () => {
    if (!selectedMood) return;
    try {
      const mood = MOODS.find(m => m.key === selectedMood);
      await ampFetch('/moods', { method: 'POST', body: JSON.stringify({ mood: selectedMood, emoji: mood?.emoji, note: moodNote || undefined }) });
      setMoodSaved(true);
    } catch {}
  };

  const saveJournal = async () => {
    if (!journalText.trim()) return;
    try {
      await ampFetch('/journal', { method: 'POST', body: JSON.stringify({ content: journalText, gratitude: gratitudeText || undefined }) });
      setJournalSaved(true);
    } catch {}
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', background: '#FFF9F0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Flame size={32} color="#D4A030" style={{ animation: 'pulse 1.5s infinite' }} />
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#FFF9F0' }}>
      <AmpNav user={user} />
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '20px 16px 60px' }}>
        {/* Header with AMP Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <img src={AMP_LOGO} alt="AMP" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: '#2D2A26', margin: 0 }}>
              Hola, {user?.name?.split(' ')[0]} <span style={{ fontSize: 20 }}>🔥</span>
            </h1>
            <p style={{ fontSize: 12, color: '#9B9590', margin: 0 }}>
              Racha: {user?.stats?.moods || 0} dias · {new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
            </p>
          </div>
        </div>

        {/* Daily Affirmation */}
        <div style={{ background: 'linear-gradient(135deg, #D4A030, #c49028)', borderRadius: 16, padding: 24, marginBottom: 16, color: '#fff' }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, opacity: 0.8, marginBottom: 8 }}>AFIRMACION DEL DIA</div>
          <p style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, lineHeight: 1.5, margin: 0 }}>
            &ldquo;{todayAffirmation}&rdquo;
          </p>
          <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
            <button style={{ background: 'rgba(255,255,255,0.2)', border: 'none', borderRadius: 8, padding: '6px 14px', fontSize: 11, fontWeight: 600, color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Sparkles size={12} /> Repetir
            </button>
          </div>
        </div>

        {/* Progress Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
          <div style={{ background: '#fff', borderRadius: 14, padding: '14px 12px', textAlign: 'center', border: '1px solid #F5EDE0' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#D4A030' }}>{user?.stats?.moods || 0}</div>
            <div style={{ fontSize: 10, color: '#9B9590', fontWeight: 600, marginTop: 2 }}>Dias de Racha</div>
          </div>
          <div style={{ background: '#fff', borderRadius: 14, padding: '14px 12px', textAlign: 'center', border: '1px solid #F5EDE0' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#7CB98B' }}>{progressStats.lessons}</div>
            <div style={{ fontSize: 10, color: '#9B9590', fontWeight: 600, marginTop: 2 }}>Lecciones</div>
          </div>
          <div style={{ background: '#fff', borderRadius: 14, padding: '14px 12px', textAlign: 'center', border: '1px solid #F5EDE0' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#9B8EC4' }}>{progressStats.courses}</div>
            <div style={{ fontSize: 10, color: '#9B9590', fontWeight: 600, marginTop: 2 }}>Cursos Completos</div>
          </div>
        </div>

        {/* Content Search */}
        <div style={{ background: '#fff', borderRadius: 16, padding: 16, marginBottom: 16, border: '1px solid #F5EDE0' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <Search size={14} style={{ position: 'absolute', left: 12, top: 11, color: '#9B9590' }} />
              <input
                value={contentSearch}
                onChange={e => setContentSearch(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && searchContent()}
                placeholder="Buscar meditaciones, lecciones, afirmaciones..."
                style={{ width: '100%', padding: '9px 12px 9px 34px', borderRadius: 10, border: '1px solid #F5EDE0', background: '#FFF9F0', fontSize: 12, outline: 'none', boxSizing: 'border-box' }}
              />
            </div>
            <button onClick={searchContent} disabled={searching}
              style={{ background: '#D4A030', color: '#fff', border: 'none', borderRadius: 10, padding: '0 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' }}>
              {searching ? '...' : 'Buscar'}
            </button>
          </div>
          {searchResults !== null && (
            <div style={{ marginTop: 12 }}>
              {searchResults.length === 0 ? (
                <p style={{ fontSize: 12, color: '#9B9590', textAlign: 'center', margin: '8px 0' }}>No se encontraron resultados</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {searchResults.map((item: any) => (
                    <div key={item.id} style={{ background: '#FFF9F0', borderRadius: 10, padding: '10px 14px', borderLeft: `3px solid ${item.pillar === 'bienestar' ? '#7CB98B' : item.pillar === 'liderazgo' ? '#9B8EC4' : '#D4A030'}` }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                        <span style={{ fontSize: 9, fontWeight: 700, color: '#9B9590', textTransform: 'uppercase' }}>{item.type}</span>
                        <span style={{ fontSize: 9, color: '#D5D0C8' }}>·</span>
                        <span style={{ fontSize: 9, color: '#9B9590' }}>{item.pillar}</span>
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#2D2A26' }}>{item.title}</div>
                      {item.description && <div style={{ fontSize: 11, color: '#9B9590', marginTop: 2 }}>{item.description}</div>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Book Mentoring CTA */}
        <div style={{
          background: 'linear-gradient(135deg, #2D2A26 0%, #3d3530 100%)', borderRadius: 16, padding: 20, marginBottom: 16,
          display: 'flex', alignItems: 'center', gap: 16, cursor: 'pointer', border: '1px solid #D4A03030',
        }}
          onClick={() => window.open('https://actitudmentalpositiva.com/', '_blank')}
        >
          <div style={{ width: 48, height: 48, borderRadius: 14, background: '#D4A030', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <Video size={22} color="#fff" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#FFF9F0', marginBottom: 2 }}>Agendar Sesion de Mentoria</div>
            <div style={{ fontSize: 11, color: '#9B9590' }}>Primera sesion de 15 minutos GRATIS. Conecta con un mentor certificado.</div>
          </div>
          <ArrowRight size={18} color="#D4A030" />
        </div>

        {/* Mood Check-in */}
        <div style={{ background: '#fff', borderRadius: 16, padding: 20, marginBottom: 16, border: '1px solid #F5EDE0' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#9B9590', letterSpacing: 1, marginBottom: 12 }}>
            {moodSaved ? '✓ ANIMO REGISTRADO' : 'COMO TE SIENTES HOY?'}
          </div>
          {!moodSaved ? (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
                {MOODS.map(m => (
                  <button key={m.key} onClick={() => setSelectedMood(m.key)}
                    style={{
                      background: selectedMood === m.key ? m.color + '20' : '#FFF9F0',
                      border: `2px solid ${selectedMood === m.key ? m.color : '#F5EDE0'}`,
                      borderRadius: 12, padding: '10px 4px', cursor: 'pointer', textAlign: 'center',
                    }}>
                    <div style={{ fontSize: 24 }}>{m.emoji}</div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: selectedMood === m.key ? m.color : '#9B9590', marginTop: 2 }}>{m.label}</div>
                  </button>
                ))}
              </div>
              {selectedMood && (
                <>
                  <input value={moodNote} onChange={e => setMoodNote(e.target.value)} placeholder="Que causo este animo? (opcional)"
                    style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #F5EDE0', background: '#FFF9F0', fontSize: 13, outline: 'none', boxSizing: 'border-box', marginBottom: 10 }} />
                  <button onClick={saveMood}
                    style={{ background: '#D4A030', color: '#fff', border: 'none', borderRadius: 10, padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer', width: '100%' }}>
                    Guardar Animo
                  </button>
                </>
              )}
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: 12 }}>
              <div style={{ fontSize: 36 }}>{MOODS.find(m => m.key === selectedMood)?.emoji}</div>
              <p style={{ fontSize: 13, color: '#5C5650', marginTop: 8 }}>Gracias por compartir! Tu bienestar importa.</p>
            </div>
          )}
        </div>

        {/* Blog / Noticias */}
        <div style={{ background: '#fff', borderRadius: 16, padding: 20, marginBottom: 16, border: '1px solid #F5EDE0' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 1 }}>BLOG / NOTICIAS</div>
            <button onClick={() => window.open('https://actitudmentalpositiva.com/', '_blank')}
              style={{ background: 'none', border: 'none', fontSize: 11, fontWeight: 600, color: '#D4A030', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3 }}>
              Ver todos <ChevronRight size={12} />
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {BLOG_POSTS.map((post, i) => (
              <div key={i} style={{
                background: '#FFF9F0', borderRadius: 12, padding: '14px 16px', cursor: 'pointer',
                borderLeft: `3px solid ${post.color}`, transition: 'background 0.2s',
              }}
                onClick={() => window.open('https://actitudmentalpositiva.com/', '_blank')}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.background = '#FEF7EC'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.background = '#FFF9F0'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <span style={{
                    fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
                    background: (TAG_COLORS[post.tag] || '#D4A030') + '20',
                    color: TAG_COLORS[post.tag] || '#D4A030',
                  }}>
                    {post.tag}
                  </span>
                  <span style={{ fontSize: 9, color: '#9B9590' }}>{post.date}</span>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#2D2A26', marginBottom: 4, lineHeight: 1.4 }}>{post.title}</div>
                <div style={{ fontSize: 11, color: '#5C5650', lineHeight: 1.5 }}>{post.excerpt}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Meditation */}
        <div style={{ background: '#E8F5EC', borderRadius: 16, padding: 20, marginBottom: 16, border: '1px solid #7CB98B30' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#7CB98B', letterSpacing: 1, marginBottom: 12 }}>MEDITACIONES GUIADAS</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {MEDITATIONS.slice(0, 3).map((m, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#fff', borderRadius: 12, padding: '12px 14px', cursor: 'pointer' }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: m.color + '20', display: 'flex', alignItems: 'center', justifyContent: 'center', color: m.color, flexShrink: 0 }}>
                  <Play size={16} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#2D2A26' }}>{m.title}</div>
                  <div style={{ fontSize: 10, color: '#9B9590' }}>{m.pillar} · {m.duration}</div>
                </div>
                <ChevronRight size={14} color="#9B9590" />
              </div>
            ))}
          </div>
        </div>

        {/* Micro Lesson */}
        <div style={{ background: '#fff', borderRadius: 16, padding: 20, marginBottom: 16, border: '1px solid #F5EDE0' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#D4A030', letterSpacing: 1, marginBottom: 12 }}>MICRO-LECCION DEL DIA</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: todayLesson.color + '20', display: 'flex', alignItems: 'center', justifyContent: 'center', color: todayLesson.color }}>
              {todayLesson.icon}
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#2D2A26' }}>{todayLesson.title}</div>
              <div style={{ fontSize: 10, color: todayLesson.color, fontWeight: 600 }}>{todayLesson.pillar}</div>
            </div>
          </div>
          <p style={{ fontSize: 13, color: '#5C5650', lineHeight: 1.6, margin: 0 }}>{todayLesson.content}</p>
        </div>

        {/* Journal */}
        <div style={{ background: '#EDE8F5', borderRadius: 16, padding: 20, marginBottom: 16, border: '1px solid #9B8EC430' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#9B8EC4', letterSpacing: 1, marginBottom: 12 }}>
            {journalSaved ? '✓ DIARIO GUARDADO' : 'DIARIO DE HOY'}
          </div>
          {!journalSaved ? (
            <>
              <textarea value={journalText} onChange={e => setJournalText(e.target.value)}
                placeholder="Que quieres reflexionar hoy? Escribe libremente..."
                style={{ width: '100%', minHeight: 80, padding: 14, borderRadius: 12, border: '1px solid #9B8EC430', background: '#fff', fontSize: 13, outline: 'none', resize: 'vertical', boxSizing: 'border-box', marginBottom: 8, fontFamily: 'inherit', lineHeight: 1.6 }} />
              <input value={gratitudeText} onChange={e => setGratitudeText(e.target.value)}
                placeholder="🙏 Hoy estoy agradecido/a por..."
                style={{ width: '100%', padding: '10px 14px', borderRadius: 10, border: '1px solid #9B8EC430', background: '#fff', fontSize: 13, outline: 'none', boxSizing: 'border-box', marginBottom: 10 }} />
              <button onClick={saveJournal} disabled={!journalText.trim()}
                style={{ background: '#9B8EC4', color: '#fff', border: 'none', borderRadius: 10, padding: '10px 20px', fontSize: 13, fontWeight: 700, cursor: 'pointer', width: '100%', opacity: journalText.trim() ? 1 : 0.4 }}>
                <PenLine size={13} style={{ marginRight: 6, verticalAlign: 'middle' }} /> Guardar Reflexion
              </button>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: 12 }}>
              <PenLine size={24} color="#9B8EC4" />
              <p style={{ fontSize: 13, color: '#5C5650', marginTop: 8 }}>Excelente! Escribir sana el alma.</p>
            </div>
          )}
        </div>

        {/* Quick Links */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          {[
            { label: 'Cursos', icon: <BookOpen size={18} />, href: '/amp/cursos', color: '#D4A030' },
            { label: 'Retos', icon: <Target size={18} />, href: '/amp/retos', color: '#E07A5F' },
            { label: 'Animo', icon: <Calendar size={18} />, href: '/amp/animo', color: '#7CB98B' },
            { label: 'Mentoria', icon: <Video size={18} />, href: 'https://actitudmentalpositiva.com/', color: '#9B8EC4', external: true },
          ].map(link => (
            <button key={link.label} onClick={() => link.external ? window.open(link.href as string, '_blank') : router.push(link.href)}
              style={{ background: '#fff', border: '1px solid #F5EDE0', borderRadius: 14, padding: 16, textAlign: 'center', cursor: 'pointer' }}>
              <div style={{ width: 40, height: 40, borderRadius: 12, background: link.color + '15', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', color: link.color, marginBottom: 6 }}>
                {link.icon}
              </div>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#2D2A26' }}>{link.label}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
