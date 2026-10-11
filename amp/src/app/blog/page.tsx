import React from 'react';
import Link from 'next/link';
import { BLOG_POSTS } from '@/lib/amp-content';
import { Sparkles, Clock, ArrowRight } from 'lucide-react';

export const metadata = {
  title: 'Blog de Bienestar & Mentalidad | AMP — El Portal de la Alegría',
  description: 'Artículos, reflexiones y guías prácticas sobre amor propio, crianza consciente, resiliencia y liderazgo personal por los coaches de Actitud Mental Positiva.',
};

export default function BlogIndexPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Sabiduría Diaria & Reflexión
        </div>
        <h1 className="font-serif text-3xl sm:text-5xl md:text-6xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
          Artículos & Reflexiones de Vida
        </h1>
        <p className="text-sm sm:text-base text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
          Pensamientos y aprendizajes de nuestros coaches para iluminar tu jornada, transformar tus vínculos familiares y fortalecer tu paz interior.
        </p>
      </div>

      {/* ── BLOG POSTS GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
        {BLOG_POSTS.map((post) => (
          <article
            key={post.slug}
            className="glass-card rounded-3xl p-8 sm:p-10 border border-[#EFE6D8] dark:border-[#2B254E] shadow-sm flex flex-col justify-between hover:border-[#E0A526] transition-all duration-300 group"
          >
            <div>
              <div className="flex items-center justify-between text-xs mb-3">
                <span className="font-bold px-3 py-1 rounded-full bg-[#E0A526]/15 text-[#C68C14] dark:text-[#F2C14E] uppercase tracking-wider">
                  {post.category}
                </span>
                <span className="text-[#5C544D] dark:text-[#B4ACC5] flex items-center gap-1 font-medium">
                  <Clock size={12} /> {post.readTime}
                </span>
              </div>

              <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-3 group-hover:text-[#E0A526] transition-colors leading-snug">
                <Link href={`/blog/${post.slug}`} className="no-underline text-inherit">
                  {post.title}
                </Link>
              </h2>

              <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed mb-6">
                {post.excerpt}
              </p>
            </div>

            <div className="pt-5 border-t border-black/5 dark:border-white/5 flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                  {post.author}
                </p>
                <p className="text-[11px] text-[#5C544D] dark:text-[#B4ACC5]">
                  {post.authorRole} · {post.date}
                </p>
              </div>

              <Link
                href={`/blog/${post.slug}`}
                className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[#E0A526] group-hover:text-[#C68C14] no-underline"
              >
                Leer <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
