'use client';

import { useState, useEffect, useMemo } from 'react';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import ContentCard from '../../components/ContentCard';
import AudioPlayer from '../../components/AudioPlayer';
import { PILLAR_CONFIG } from '../../lib/data';
import type { Pillar } from '../../lib/data';
import { Search, Library, X } from 'lucide-react';

interface ContentItem {
  id: string;
  type: string;
  title: string;
  description: string;
  duration_seconds?: number;
  pillar?: string;
  premium?: boolean;
  category?: string;
  content_text?: string;
  audio_url?: string;
}

const TYPE_FILTERS: { key: string; label: string }[] = [
  { key: 'all', label: 'Todas' },
  { key: 'meditation', label: 'Meditaciones' },
  { key: 'affirmation', label: 'Afirmaciones' },
  { key: 'lesson', label: 'Lecciones' },
  { key: 'exercise', label: 'Ejercicios' },
];

export default function BibliotecaPage() {
  const [content, setContent] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterPillar, setFilterPillar] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [activeContent, setActiveContent] = useState<ContentItem | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterType !== 'all') params.set('type', filterType);
      if (filterPillar !== 'all') params.set('pillar', filterPillar);
      params.set('limit', '100');
      const res = await fetch(`http://localhost:8000/api/v1/amp/content?${params}`);
      if (res.ok) setContent(await res.json());
    } catch {
      // Network error — keep existing content
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType, filterPillar]);

  // Client-side search filter on title/description
  const filtered = useMemo(() => {
    if (!search.trim()) return content;
    const q = search.toLowerCase();
    return content.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.description?.toLowerCase().includes(q)
    );
  }, [content, search]);

  const handlePlay = (item: ContentItem) => {
    setActiveContent(item);
  };

  const handleClosePlayer = () => {
    setActiveContent(null);
  };

  return (
    <div className="min-h-screen flex flex-col bg-warmwhite">
      <Navbar />

      <main className="flex-1 max-w-5xl mx-auto px-4 py-8 w-full">
        {/* ── Page Header ── */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <Library size={28} className="text-gold" />
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#2D2A26] mb-3">
            Biblioteca
          </h1>
          <p className="text-[#9B9590] text-lg max-w-xl mx-auto">
            Explora todo nuestro contenido de transformaci&oacute;n personal
          </p>
        </div>

        {/* ── Filter Bar ── */}
        <div className="space-y-4 mb-8">
          {/* Type filters */}
          <div className="flex items-center justify-center gap-2 flex-wrap">
            {TYPE_FILTERS.map((t) => (
              <button
                key={t.key}
                onClick={() => setFilterType(t.key)}
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  filterType === t.key
                    ? 'bg-gold/15 text-gold-dark border border-gold/30'
                    : 'text-[#9B9590] hover:text-[#5C5650] border border-transparent'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Pillar filters */}
          <div className="flex items-center justify-center gap-2 flex-wrap">
            <button
              onClick={() => setFilterPillar('all')}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                filterPillar === 'all'
                  ? 'bg-gold/15 text-gold-dark border border-gold/30'
                  : 'text-[#9B9590] hover:text-[#5C5650] border border-transparent'
              }`}
            >
              Todos los Pilares
            </button>
            {(Object.entries(PILLAR_CONFIG) as [Pillar, (typeof PILLAR_CONFIG)[Pillar]][]).map(
              ([key, p]) => (
                <button
                  key={key}
                  onClick={() => setFilterPillar(key)}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center gap-1.5 ${
                    filterPillar === key ? 'border' : 'border border-transparent'
                  }`}
                  style={
                    filterPillar === key
                      ? { color: p.color, background: p.color + '15', borderColor: p.color + '30' }
                      : { color: '#9B9590' }
                  }
                >
                  {p.icon} {p.label}
                </button>
              )
            )}
          </div>

          {/* Search input */}
          <div className="max-w-md mx-auto relative">
            <Search
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[#9B9590] pointer-events-none"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar contenido..."
              className="w-full pl-11 pr-10 py-3 rounded-2xl border border-gold-light/30 bg-white text-sm text-[#2D2A26] placeholder-[#9B9590] focus:outline-none focus:border-gold/50 focus:ring-2 focus:ring-gold/10 transition-all"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9B9590] hover:text-[#5C5650] transition-colors"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* ── Content Grid ── */}
        {loading ? (
          // Loading skeleton
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-3xl p-6 border border-gold-light/30 animate-pulse"
              >
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-sand" />
                  <div className="flex-1 space-y-2">
                    <div className="h-3 w-20 bg-sand rounded" />
                    <div className="h-4 w-3/4 bg-sand rounded" />
                  </div>
                </div>
                <div className="space-y-2 mb-4">
                  <div className="h-3 w-full bg-sand rounded" />
                  <div className="h-3 w-2/3 bg-sand rounded" />
                </div>
                <div className="flex items-center justify-between">
                  <div className="h-3 w-16 bg-sand rounded" />
                  <div className="h-8 w-20 bg-sand rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          // Empty state
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-3xl bg-sand flex items-center justify-center">
              <Library size={28} className="text-[#9B9590]" />
            </div>
            <h3 className="font-serif text-xl font-bold text-[#2D2A26] mb-2">
              No encontramos contenido con esos filtros
            </h3>
            <p className="text-sm text-[#9B9590] mb-6">
              Intenta cambiar los filtros o buscar algo diferente
            </p>
            <button
              onClick={() => {
                setFilterType('all');
                setFilterPillar('all');
                setSearch('');
              }}
              className="px-6 py-2.5 rounded-2xl bg-gold/10 text-gold-dark font-semibold text-sm hover:bg-gold/20 transition-all"
            >
              Limpiar filtros
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filtered.map((item) => (
              <ContentCard key={item.id} item={item} onPlay={handlePlay} />
            ))}
          </div>
        )}

        {/* Result count */}
        {!loading && filtered.length > 0 && (
          <p className="text-center text-xs text-[#9B9590] mt-6">
            {filtered.length} {filtered.length === 1 ? 'resultado' : 'resultados'}
            {search && ` para "${search}"`}
          </p>
        )}
      </main>

      <Footer />

      {/* ── Active Content Player / Viewer ── */}
      {activeContent && (
        <>
          {activeContent.type === 'meditation' || activeContent.type === 'exercise' ? (
            <AudioPlayer
              title={activeContent.title}
              description={activeContent.description}
              pillar={activeContent.pillar}
              audioUrl={activeContent.audio_url}
              durationSeconds={activeContent.duration_seconds ?? 300}
              contentText={activeContent.content_text}
              onClose={handleClosePlayer}
            />
          ) : (
            // Full text overlay for affirmations/lessons
            <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-end sm:items-center justify-center p-4">
              <div className="bg-white rounded-3xl w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-2xl animate-fade-up">
                {/* Header stripe */}
                <div
                  className="h-1.5 rounded-t-3xl"
                  style={{
                    background: activeContent.pillar && activeContent.pillar in PILLAR_CONFIG
                      ? PILLAR_CONFIG[activeContent.pillar as Pillar].color
                      : '#D4A030',
                  }}
                />

                <div className="p-6">
                  {/* Type & pillar badges */}
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#9B9590]">
                      {activeContent.type === 'affirmation'
                        ? 'Afirmaci\u00f3n'
                        : activeContent.type === 'lesson'
                        ? 'Lecci\u00f3n'
                        : activeContent.type}
                    </span>
                    {activeContent.pillar && activeContent.pillar in PILLAR_CONFIG && (
                      <span
                        className="text-xs font-bold px-2 py-0.5 rounded-full"
                        style={{
                          color: PILLAR_CONFIG[activeContent.pillar as Pillar].color,
                          background: PILLAR_CONFIG[activeContent.pillar as Pillar].color + '15',
                        }}
                      >
                        {PILLAR_CONFIG[activeContent.pillar as Pillar].icon}{' '}
                        {PILLAR_CONFIG[activeContent.pillar as Pillar].label}
                      </span>
                    )}
                    {activeContent.premium && (
                      <span className="text-[10px] font-bold text-gold-dark bg-gold/10 px-1.5 py-0.5 rounded-full">
                        Premium
                      </span>
                    )}
                  </div>

                  <h2 className="font-serif text-2xl font-bold text-[#2D2A26] mb-3">
                    {activeContent.title}
                  </h2>

                  {activeContent.description && (
                    <p className="text-sm text-[#5C5650] leading-relaxed mb-4">
                      {activeContent.description}
                    </p>
                  )}

                  {activeContent.content_text && (
                    <div className="bg-sand/30 rounded-2xl p-5 mb-4">
                      <p className="text-sm text-[#2D2A26] leading-relaxed whitespace-pre-wrap">
                        {activeContent.content_text}
                      </p>
                    </div>
                  )}

                  <button
                    onClick={handleClosePlayer}
                    className="w-full py-3 rounded-2xl bg-gold/10 text-gold-dark font-bold text-sm hover:bg-gold/20 transition-all"
                  >
                    Cerrar
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
