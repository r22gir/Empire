import React from 'react';
import Link from 'next/link';
import { SERVICES } from '@/lib/amp-content';
import { Sparkles, Check, ArrowRight, Calendar, ShieldCheck } from 'lucide-react';

export const metadata = {
  title: 'Servicios | Sesiones 1:1, Talleres y Empresas',
  description: 'Descubre los servicios de Actitud Mental Positiva: coaching individual 1:1, talleres grupales, membresía El Portal de la Alegría y programas para empresas.',
};

export default function ServiciosPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12 md:py-16">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-4">
          <Sparkles size={14} /> Soluciones de Crecimiento
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-6">
          Servicios Diseñados para tu Bienestar y Liderazgo
        </h1>
        <p className="text-base sm:text-lg text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
          Ya sea que busques una sesión privada para destrabar una decisión clave, un taller transformador en comunidad, o elevar la salud mental de tu equipo de trabajo.
        </p>
      </div>

      {/* ── SERVICES GRID ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        {SERVICES.map((serv) => (
          <div
            key={serv.id}
            className="bg-white dark:bg-[#1E1B3A] rounded-3xl p-8 border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm flex flex-col justify-between hover:border-[#E0A526] transition-all group"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[#E0A526]">
                  {serv.subtitle}
                </span>
                <span className="text-xs px-2.5 py-1 rounded-full bg-[#E4EDE6] dark:bg-[#14122B] text-[#5A7A60] dark:text-[#9DBFA2] font-semibold">
                  {serv.priceNote}
                </span>
              </div>

              <h2 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4 group-hover:text-[#E0A526] transition-colors">
                {serv.title}
              </h2>

              <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-6">
                {serv.description}
              </p>

              <div className="space-y-2.5 mb-8">
                <p className="text-xs font-bold uppercase tracking-wider text-[#2B2622] dark:text-[#F4EFE8]">
                  Qué incluye:
                </p>
                {serv.bullets.map((b, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9]">
                    <Check size={16} className="text-[#E0A526] shrink-0 mt-0.5" />
                    <span>{b}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-[#F0E6D8] dark:border-[#2E2A54]">
              {serv.id === 'membresia-portal' ? (
                <Link
                  href="/membresia"
                  className="w-full py-3.5 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-[#2B2622] font-bold text-sm flex items-center justify-center gap-2 shadow hover:scale-[1.02] transition-transform"
                >
                  {serv.ctaLabel} <ArrowRight size={16} />
                </Link>
              ) : serv.id === 'bienestar-empresas' ? (
                <Link
                  href="/agenda?type=empresas"
                  className="w-full py-3.5 rounded-2xl bg-[#2B2622] dark:bg-white text-white dark:text-[#2B2622] font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
                >
                  {serv.ctaLabel} <ArrowRight size={16} />
                </Link>
              ) : (
                <Link
                  href={`/agenda?service=${serv.id}`}
                  className="w-full py-3.5 rounded-2xl border-2 border-[#E0A526] text-[#B8860B] dark:text-[#F2C14E] font-bold text-sm flex items-center justify-center gap-2 hover:bg-[#E0A526]/10 transition-colors"
                >
                  <Calendar size={16} /> {serv.ctaLabel}
                </Link>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* ── SATISFACTION & TRUST GUARANTEE ── */}
      <div className="bg-[#FFF9F1] dark:bg-[#14122B] p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] text-center max-w-3xl mx-auto">
        <ShieldCheck size={32} className="text-[#7E9F84] mx-auto mb-3" />
        <h3 className="font-serif text-xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2">
          Compromiso de Confidencialidad y Calidad
        </h3>
        <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed max-w-xl mx-auto">
          Todas las sesiones individuales y consultas corporativas se rigen bajo los más altos estándares éticos de confidencialidad y respeto mutuo. Tu bienestar es nuestra única prioridad.
        </p>
      </div>
    </div>
  );
}
