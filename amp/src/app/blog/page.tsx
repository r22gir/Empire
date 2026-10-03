import React from 'react';
import Link from 'next/link';
import { BLOG_POSTS } from '@/lib/amp-content';
import { Sparkles, Clock, ArrowRight, BookOpen } from 'lucide-react';

export const metadata = {
  title: 'Blog de Bienestar & Mentalidad | AMP',
  description: 'Artículos, reflexiones y guías prácticas sobre amor propio, crianza consciente, resiliencia y liderazgo personal por los coaches de Actitud Mental Positiva.',
};

export default function BlogIndexPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12 md:py-16">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-14">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Sabiduría Diaria
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
          Artículos & Reflexiones de Vida
        </h1>
        <p className="text-sm sm:text-base text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
          Pensamientos y aprendizajes de nuestros coaches para iluminar tu jornada, transformar tus vínculos familiares y fortalecer tu paz interior.
        </p>
      </div>

      {/* ── BLOG POSTS GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        {BLOG_POSTS.map((post) => (
          <article
            key={post.slug}
            className="bg-white dark:bg-[#1E1B3A] rounded-3xl p-8 border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm flex flex-col justify-between hover:border-[#E0A526] transition-all group"
          >
            <div>
              <div className="flex items-center justify-between text-xs mb-3">
                <span className="font-bold px-3 py-1 rounded-full bg-[#E0A526]/15 text-[#B8860B] dark:text-[#F2C14E] uppercase tracking-wider">
                  {post.category}
                </span>
                <span className="text-[#6B625A] dark:text-[#B9B2C9] flex items-center gap-1 font-medium">
                  <Clock size={12} /> {post.readTime}
                </span>
              </div>

              <h2 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-3 group-hover:text-[#E0A526] transition-colors leading-snug">
                <Link href={`/blog/${post.slug}`} className="no-underline text-inherit">
                  {post.title}
                </Link>
              </h2>

              <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-6">
                {post.excerpt}
              </p>
            </div>

            <div className="pt-4 border-t border-[#F0E6D8] dark:border-[#2E2A54] flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                  {post.author}
                </p>
                <p className="text-[11px] text-[#6B625A] dark:text-[#B9B2C9]">
                  {post.authorRole} · {post.date}
                </p>
              </div>

              <Link
                href={`/blog/${post.slug}`}
                className="text-xs font-bold text-[#E0A526] group-hover:text-[#B8860B] flex items-center gap-1 uppercase tracking-wider"
              >
                Leer artículo <ArrowRight size={14} />
              </Link>
            </div>
          </article>
        ))}
      </div>

      {/* ── LEAD MAGNET CALLOUT ── */}
      <div className="bg-[#FFE3B3]/25 dark:bg-[#1E1B3A] p-8 sm:p-10 rounded-3xl border border-[#E0A526]/30 text-center max-w-2xl mx-auto">
        <BookOpen size={30} className="text-[#E0A526] mx-auto mb-3" />
        <h3 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2">
          ¿Deseas profundizar en tu transformación personal?
        </h3>
        <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-6">
          Realiza nuestro breve quiz de inicio para recibir una guía personalizada de lecturas y meditaciones recomendadas.
        </p>
        <Link
          href="/onboarding"
          className="inline-flex px-8 py-3.5 rounded-full bg-[#E0A526] hover:bg-[#B8860B] text-white font-bold text-xs uppercase tracking-wider shadow"
        >
          Hacer Diagnóstico Gratuito
        </Link>
      </div>
    </div>
  );
}
