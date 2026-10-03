import React from 'react';
import Link from 'next/link';
import { COACHES, PROGRAMS } from '@/lib/amp-content';
import { Sparkles, Calendar, AlertCircle, Heart, Award, ArrowRight, BookOpen, Compass } from 'lucide-react';

export const metadata = {
  title: 'Conócenos | Coaches y Filosofía AMP — El Portal de la Alegría',
  description: 'Conoce a Juan Diego Giraldo, Andrea Silva, Dericielo Jiménez y Lina Valencia. Coaches y mentores de Actitud Mental Positiva y El Portal de la Alegría.',
};

export default function ConocenosPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
      {/* ── HEADER WITH CINEMATIC ATMOSPHERE ── */}
      <div className="text-center max-w-3xl mx-auto mb-20">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-4">
          <Sparkles size={14} /> Historia & Propósito
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl md:text-6xl font-extrabold text-[#1E1A17] dark:text-[#F6F3EE] mb-6 leading-tight">
          Nuestra Misión: Compartir Herramientas de Sanación y Sabiduría
        </h1>
        <p className="text-base sm:text-lg text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
          Nacimos con una convicción clara: la actitud mental positiva no es una ilusión ni un optimismo ingenuo. Es la disciplina diaria de cuidar lo que pensamos, manifestar bienestar en comunidad y superar situaciones complejas acompañados por personas reales.
        </p>
      </div>

      {/* ── THREE ETHICAL PILLARS ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-24">
        <div className="glass-card p-8 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#E0A526] transition-colors shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-[#E0A526]/15 text-[#C68C14] dark:text-[#F2C14E] flex items-center justify-center mb-5">
            <Heart size={24} />
          </div>
          <h3 className="font-serif text-xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-3">
            1. Calidez & Humanidad
          </h3>
          <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
            Hablamos en español cálido, directo y compasivo. Ningún algoritmo sustituye la empatía de un mentor que comprende tus desafíos culturales y familiares.
          </p>
        </div>

        <div className="glass-card p-8 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#7E9F84] transition-colors shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-[#7E9F84]/15 text-[#7E9F84] flex items-center justify-center mb-5">
            <Compass size={24} />
          </div>
          <h3 className="font-serif text-xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-3">
            2. Práctica Sostenida
          </h3>
          <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
            La transformación no sucede en un momento de euforia. Se construye con 5 a 10 minutos de pausa, respiración y afirmación consciente cada mañana.
          </p>
        </div>

        <div className="glass-card p-8 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#F28C6B] transition-colors shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-[#F28C6B]/15 text-[#F28C6B] flex items-center justify-center mb-5">
            <Award size={24} />
          </div>
          <h3 className="font-serif text-xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-3">
            3. Integridad Ética
          </h3>
          <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
            Reconocemos con humildad nuestros alcances. El coaching y la meditación potencian tu vida, pero sabemos cuándo recomendar y apoyar la atención clínica profesional.
          </p>
        </div>
      </div>

      {/* ── TEACHER-FORWARD DETAILED ROSTER ── */}
      <div className="mb-24">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <p className="text-xs font-bold uppercase tracking-widest text-[#E0A526] mb-2">
            El Claustro de Mentores AMP
          </p>
          <h2 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
            Conoce a tus Mentores & Guías
          </h2>
          <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5]">
            Cada mentor aporta una historia de superación personal y una formación certificada para acompañarte.
          </p>
        </div>

        <div className="space-y-16">
          {COACHES.map((coach, idx) => {
            const isEven = idx % 2 === 0;
            const coachPrograms = PROGRAMS.filter((p) => p.coachId === coach.id);
            return (
              <div
                key={coach.id}
                id={coach.id}
                className={`glass-card rounded-3xl p-6 sm:p-10 border border-[#EFE6D8] dark:border-[#2B254E] shadow-xl flex flex-col md:flex-row items-start gap-10 ${
                  isEven ? '' : 'md:flex-row-reverse'
                }`}
              >
                {/* Photo & Badge placeholder with clear note */}
                <div className="w-full md:w-72 shrink-0 text-center">
                  <div className="w-full aspect-[4/5] rounded-3xl overflow-hidden shadow-xl border-2 border-[#E0A526]/30 mb-4 relative group">
                    <img
                      src={coach.photoLocal}
                      alt={coach.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                    <div className="absolute inset-x-0 bottom-0 bg-black/75 backdrop-blur-sm text-white text-[10px] py-2 px-3 font-mono">
                      Foto temporal stock (Juan reemplazará)
                    </div>
                  </div>

                  <div className="flex items-center justify-center gap-2 mb-4">
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#E0A526]/15 text-[#C68C14] dark:text-[#F2C14E]">
                      Mentor Certificado AMP
                    </span>
                  </div>

                  <Link
                    href={`/agenda?coach=${coach.id}`}
                    className="w-full py-3 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 shadow-md hover:shadow-lg transition-all no-underline"
                  >
                    <Calendar size={14} /> Reservar Sesión 1:1
                  </Link>
                </div>

                {/* Info & Bio */}
                <div className="flex-1 space-y-5 text-left">
                  <div>
                    <h3 className="font-serif text-3xl sm:text-4xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                      {coach.name}
                    </h3>
                    <p className="text-base font-semibold text-[#E0A526] mt-1">
                      {coach.role}
                    </p>
                  </div>

                  {/* Tagline */}
                  <blockquote className="border-l-4 border-[#E0A526] pl-4 italic text-sm text-[#5C544D] dark:text-[#B4ACC5] bg-black/[0.02] dark:bg-white/[0.02] py-2 rounded-r-xl">
                    &ldquo;{coach.tagline}&rdquo;
                  </blockquote>

                  {/* Bio */}
                  <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
                    {coach.bio}
                  </p>

                  {/* Specialties */}
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-[#1E1A17] dark:text-[#F6F3EE] mb-2.5">
                      Especialidades & Herramientas:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {coach.specialties.map((spec) => (
                        <span
                          key={spec}
                          className="text-xs px-3 py-1 rounded-xl bg-black/5 dark:bg-white/5 text-[#1E1A17] dark:text-[#F6F3EE] font-medium border border-black/5 dark:border-white/5"
                        >
                          {spec}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Associated Programs */}
                  {coachPrograms.length > 0 && (
                    <div className="pt-4 border-t border-black/5 dark:border-white/5">
                      <p className="text-xs font-bold uppercase tracking-wider text-[#E0A526] mb-3 flex items-center gap-1.5">
                        <BookOpen size={14} /> Programas dirigidos por {coach.name.split(' ')[0]}:
                      </p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {coachPrograms.map((p) => (
                          <Link
                            key={p.id}
                            href="/membresia"
                            className="p-3 rounded-2xl bg-white/60 dark:bg-white/5 border border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#E0A526] flex items-center justify-between no-underline group transition-all"
                          >
                            <div>
                              <p className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE] group-hover:text-[#E0A526]">
                                {p.title}
                              </p>
                              <p className="text-[10px] text-[#5C544D] dark:text-[#B4ACC5]">
                                {p.durationWeeks} semanas · {p.lessonsCount} lecciones
                              </p>
                            </div>
                            <ArrowRight size={14} className="text-[#E0A526] group-hover:translate-x-1 transition-transform" />
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── PLACEHOLDER REPLACEMENT NOTICE ── */}
      <div className="p-6 rounded-3xl bg-[#E0A526]/10 border border-[#E0A526]/30 flex items-start gap-4 mb-12">
        <AlertCircle className="text-[#C68C14] dark:text-[#F2C14E] shrink-0 mt-0.5" size={20} />
        <div className="text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5] space-y-1">
          <p className="font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
            Nota para el equipo de producción de Juan Diego Giraldo:
          </p>
          <p>
            Las fotografías actuales provienen de stock con licencia libre y actúan como marcadores de posición estéticos. Los retratos definitivos tomados en alta resolución se ubican en <code className="font-mono bg-white dark:bg-black/30 px-1 py-0.5 rounded">public/coaches/</code> y se vinculan directamente en <code className="font-mono bg-white dark:bg-black/30 px-1 py-0.5 rounded">src/lib/amp-content.ts</code>.
          </p>
        </div>
      </div>
    </div>
  );
}
