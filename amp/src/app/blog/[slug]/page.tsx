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
    title: `${post.title} | Blog AMP — El Portal de la Alegría`,
    description: post.excerpt,
  };
}

export default function SingleBlogPostPage({ params }: PostPageProps) {
  const post = BLOG_POSTS.find((p) => p.slug === params.slug);
  if (!post) notFound();

  // Find related audio track
  const relatedAudio = SAMPLE_TRACKS.find(t => t.theme === post.relatedTheme) || SAMPLE_TRACKS[0];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12 md:py-20">
      {/* Back button */}
      <div className="mb-8">
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-xs font-bold text-[#E0A526] hover:text-[#C68C14] uppercase tracking-wider no-underline"
        >
          <ArrowLeft size={16} /> Volver a todos los artículos
        </Link>
      </div>

      {/* Header */}
      <header className="mb-12 text-center max-w-3xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-4">
          {post.category}
        </div>
        <h1 className="font-serif text-3xl sm:text-5xl md:text-6xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] leading-tight mb-6">
          {post.title}
        </h1>
        <div className="flex items-center justify-center gap-3 text-xs text-[#5C544D] dark:text-[#B4ACC5]">
          <span className="font-bold text-[#1E1A17] dark:text-[#F6F3EE]">{post.author}</span>
          <span>•</span>
          <span>{post.date}</span>
          <span>•</span>
          <span className="flex items-center gap-1"><Clock size={12} /> {post.readTime} de lectura</span>
        </div>
      </header>

      {/* Content body */}
      <div className="glass-card p-8 sm:p-12 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] shadow-md mb-12">
        <div className="space-y-6 text-[#1E1A17] dark:text-[#F6F3EE] text-base sm:text-lg leading-relaxed font-sans">
          {post.content.map((paragraph, idx) => (
            <p key={idx} className="leading-loose">
              {paragraph}
            </p>
          ))}
        </div>

        {/* Lead magnet call to action embedded */}
        <div className="mt-12 p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-[#E0A526]/15 via-[#F28C6B]/15 to-transparent border border-[#E0A526]/30 flex flex-col sm:flex-row items-center justify-between gap-5">
          <div>
            <h4 className="font-serif font-bold text-xl text-[#1E1A17] dark:text-[#F6F3EE] mb-1.5">
              ¿Te inspiró esta reflexión?
            </h4>
            <p className="text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5]">
              Escucha la meditación guiada de {relatedAudio.durationLabel} conectada con este tema en nuestra biblioteca sonora.
            </p>
          </div>
          <Link
            href={`/biblioteca?tema=${post.relatedTheme}`}
            className="px-6 py-3 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 shrink-0 shadow-md hover:scale-105 transition-all no-underline"
          >
            <Play size={14} className="fill-current" /> Escuchar Audio
          </Link>
        </div>
      </div>

      {/* Author Bio Box */}
      <div className="glass-card p-6 sm:p-8 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] flex flex-col sm:flex-row items-center sm:items-start gap-5 text-center sm:text-left mb-12">
        <div className="w-16 h-16 rounded-2xl bg-[#E0A526]/20 flex items-center justify-center text-[#E0A526] font-bold text-xl shrink-0">
          <User size={30} />
        </div>
        <div>
          <h3 className="font-serif font-bold text-lg text-[#1E1A17] dark:text-[#F6F3EE]">
            {post.author}
          </h3>
          <p className="text-xs text-[#E0A526] font-semibold mb-2">{post.authorRole}</p>
          <p className="text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed mb-4">
            Facilitador y mentor activo en Actitud Mental Positiva. Acompaña procesos grupales y mentorías 1:1 orientadas a la plenitud, la paz mental y la sabiduría familiar.
          </p>
          <Link
            href={`/agenda`}
            className="text-xs font-bold text-[#E0A526] hover:text-[#C68C14] inline-flex items-center gap-1 no-underline"
          >
            Agendar sesión privada 1:1 con un mentor →
          </Link>
        </div>
      </div>
    </div>
  );
}
