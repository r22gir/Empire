import React from 'react';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { BLOG_POSTS, SAMPLE_TRACKS } from '@/lib/amp-content';
import { Clock, ArrowLeft, User, Play } from 'lucide-react';

interface PostPageProps {
  params: {
    slug: string;
  };
}

export function generateStaticParams() {
  return BLOG_POSTS.map((post) => ({
    slug: post.slug,
  }));
}

export function generateMetadata({ params }: PostPageProps) {
  const post = BLOG_POSTS.find((p) => p.slug === params.slug);
  if (!post) return { title: 'Artículo no encontrado | AMP' };

  return {
    title: `${post.title} | Blog AMP`,
    description: post.excerpt,
  };
}

export default function SingleBlogPostPage({ params }: PostPageProps) {
  const post = BLOG_POSTS.find((p) => p.slug === params.slug);
  if (!post) notFound();

  // Find related audio track
  const relatedAudio = SAMPLE_TRACKS.find(t => t.theme === post.relatedTheme) || SAMPLE_TRACKS[0];

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 md:py-16">
      {/* Back button */}
      <div className="mb-8">
        <Link
          href="/blog"
          className="inline-flex items-center gap-1.5 text-xs font-bold text-[#E0A526] hover:text-[#B8860B] uppercase tracking-wider"
        >
          <ArrowLeft size={14} /> Volver a todos los artículos
        </Link>
      </div>

      {/* Header */}
      <header className="mb-10 text-center max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-4">
          {post.category}
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#2B2622] dark:text-[#F4EFE8] leading-tight mb-6">
          {post.title}
        </h1>
        <div className="flex items-center justify-center gap-3 text-xs text-[#6B625A] dark:text-[#B9B2C9]">
          <span className="font-bold text-[#2B2622] dark:text-[#F4EFE8]">{post.author}</span>
          <span>•</span>
          <span>{post.date}</span>
          <span>•</span>
          <span className="flex items-center gap-1"><Clock size={12} /> {post.readTime} de lectura</span>
        </div>
      </header>

      {/* Content body */}
      <div className="bg-white dark:bg-[#1E1B3A] p-6 sm:p-10 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm mb-12">
        <div className="space-y-6 text-[#2B2622] dark:text-[#F4EFE8] text-base leading-relaxed font-sans">
          {post.content.map((paragraph, idx) => (
            <p key={idx} className="leading-loose">
              {paragraph}
            </p>
          ))}
        </div>

        {/* Lead magnet call to action embedded */}
        <div className="mt-10 p-6 rounded-2xl bg-[#FFE3B3]/25 dark:bg-[#14122B] border border-[#E0A526]/40 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h4 className="font-serif font-bold text-lg text-[#2B2622] dark:text-[#F4EFE8] mb-1">
              ¿Te inspiró esta reflexión?
            </h4>
            <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9]">
              Escucha la meditación guiada de {relatedAudio.durationLabel} conectada con este tema en nuestra biblioteca.
            </p>
          </div>
          <Link
            href={`/biblioteca?theme=${post.relatedTheme}`}
            className="px-5 py-2.5 rounded-full bg-[#E0A526] hover:bg-[#B8860B] text-white text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shrink-0 shadow-sm"
          >
            <Play size={14} /> Escuchar Audio
          </Link>
        </div>
      </div>

      {/* Author Bio Box */}
      <div className="bg-[#FFF9F1] dark:bg-[#14122B] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] flex flex-col sm:flex-row items-center sm:items-start gap-4 text-center sm:text-left mb-12">
        <div className="w-16 h-16 rounded-full bg-[#E0A526]/20 flex items-center justify-center text-[#E0A526] font-bold text-xl shrink-0">
          <User size={28} />
        </div>
        <div>
          <h3 className="font-serif font-bold text-base text-[#2B2622] dark:text-[#F4EFE8]">
            {post.author}
          </h3>
          <p className="text-xs text-[#E0A526] font-semibold mb-2">{post.authorRole}</p>
          <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-3">
            Facilitador y coach activo en Actitud Mental Positiva. Acompaña procesos grupales y mentorías 1:1 orientadas a la plenitud, la paz mental y la sabiduría familiar.
          </p>
          <Link
            href={`/agenda?coach=${post.author.toLowerCase().replace(/\s+/g, '-')}`}
            className="text-xs font-bold text-[#E0A526] hover:underline"
          >
            Agendar sesión con {post.author} →
          </Link>
        </div>
      </div>
    </div>
  );
}
