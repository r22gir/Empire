'use client';
import { useState, useEffect } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import { COURSES, PILLAR_CONFIG } from '../../lib/data';
import type { Pillar } from '../../lib/data';
import { User, Trophy, Settings, Bell, Globe, LogOut, ChevronRight, Crown, Heart } from 'lucide-react';

export default function PerfilPage() {
  const [name, setName] = useState('');
  const [editing, setEditing] = useState(false);
  const [streak, setStreak] = useState(0);
  const [moodCount, setMoodCount] = useState(0);
  const [completedLessons, setCompletedLessons] = useState<Record<string, boolean>>({});
  const [lang, setLang] = useState('ES');
  const [notifs, setNotifs] = useState(true);

  useEffect(() => {
    setName(localStorage.getItem('amp-name') || '');
    setStreak(parseInt(localStorage.getItem('amp-streak') || '0'));
    const history = JSON.parse(localStorage.getItem('amp-mood-history') || '[]');
    setMoodCount(history.length);
    const lessons = localStorage.getItem('amp-completed-lessons');
    if (lessons) setCompletedLessons(JSON.parse(lessons));
  }, []);

  const saveName = () => {
    localStorage.setItem('amp-name', name);
    setEditing(false);
  };

  const totalLessons = COURSES.reduce((sum, c) => sum + c.lessons.length, 0);
  const completedCount = Object.values(completedLessons).filter(Boolean).length;

  const coursesStarted = COURSES.filter(c =>
    c.lessons.some((_, i) => completedLessons[`${c.id}-${i + 1}`])
  );

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <Navbar />
      <main className="flex-1 max-w-2xl mx-auto px-4 py-8 w-full space-y-6">

        {/* Profile header */}
        <section className="bg-gradient-to-br from-gold-light/40 to-sunrise/10 rounded-3xl p-8 text-center border border-gold/20">
          <div className="w-20 h-20 rounded-full bg-white shadow-lg shadow-gold/20 flex items-center justify-center mx-auto mb-4">
            <User size={36} className="text-gold" />
          </div>

          {editing ? (
            <div className="flex items-center justify-center gap-2 mb-2">
              <input value={name} onChange={e => setName(e.target.value)}
                placeholder="Tu nombre"
                className="px-4 py-2 rounded-xl border border-gold/30 bg-white text-center text-lg font-bold text-[#2D2A26] focus:outline-none focus:border-gold w-48" />
              <button onClick={saveName}
                className="px-4 py-2 rounded-xl bg-gold text-white font-bold text-sm">
                Guardar
              </button>
            </div>
          ) : (
            <h2 className="font-serif text-2xl font-bold text-[#2D2A26] mb-1 cursor-pointer" onClick={() => setEditing(true)}>
              {name || 'Toca para agregar tu nombre'}
            </h2>
          )}

          <p className="text-sm text-[#9B9590]">Miembro gratuito</p>

          <div className="flex items-center justify-center gap-6 mt-6">
            <div className="text-center">
              <div className="flex items-center justify-center gap-1 text-xl font-bold text-[#2D2A26]">
                <span className="streak-fire">🔥</span> {streak}
              </div>
              <div className="text-xs text-[#9B9590]">Racha</div>
            </div>
            <div className="w-px h-8 bg-gold/20" />
            <div className="text-center">
              <div className="text-xl font-bold text-[#2D2A26]">{moodCount}</div>
              <div className="text-xs text-[#9B9590]">Ánimos</div>
            </div>
            <div className="w-px h-8 bg-gold/20" />
            <div className="text-center">
              <div className="text-xl font-bold text-[#2D2A26]">{completedCount}</div>
              <div className="text-xs text-[#9B9590]">Lecciones</div>
            </div>
          </div>
        </section>

        {/* Progress overview */}
        <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
          <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-4 flex items-center gap-2">
            <Trophy size={20} className="text-gold" /> Mi Progreso
          </h3>

          <div className="mb-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-[#5C5650]">Lecciones completadas</span>
              <span className="text-sm font-bold text-gold-dark">{completedCount}/{totalLessons}</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-sand overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-gold to-sunrise transition-all"
                style={{ width: `${totalLessons > 0 ? (completedCount / totalLessons) * 100 : 0}%` }} />
            </div>
          </div>

          {coursesStarted.length > 0 ? (
            <div className="space-y-2">
              {coursesStarted.map(c => {
                const pillar = PILLAR_CONFIG[c.pillar as Pillar];
                const done = c.lessons.filter((_, i) => completedLessons[`${c.id}-${i + 1}`]).length;
                const pct = Math.round((done / c.lessons.length) * 100);
                const isComplete = done === c.lessons.length;

                return (
                  <a key={c.id} href={`/retos?id=${c.id}`}
                    className="flex items-center gap-3 p-3 rounded-2xl hover:bg-gold/5 transition-all no-underline">
                    <span className="text-xl">{pillar.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-bold text-[#2D2A26] truncate">{c.title}</div>
                      <div className="w-full h-1.5 rounded-full bg-sand overflow-hidden mt-1">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: pillar.color }} />
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      {isComplete ? (
                        <span className="text-xs font-bold text-sage bg-sage-light px-2 py-1 rounded-full">Completado ✓</span>
                      ) : (
                        <span className="text-xs text-[#9B9590]">{pct}%</span>
                      )}
                    </div>
                  </a>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-[#9B9590] text-center py-4">
              Aún no has empezado ningún reto. <a href="/retos" className="text-gold-dark font-bold">Comienza uno hoy →</a>
            </p>
          )}
        </section>

        {/* Upgrade CTA */}
        <section className="bg-gradient-to-r from-gold/10 to-sunrise/10 rounded-3xl p-6 border border-gold/20">
          <div className="flex items-start gap-4">
            <Crown size={28} className="text-gold shrink-0 mt-1" />
            <div>
              <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-1">Pasa a Premium</h3>
              <p className="text-sm text-[#5C5650] mb-3">Desbloquea todos los retos, meditaciones y micro-lecciones. Sin límites.</p>
              <button className="px-5 py-2.5 rounded-2xl bg-gradient-to-r from-gold to-sunrise text-white font-bold text-sm shadow-md hover:shadow-lg transition-all">
                $9.99/mes — Obtener Premium
              </button>
            </div>
          </div>
        </section>

        {/* Settings */}
        <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
          <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-4 flex items-center gap-2">
            <Settings size={20} className="text-[#9B9590]" /> Ajustes
          </h3>

          <div className="space-y-1">
            <div className="flex items-center justify-between p-3 rounded-2xl hover:bg-gold/5 transition-all cursor-pointer">
              <div className="flex items-center gap-3">
                <Bell size={18} className="text-[#9B9590]" />
                <span className="text-sm font-semibold text-[#2D2A26]">Notificaciones</span>
              </div>
              <button onClick={() => setNotifs(!notifs)}
                className={`w-10 h-6 rounded-full transition-all relative ${notifs ? 'bg-sage' : 'bg-sand'}`}>
                <div className={`w-4 h-4 rounded-full bg-white shadow-sm absolute top-1 transition-all ${notifs ? 'left-5' : 'left-1'}`} />
              </button>
            </div>

            <div className="flex items-center justify-between p-3 rounded-2xl hover:bg-gold/5 transition-all cursor-pointer">
              <div className="flex items-center gap-3">
                <Globe size={18} className="text-[#9B9590]" />
                <span className="text-sm font-semibold text-[#2D2A26]">Idioma</span>
              </div>
              <button onClick={() => setLang(l => l === 'ES' ? 'EN' : 'ES')}
                className="text-sm font-bold text-gold-dark bg-gold/10 px-3 py-1 rounded-lg">
                {lang}
              </button>
            </div>

            <div className="flex items-center justify-between p-3 rounded-2xl hover:bg-gold/5 transition-all cursor-pointer">
              <div className="flex items-center gap-3">
                <Heart size={18} className="text-[#9B9590]" />
                <span className="text-sm font-semibold text-[#2D2A26]">Sobre AMP</span>
              </div>
              <ChevronRight size={16} className="text-[#9B9590]" />
            </div>

            <div className="flex items-center justify-between p-3 rounded-2xl hover:bg-red-50 transition-all cursor-pointer">
              <div className="flex items-center gap-3">
                <LogOut size={18} className="text-red-400" />
                <span className="text-sm font-semibold text-red-400">Cerrar sesión</span>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
