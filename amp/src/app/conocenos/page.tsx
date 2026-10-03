import React from 'react';
import Link from 'next/link';
import { COACHES } from '@/lib/amp-content';
import { Sparkles, Calendar, AlertCircle } from 'lucide-react';

export const metadata = {
  title: 'Conócenos | Coaches y Filosofía AMP',
  description: 'Conoce a Juan Diego Giraldo, Andrea Silva, Dericielo Jiménez y Lina Valencia. Coaches y mentores de Actitud Mental Positiva y El Portal de la Alegría.',
};

export default function ConocenosPage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-12 md:py-16">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-4">
          <Sparkles size={14} /> Historia & Propósito
        </div>
        <h1 className="font-serif text-4xl sm:text-5xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-6">
          Nuestra Misión: Compartir Herramientas de Sanación y Aprendizaje
        </h1>
        <p className="text-base sm:text-lg text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
          Nacimos con una convicción clara: la actitud mental positiva no es una ilusión ni un optimismo ingenuo. Es la disciplina diaria de cuidar lo que pensamos, manifestar bienestar en comunidad y superar situaciones complejas acompañados por personas reales.
        </p>
      </div>

      {/* ── VALUES CARDS ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-20">
        <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54]">
          <h3 className="font-serif text-lg font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2 text-[#E0A526]">
            1. Calidez & Humanidad
          </h3>
          <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
            Hablamos en español cálido, directo y compasivo. Ningún algoritmo sustituye la empatía de un mentor que comprende tus desafíos culturales y familiares.
          </p>
        </div>

        <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54]">
          <h3 className="font-serif text-lg font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2 text-[#7E9F84]">
            2. Práctica Sostenida
          </h3>
          <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
            La transformación no sucede en un momento de euforia. Se construye con 5 a 10 minutos de pausa, respiración y afirmación consciente cada mañana.
          </p>
        </div>

        <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54]">
          <h3 className="font-serif text-lg font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2 text-[#F28C6B]">
            3. Integridad Ética
          </h3>
          <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
            Reconocemos con humildad nuestros alcances. El coaching y la meditación potencian tu vida, pero sabemos cuándo recomendar y apoyar la atención clínica profesional.
          </p>
        </div>
      </div>

      {/* ── COACH PROFILES SECTION ── */}
      <div className="mb-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <p className="text-xs font-bold uppercase tracking-wider text-[#E0A526] mb-2">
            El Equipo AMP
          </p>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
            Conoce a tus Mentores
          </h2>
          <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9]">
            Cada uno aporta un don único y una especialidad para acompañarte en tu momento de vida.
          </p>
        </div>

        <div className="space-y-12">
          {COACHES.map((coach, idx) => {
            const isEven = idx % 2 === 0;
            return (
              <div
                key={coach.id}
                id={coach.id}
                className={`bg-white dark:bg-[#1E1B3A] rounded-3xl p-6 sm:p-10 border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm flex flex-col md:flex-row items-center gap-8 ${
                  isEven ? '' : 'md:flex-row-reverse'
                }`}
              >
                {/* Photo & Badge placeholder */}
                <div className="w-full md:w-56 shrink-0 text-center">
                  <div className="w-40 h-40 sm:w-48 sm:h-48 mx-auto rounded-3xl overflow-hidden shadow-lg border-2 border-[#E0A526]/30 mb-3 relative group">
                    <img
                      src={coach.photoPlaceholder}
                      alt={coach.name}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-x-0 bottom-0 bg-black/60 text-white text-[10px] py-1 px-2 font-mono">
                      Foto temporal (reemplazar)
                    </div>
                  </div>
                  <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#E0A526]/10 text-[#B8860B] dark:text-[#F2C14E]">
                    Coach Verificado AMP
                  </span>
                </div>

                {/* Info & Bio */}
                <div className="flex-1 space-y-4 text-left">
                  <div>
                    <h3 className="font-serif text-2xl sm:text-3xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                      {coach.name}
                    </h3>
                    <p className="text-sm font-semibold text-[#E0A526]">
                      {coach.role}
                    </p>
                  </div>

                  {/* Quote */}
                  <blockquote className="border-l-4 border-[#E0A526] pl-4 italic text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9]">
                    &ldquo;{coach.tagline}&rdquo;
                  </blockquote>

                  {/* Bio */}
                  <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
                    {coach.bio}
                  </p>

                  {/* Specialties */}
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-[#2B2622] dark:text-[#F4EFE8] mb-2">
                      Especialidades & Enfoque:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {coach.specialties.map((spec) => (
                        <span
                          key={spec}
                          className="text-xs px-3 py-1 rounded-full bg-black/5 dark:bg-white/5 text-[#2B2622] dark:text-[#F4EFE8] font-medium"
                        >
                          {spec}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* CTAs */}
                  <div className="pt-2 flex flex-wrap gap-3">
                    <Link
                      href={`/agenda?coach=${coach.id}`}
                      className="px-5 py-2.5 rounded-full bg-[#E0A526] hover:bg-[#B8860B] text-white font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-colors shadow-sm"
                    >
                      <Calendar size={14} /> Reservar Sesión 1:1 con {coach.name.split(' ')[0]}
                    </Link>
                    <Link
                      href={`/biblioteca?coach=${coach.id}`}
                      className="px-5 py-2.5 rounded-full border border-[#E0A526]/40 hover:border-[#E0A526] text-[#2B2622] dark:text-[#F4EFE8] font-bold text-xs uppercase tracking-wider flex items-center gap-1.5 transition-colors"
                    >
                      Ver meditaciones guiadas
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── PLACEHOLDER REPLACEMENT NOTICE FOR JUAN ── */}
      <div className="p-4 rounded-2xl bg-[#FFE3B3]/25 dark:bg-[#1E1B3A] border border-[#E0A526]/30 text-xs text-[#6B625A] dark:text-[#B9B2C9] flex items-start gap-3">
        <AlertCircle size={18} className="text-[#E0A526] shrink-0 mt-0.5" />
        <div>
          <strong className="text-[#2B2622] dark:text-[#F4EFE8]">Nota para Juan Diego y el equipo AMP:</strong> Las fotografías actuales son fotos de archivo de alta definición marcadas como marcadores de posición temporales. En la fase de contenido final, se reemplazarán por las sesiones de fotos oficiales en estudio con luz dorada de Juan Diego Giraldo, Andrea Silva, Dericielo Jiménez y Lina Valencia Triviño.
        </div>
      </div>
    </div>
  );
}
