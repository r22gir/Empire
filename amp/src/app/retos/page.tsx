'use client';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import { COURSES, PILLAR_CONFIG } from '../../lib/data';
import type { Pillar } from '../../lib/data';
import { BookOpen, Users, Star, Lock, ChevronLeft, Check, Clock, ArrowRight } from 'lucide-react';

export default function RetosPage() {
  const searchParams = useSearchParams();
  const courseId = searchParams.get('id');
  const [filter, setFilter] = useState<'all' | Pillar>('all');
  const [selectedCourse, setSelectedCourse] = useState<typeof COURSES[0] | null>(null);
  const [completedLessons, setCompletedLessons] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (courseId) {
      const found = COURSES.find(c => c.id === courseId);
      if (found) setSelectedCourse(found);
    }
    const saved = localStorage.getItem('amp-completed-lessons');
    if (saved) setCompletedLessons(JSON.parse(saved));
  }, [courseId]);

  const toggleLesson = (courseId: string, day: number) => {
    const key = `${courseId}-${day}`;
    const updated = { ...completedLessons, [key]: !completedLessons[key] };
    setCompletedLessons(updated);
    localStorage.setItem('amp-completed-lessons', JSON.stringify(updated));
  };

  const filtered = filter === 'all' ? COURSES : COURSES.filter(c => c.pillar === filter);

  // ── Course Detail View ──
  if (selectedCourse) {
    const pillar = PILLAR_CONFIG[selectedCourse.pillar as Pillar];
    const completedCount = selectedCourse.lessons.filter((_, i) =>
      completedLessons[`${selectedCourse.id}-${i + 1}`]
    ).length;
    const progressPct = Math.round((completedCount / selectedCourse.lessons.length) * 100);

    return (
      <div className="min-h-screen flex flex-col bg-warmwhite">
        <Navbar />
        <main className="flex-1 max-w-2xl mx-auto px-4 py-8 w-full">
          <button onClick={() => setSelectedCourse(null)}
            className="flex items-center gap-1 text-sm text-gold-dark font-semibold mb-6 hover:text-gold">
            <ChevronLeft size={16} /> Todos los Retos
          </button>

          {/* Course header */}
          <div className={`rounded-3xl p-8 bg-gradient-to-br ${pillar.gradient} border border-white/60 mb-6`}>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-2xl">{pillar.icon}</span>
              <span className="text-xs font-bold px-2 py-1 rounded-full" style={{ color: pillar.color, background: pillar.color + '20' }}>
                {pillar.label}
              </span>
              {selectedCourse.premium && (
                <span className="text-xs font-bold text-sunrise bg-sunrise/10 px-2 py-1 rounded-full ml-auto">Premium</span>
              )}
            </div>
            <h1 className="font-serif text-3xl font-bold text-[#2D2A26] mb-2">{selectedCourse.title}</h1>
            <p className="text-[#5C5650] leading-relaxed mb-4">{selectedCourse.description}</p>
            <div className="flex items-center gap-4 text-sm text-[#9B9590]">
              <span className="flex items-center gap-1"><BookOpen size={14} /> {selectedCourse.days} días</span>
              <span className="flex items-center gap-1"><Users size={14} /> {selectedCourse.enrolled.toLocaleString()} inscritos</span>
              <span className="flex items-center gap-1"><Star size={14} className="text-gold" /> {selectedCourse.rating}</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="bg-white rounded-2xl p-4 border border-gold-light/30 mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-[#2D2A26]">Tu Progreso</span>
              <span className="text-sm font-bold" style={{ color: pillar.color }}>{progressPct}%</span>
            </div>
            <div className="w-full h-3 rounded-full bg-sand overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%`, background: `linear-gradient(to right, ${pillar.color}, ${pillar.color}dd)` }} />
            </div>
            <p className="text-xs text-[#9B9590] mt-1">{completedCount} de {selectedCourse.lessons.length} lecciones completadas</p>
          </div>

          {/* Lessons list */}
          <div className="space-y-2">
            {selectedCourse.lessons.map((lesson, i) => {
              const isCompleted = completedLessons[`${selectedCourse.id}-${lesson.day}`];
              const isLocked = selectedCourse.premium && i > 2;

              return (
                <div key={i}
                  className={`rounded-2xl p-4 border transition-all ${
                    isCompleted
                      ? 'bg-sage-light/50 border-sage/30'
                      : isLocked
                        ? 'bg-sand/30 border-gold-light/20 opacity-60'
                        : 'bg-white border-gold-light/30 hover:border-gold/30'
                  }`}>
                  <div className="flex items-center gap-3">
                    {isLocked ? (
                      <div className="w-8 h-8 rounded-full bg-gold-light/50 flex items-center justify-center shrink-0">
                        <Lock size={14} className="text-gold" />
                      </div>
                    ) : (
                      <button onClick={() => toggleLesson(selectedCourse.id, lesson.day)}
                        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all ${
                          isCompleted
                            ? 'bg-sage text-white'
                            : 'border-2 border-gold-light hover:border-gold'
                        }`}>
                        {isCompleted && <Check size={14} />}
                      </button>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className={`text-sm font-bold ${isCompleted ? 'text-sage-dark' : 'text-[#2D2A26]'}`}>
                        {lesson.title}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-[#9B9590] mt-0.5">
                        <Clock size={10} /> {lesson.duration}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {selectedCourse.premium && (
            <div className="mt-6 bg-gradient-to-r from-gold/10 to-sunrise/10 rounded-2xl p-6 text-center border border-gold/20">
              <Lock size={24} className="text-gold mx-auto mb-2" />
              <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-1">Contenido Premium</h3>
              <p className="text-sm text-[#9B9590] mb-4">Desbloquea todas las lecciones con AMP Premium</p>
              <button className="px-6 py-3 rounded-2xl bg-gradient-to-r from-gold to-sunrise text-white font-bold shadow-md hover:shadow-lg transition-all">
                Obtener Premium — $9.99/mes
              </button>
            </div>
          )}
        </main>
        <Footer />
      </div>
    );
  }

  // ── Course List View ──
  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <Navbar />
      <main className="flex-1 max-w-5xl mx-auto px-4 py-8 w-full">
        <div className="text-center mb-8">
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#2D2A26] mb-3">Retos AMP</h1>
          <p className="text-[#9B9590] text-lg">Desafíos transformadores. Un día a la vez.</p>
        </div>

        {/* Filter */}
        <div className="flex items-center justify-center gap-2 mb-8 flex-wrap">
          <button onClick={() => setFilter('all')}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${filter === 'all' ? 'bg-gold/15 text-gold-dark border border-gold/30' : 'text-[#9B9590] hover:text-[#5C5650] border border-transparent'}`}>
            Todos
          </button>
          {(Object.entries(PILLAR_CONFIG) as [Pillar, typeof PILLAR_CONFIG.mentalidad][]).map(([key, p]) => (
            <button key={key} onClick={() => setFilter(key)}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center gap-1.5 ${filter === key ? 'border' : 'border border-transparent'}`}
              style={filter === key ? { color: p.color, background: p.color + '15', borderColor: p.color + '30' } : { color: '#9B9590' }}>
              {p.icon} {p.label}
            </button>
          ))}
        </div>

        {/* Course grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map(c => {
            const pillar = PILLAR_CONFIG[c.pillar as Pillar];
            const completedCount = c.lessons.filter((_, i) => completedLessons[`${c.id}-${i + 1}`]).length;
            const started = completedCount > 0;

            return (
              <div key={c.id} onClick={() => setSelectedCourse(c)}
                className="bg-white rounded-3xl p-6 border border-gold-light/30 hover:shadow-lg hover:border-gold/30 transition-all cursor-pointer group">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-xl">{pillar.icon}</span>
                  <span className="text-xs font-bold px-2 py-1 rounded-full" style={{ color: pillar.color, background: pillar.color + '15' }}>
                    {pillar.label}
                  </span>
                  {c.premium && (
                    <span className="text-xs font-bold text-sunrise bg-sunrise/10 px-2 py-1 rounded-full ml-auto flex items-center gap-1">
                      <Lock size={10} /> Premium
                    </span>
                  )}
                </div>
                <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-2 group-hover:text-gold-dark transition-colors">{c.title}</h3>
                <p className="text-sm text-[#9B9590] mb-4 leading-relaxed line-clamp-2">{c.description}</p>

                {started && (
                  <div className="mb-3">
                    <div className="w-full h-1.5 rounded-full bg-sand overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${(completedCount / c.lessons.length) * 100}%`, background: pillar.color }} />
                    </div>
                    <p className="text-[10px] text-[#9B9590] mt-1">{completedCount}/{c.lessons.length} completados</p>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-xs text-[#9B9590]">
                    <span>{c.days} días</span>
                    <span className="flex items-center gap-1"><Star size={10} className="text-gold" /> {c.rating}</span>
                  </div>
                  <span className="text-xs font-bold text-gold-dark group-hover:translate-x-1 transition-transform flex items-center gap-1">
                    {started ? 'Continuar' : 'Empezar'} <ArrowRight size={12} />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </main>
      <Footer />
    </div>
  );
}
