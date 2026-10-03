'use client';

import React, { useState } from 'react';
import { COACHES } from '@/lib/amp-content';
import { Calendar, Clock, Video, CheckCircle2, Sparkles, ExternalLink, ShieldCheck } from 'lucide-react';

export default function AgendaPage() {
  const [selectedCoach, setSelectedCoach] = useState(COACHES[0].id);

  const calUrl = process.env.NEXT_PUBLIC_CALCOM_URL ||
    `https://cal.com/amp-edition/${selectedCoach}`;

  const currentCoach = COACHES.find(c => c.id === selectedCoach) || COACHES[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Agenda & Encuentros 1:1
        </div>
        <h1 className="font-serif text-3xl sm:text-5xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
          Reserva tu Sesión Privada con un Mentor
        </h1>
        <p className="text-sm sm:text-base text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
          Elige a tu guía de preferencia y selecciona un espacio privado de 60 minutos por videollamada para destrabar metas, sanar bloqueos o transiciones de vida.
        </p>
      </div>

      {/* ── COACH SELECTOR TABS (Mindvalley style) ── */}
      <div className="flex flex-wrap justify-center gap-3 mb-12">
        {COACHES.map((coach) => {
          const isSelected = selectedCoach === coach.id;
          return (
            <button
              key={coach.id}
              onClick={() => setSelectedCoach(coach.id)}
              className={`px-5 py-3.5 rounded-2xl border text-sm font-semibold transition-all flex items-center gap-3.5 ${
                isSelected
                  ? 'border-[#E0A526] bg-[#E0A526] text-white shadow-lg scale-102'
                  : 'border-[#EFE6D8] dark:border-[#2B254E] glass-card text-[#1E1A17] dark:text-[#F6F3EE] hover:border-[#E0A526]'
              }`}
            >
              <div className="w-10 h-10 rounded-full overflow-hidden shrink-0 ring-2 ring-white/40">
                <img src={coach.photoLocal} alt={coach.name} className="w-full h-full object-cover" />
              </div>
              <div className="text-left">
                <p className="font-bold leading-tight text-sm">{coach.name}</p>
                <p className={`text-[11px] leading-tight ${isSelected ? 'text-white/80' : 'text-[#E0A526]'}`}>
                  {coach.role.split('&')[0]}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* ── BOOKING CONTAINER ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-20">
        {/* Left Side: Coach session details */}
        <div className="glass-card p-6 sm:p-8 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] space-y-6 shadow-md">
          <div>
            <div className="w-24 h-24 rounded-2xl overflow-hidden mb-4 border-2 border-[#E0A526]/30 shadow">
              <img src={currentCoach.photoLocal} alt={currentCoach.name} className="w-full h-full object-cover" />
            </div>
            <h3 className="font-serif text-2xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
              {currentCoach.name}
            </h3>
            <p className="text-xs font-semibold text-[#E0A526] mt-1">{currentCoach.role}</p>
          </div>

          <div className="space-y-3.5 text-xs text-[#5C544D] dark:text-[#B4ACC5]">
            <div className="flex items-center gap-2.5">
              <Clock size={16} className="text-[#E0A526] shrink-0" />
              <span>Sesión privada de 60 minutos</span>
            </div>
            <div className="flex items-center gap-2.5">
              <Video size={16} className="text-[#E0A526] shrink-0" />
              <span>Videollamada 1:1 en sala privada (Google Meet / Zoom)</span>
            </div>
            <div className="flex items-center gap-2.5">
              <CheckCircle2 size={16} className="text-[#E0A526] shrink-0" />
              <span>Plan de acción e integración posterior a la sesión</span>
            </div>
            <div className="flex items-center gap-2.5">
              <ShieldCheck size={16} className="text-[#7E9F84] shrink-0" />
              <span>Confidencialidad absoluta y ética profesional garantizada</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-xs space-y-2">
            <span className="font-bold text-[#1E1A17] dark:text-[#F6F3EE] block">Enfoques de {currentCoach.name.split(' ')[0]}:</span>
            <ul className="list-disc list-inside space-y-1 text-[#5C544D] dark:text-[#B4ACC5]">
              {currentCoach.specialties.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right Side: Interactive Cal.com Scheduler Embed */}
        <div className="lg:col-span-2 glass-card rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] p-6 sm:p-8 flex flex-col justify-between shadow-md">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-serif text-xl sm:text-2xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                Selecciona Fecha y Hora
              </h4>
              <span className="text-xs px-3 py-1 rounded-full bg-[#7E9F84]/15 text-[#5A7A60] dark:text-[#9DBFA2] font-semibold">
                Detección automática de zona horaria
              </span>
            </div>

            <p className="text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed mb-6">
              Módulo sincronizado con Cal.com / Google Calendar (configurable mediante la variable de entorno <code className="bg-black/5 dark:bg-white/10 px-1.5 py-0.5 rounded font-mono text-xs">NEXT_PUBLIC_CALCOM_URL</code>).
            </p>

            {/* Interactive Scheduler Container */}
            <div className="w-full h-84 sm:h-96 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border-2 border-dashed border-[#E0A526]/40 flex flex-col items-center justify-center p-6 text-center space-y-4">
              <div className="w-16 h-16 rounded-3xl bg-[#E0A526]/15 flex items-center justify-center text-[#E0A526]">
                <Calendar size={32} className="animate-pulse" />
              </div>
              <div>
                <h5 className="font-serif font-bold text-lg text-[#1E1A17] dark:text-[#F6F3EE] mb-1">
                  Agenda Disponible: {currentCoach.name}
                </h5>
                <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5] max-w-sm mx-auto">
                  Haz clic para abrir el agendador interactivo en vivo y asegurar tu espacio:
                </p>
              </div>

              <a
                href={calUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-7 py-3.5 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow-lg hover:scale-105 active:scale-95 transition-all no-underline"
              >
                Abrir Agendador Cal.com <ExternalLink size={14} />
              </a>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-black/5 dark:border-white/5 flex flex-col sm:flex-row items-center justify-between text-xs text-[#5C544D] dark:text-[#B4ACC5] gap-2">
            <span>Cancelación o reprogramación gratuita hasta 24 horas antes</span>
            <span className="font-semibold text-[#E0A526]">15% de descuento para miembros Premium</span>
          </div>
        </div>
      </div>
    </div>
  );
}
