'use client';
import { useState, useEffect, useMemo } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import { MOODS } from '../../lib/data';
import { ChevronLeft, ChevronRight, TrendingUp, Calendar, Sparkles, PenLine } from 'lucide-react';

interface MoodEntry {
  date: string;
  mood: string;
  timestamp: number;
  journal?: string;
}

export default function AnimoPage() {
  const [history, setHistory] = useState<MoodEntry[]>([]);
  const [viewMonth, setViewMonth] = useState(() => new Date());
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [journal, setJournal] = useState('');

  useEffect(() => {
    const saved = localStorage.getItem('amp-mood-history');
    if (saved) setHistory(JSON.parse(saved));
  }, []);

  const saveHistory = (updated: MoodEntry[]) => {
    setHistory(updated);
    localStorage.setItem('amp-mood-history', JSON.stringify(updated));
  };

  const daysInMonth = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 0).getDate();
  const firstDayOfWeek = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1).getDay();
  const monthName = viewMonth.toLocaleDateString('es', { month: 'long', year: 'numeric' });

  const calendarDays = useMemo(() => {
    const days: { date: string; day: number; mood?: string }[] = [];
    for (let d = 1; d <= daysInMonth; d++) {
      const dateObj = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), d);
      const dateStr = dateObj.toDateString();
      const entry = history.find(h => h.date === dateStr);
      days.push({ date: dateStr, day: d, mood: entry?.mood });
    }
    return days;
  }, [viewMonth, history, daysInMonth]);

  const prevMonth = () => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1));
  const nextMonth = () => setViewMonth(new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1));

  // Stats
  const thisMonthEntries = history.filter(h => {
    const d = new Date(h.date);
    return d.getMonth() === viewMonth.getMonth() && d.getFullYear() === viewMonth.getFullYear();
  });

  const moodCounts: Record<string, number> = {};
  thisMonthEntries.forEach(e => { moodCounts[e.mood] = (moodCounts[e.mood] || 0) + 1; });
  const topMood = Object.entries(moodCounts).sort((a, b) => b[1] - a[1])[0];

  // Weekday analysis
  const weekdayCounts: Record<number, { total: number; positive: number }> = {};
  const positiveEmojis = ['😊', '😌', '🤗', '💪'];
  history.forEach(e => {
    const day = new Date(e.date).getDay();
    if (!weekdayCounts[day]) weekdayCounts[day] = { total: 0, positive: 0 };
    weekdayCounts[day].total++;
    if (positiveEmojis.includes(e.mood)) weekdayCounts[day].positive++;
  });
  const bestDay = Object.entries(weekdayCounts)
    .map(([d, v]) => ({ day: parseInt(d), ratio: v.total > 0 ? v.positive / v.total : 0 }))
    .sort((a, b) => b.ratio - a.ratio)[0];
  const dayNames = ['Domingos', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábados'];

  const handleJournalSave = () => {
    if (!selectedDay || !journal.trim()) return;
    const updated = history.map(h =>
      h.date === selectedDay ? { ...h, journal: journal.trim() } : h
    );
    saveHistory(updated);
    setJournal('');
  };

  const selectedEntry = selectedDay ? history.find(h => h.date === selectedDay) : null;

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <Navbar />
      <main className="flex-1 max-w-2xl mx-auto px-4 py-8 w-full space-y-6">
        <div className="text-center">
          <h1 className="font-serif text-3xl font-bold text-[#2D2A26] mb-2">Tu Ánimo</h1>
          <p className="text-[#9B9590]">Observa tus emociones. Conócete mejor.</p>
        </div>

        {/* Calendar */}
        <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <button onClick={prevMonth} className="p-2 hover:bg-gold/5 rounded-xl text-[#9B9590] hover:text-gold-dark">
              <ChevronLeft size={20} />
            </button>
            <h3 className="font-serif text-xl font-bold text-[#2D2A26] capitalize">{monthName}</h3>
            <button onClick={nextMonth} className="p-2 hover:bg-gold/5 rounded-xl text-[#9B9590] hover:text-gold-dark">
              <ChevronRight size={20} />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1 mb-2">
            {['D', 'L', 'M', 'Mi', 'J', 'V', 'S'].map(d => (
              <div key={d} className="text-center text-[10px] font-bold text-[#9B9590] py-1">{d}</div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: firstDayOfWeek }).map((_, i) => <div key={`empty-${i}`} />)}
            {calendarDays.map(d => {
              const isToday = d.date === new Date().toDateString();
              const isSelected = d.date === selectedDay;
              return (
                <button key={d.day} onClick={() => setSelectedDay(d.date)}
                  className={`aspect-square rounded-xl flex items-center justify-center text-sm transition-all relative
                    ${isSelected ? 'ring-2 ring-gold bg-gold/10' : isToday ? 'bg-sunrise/10 font-bold' : 'hover:bg-gold/5'}
                    ${d.mood ? '' : 'text-[#9B9590]'}`}>
                  {d.mood ? (
                    <span className="text-lg">{d.mood}</span>
                  ) : (
                    <span className={isToday ? 'text-sunrise-dark' : ''}>{d.day}</span>
                  )}
                </button>
              );
            })}
          </div>
        </section>

        {/* Selected day detail */}
        {selectedDay && (
          <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm fade-up">
            <h3 className="font-serif text-lg font-bold text-[#2D2A26] mb-3">
              <Calendar size={16} className="inline mr-2 text-gold" />
              {new Date(selectedDay).toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' })}
            </h3>
            {selectedEntry ? (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-4xl">{selectedEntry.mood}</span>
                  <span className="text-lg font-semibold text-[#5C5650]">
                    {MOODS.find(m => m.emoji === selectedEntry.mood)?.label || 'Registrado'}
                  </span>
                </div>
                {selectedEntry.journal && (
                  <div className="bg-cream rounded-2xl p-4 text-sm text-[#5C5650] leading-relaxed mb-4">
                    <PenLine size={14} className="inline mr-1 text-gold" /> {selectedEntry.journal}
                  </div>
                )}
                <div>
                  <label className="text-xs font-bold text-[#9B9590] block mb-2">
                    <PenLine size={12} className="inline mr-1" />
                    {selectedEntry.journal ? 'Actualizar diario' : 'Agregar nota al diario'}
                  </label>
                  <textarea value={journal} onChange={e => setJournal(e.target.value)}
                    placeholder="¿Qué pasó hoy? ¿Cómo te sentiste?"
                    className="w-full p-3 rounded-2xl border border-gold-light bg-cream/50 text-sm text-[#2D2A26] placeholder:text-[#ccc] focus:outline-none focus:border-gold min-h-[80px] resize-none" />
                  <button onClick={handleJournalSave}
                    className="mt-2 px-4 py-2 rounded-xl bg-gold/10 text-gold-dark font-bold text-sm hover:bg-gold/20 transition-all">
                    Guardar
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-[#9B9590]">No registraste tu ánimo este día. Visita la experiencia diaria para registrarlo.</p>
            )}
          </section>
        )}

        {/* Monthly stats */}
        <section className="bg-white rounded-3xl p-6 border border-gold-light/30 shadow-sm">
          <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-4 flex items-center gap-2">
            <TrendingUp size={20} className="text-gold" /> Resumen del Mes
          </h3>

          {thisMonthEntries.length > 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-cream rounded-2xl p-4 text-center">
                  <div className="text-2xl font-bold text-[#2D2A26]">{thisMonthEntries.length}</div>
                  <div className="text-xs text-[#9B9590]">Días registrados</div>
                </div>
                <div className="bg-cream rounded-2xl p-4 text-center">
                  <div className="text-2xl">{topMood ? topMood[0] : '—'}</div>
                  <div className="text-xs text-[#9B9590]">Más frecuente</div>
                </div>
                <div className="bg-cream rounded-2xl p-4 text-center">
                  <div className="text-2xl font-bold text-[#2D2A26]">
                    {Math.round((thisMonthEntries.filter(e => positiveEmojis.includes(e.mood)).length / thisMonthEntries.length) * 100)}%
                  </div>
                  <div className="text-xs text-[#9B9590]">Días positivos</div>
                </div>
              </div>

              {/* Mood distribution */}
              <div>
                <p className="text-xs font-bold text-[#9B9590] mb-2">Distribución de emociones</p>
                <div className="flex gap-1 flex-wrap">
                  {Object.entries(moodCounts).sort((a, b) => b[1] - a[1]).map(([emoji, count]) => (
                    <div key={emoji} className="flex items-center gap-1 bg-cream rounded-xl px-3 py-1.5">
                      <span className="text-lg">{emoji}</span>
                      <span className="text-xs font-bold text-[#5C5650]">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-[#9B9590] text-center py-4">
              Aún no hay datos este mes. Registra tu ánimo en la experiencia diaria.
            </p>
          )}
        </section>

        {/* AI Insights */}
        {history.length >= 5 && bestDay && (
          <section className="bg-gradient-to-br from-lavender-light to-gold-light/30 rounded-3xl p-6 border border-lavender/20">
            <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-3 flex items-center gap-2">
              <Sparkles size={20} className="text-lavender" /> Observaciones
            </h3>
            <div className="space-y-3 text-sm text-[#5C5650]">
              <p>📊 Tienes <strong>{history.length}</strong> registros en total.</p>
              {bestDay.ratio > 0 && (
                <p>🌟 Tus mejores días suelen ser los <strong>{dayNames[bestDay.day]}</strong>.</p>
              )}
              {topMood && (
                <p>💡 Tu emoción más frecuente es {topMood[0]} — {MOODS.find(m => m.emoji === topMood[0])?.label}.</p>
              )}
              <p className="text-xs text-[#9B9590] italic mt-2">Estas observaciones mejoran con más datos. Sigue registrando tu ánimo diariamente.</p>
            </div>
          </section>
        )}
      </main>
      <Footer />
    </div>
  );
}
