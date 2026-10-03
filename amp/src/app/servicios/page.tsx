import React from 'react';
import Link from 'next/link';
import { SERVICES } from '@/lib/amp-content';
import { Sparkles, Check, ArrowRight, ShieldCheck } from 'lucide-react';

export const metadata = {
  title: 'Servicios | Sesiones 1:1, Talleres y Empresas — AMP',
  description: 'Descubre los servicios de Actitud Mental Positiva: coaching individual 1:1, talleres grupales, membresía El Portal de la Alegría y programas para empresas.',
};

export default function ServiciosPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-4">
          <Sparkles size={14} /> Soluciones de Crecimiento & Bienestar
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl md:text-6xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-6">
          Servicios Diseñados para tu Bienestar y Liderazgo
        </h1>
        <p className="text-base sm:text-lg text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
          Ya sea que busques una sesión privada para destrabar una decisión clave, un taller transformador en comunidad, o elevar la salud mental de tu equipo de trabajo.
        </p>
      </div>

      {/* ── SERVICES GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-20">
        {SERVICES.map((serv) => (
          <div
            key={serv.id}
            className="glass-card rounded-3xl p-8 sm:p-10 border border-[#EFE6D8] dark:border-[#2B254E] shadow-md flex flex-col justify-between hover:border-[#E0A526] transition-all duration-300 group"
          >
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-[#E0A526]">
                  {serv.subtitle}
                </span>
                <span className="text-xs px-3 py-1 rounded-full bg-[#7E9F84]/15 text-[#5A7A60] dark:text-[#9DBFA2] font-semibold">
                  {serv.priceNote}
                </span>
              </div>

              <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4 group-hover:text-[#E0A526] transition-colors">
                {serv.title}
              </h2>

              <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed mb-6">
                {serv.description}
              </p>

              <div className="space-y-3 mb-8">
                <p className="text-xs font-bold uppercase tracking-wider text-[#1E1A17] dark:text-[#F6F3EE]">
                  Qué incluye:
                </p>
                {serv.bullets.map((b, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5]">
                    <Check size={18} className="text-[#E0A526] shrink-0 mt-0.5" />
                    <span>{b}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-6 border-t border-black/5 dark:border-white/5">
              <Link
                href={serv.id === 'coaching-1-1' ? '/agenda' : serv.id === 'membresia-portal' ? '/membresia' : '/agenda'}
                className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-md hover:scale-102 active:scale-98 transition-all no-underline"
              >
                {serv.ctaLabel} <ArrowRight size={16} />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {/* ── ENTERPRISE / CUSTOM NOTICE ── */}
      <div className="glass-card rounded-3xl p-8 sm:p-10 border border-[#EFE6D8] dark:border-[#2B254E] flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold uppercase text-[#7E9F84]">
            <ShieldCheck size={16} /> Programas a la medida
          </div>
          <h3 className="font-serif text-2xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
            ¿Tienes requerimientos especiales para tu organización?
          </h3>
          <p className="text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5] max-w-xl">
            Diseñamos experiencias in-company y planes combinados para grupos ejecutivos, familias o comunidades específicas.
          </p>
        </div>

        <Link
          href="/agenda"
          className="px-7 py-3.5 rounded-full border-2 border-[#E0A526] text-[#C68C14] dark:text-[#F2C14E] font-bold text-xs uppercase tracking-wider hover:bg-[#E0A526]/10 transition-colors shrink-0 no-underline"
        >
          Conversar con Juan Diego
        </Link>
      </div>
    </div>
  );
}
