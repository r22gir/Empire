'use client';

import React, { useState } from 'react';
import { COACHES } from '@/lib/amp-content';
import { Calendar, Clock, Video, CheckCircle2, Sparkles, ExternalLink } from 'lucide-react';

export default function AgendaPage() {
  const [selectedCoach, setSelectedCoach] = useState(COACHES[0].id);

  const calUrl = process.env.NEXT_PUBLIC_CALCOM_URL ||
    `https://cal.com/amp-edition/${selectedCoach}`;

  const currentCoach = COACHES.find(c => c.id === selectedCoach) || COACHES[0];

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 md:py-16">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Agenda & Encuentros
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
          Reserva tu Sesión 1:1 o Asiste a un Taller
        </h1>
        <p className="text-sm sm:text-base text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
          Elige tu coach de preferencia y agenda fácilmente un espacio privado de acompañamiento virtual por videollamada.
        </p>
      </div>

      {/* ── COACH SELECTOR TABS ── */}
      <div className="flex flex-wrap justify-center gap-3 mb-10">
        {COACHES.map((coach) => {
          const isSelected = selectedCoach === coach.id;
          return (
            <button
              key={coach.id}
              onClick={() => setSelectedCoach(coach.id)}
              className={`px-5 py-3 rounded-2xl border text-sm font-semibold transition-all flex items-center gap-3 ${
                isSelected
                  ? 'border-[#E0A526] bg-[#E0A526] text-white shadow-md'
                  : 'border-[#F0E6D8] dark:border-[#2E2A54] bg-white dark:bg-[#1E1B3A] text-[#2B2622] dark:text-[#F4EFE8] hover:border-[#E0A526]'
              }`}
            >
              <div className="w-8 h-8 rounded-full overflow-hidden shrink-0">
                <img src={coach.photoPlaceholder} alt={coach.name} className="w-full h-full object-cover" />
              </div>
              <div className="text-left">
                <p className="font-bold leading-tight">{coach.name}</p>
                <p className={`text-[11px] leading-tight ${isSelected ? 'text-white/80' : 'text-[#E0A526]'}`}>
                  {coach.role.split('&')[0]}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* ── BOOKING EMBED & DETAILS CONTAINER ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-16">
        {/* Left Side: Coach session details */}
        <div className="bg-white dark:bg-[#1E1B3A] p-6 sm:p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] space-y-6">
          <div>
            <div className="w-20 h-20 rounded-2xl overflow-hidden mb-4 border-2 border-[#E0A526]/30">
              <img src={currentCoach.photoPlaceholder} alt={currentCoach.name} className="w-full h-full object-cover" />
            </div>
            <h3 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
              {currentCoach.name}
            </h3>
            <p className="text-xs font-semibold text-[#E0A526] mt-0.5">{currentCoach.role}</p>
          </div>

          <div className="space-y-3 text-xs text-[#6B625A] dark:text-[#B9B2C9]">
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-[#E0A526]" />
              <span>Sesión privada de 60 minutos</span>
            </div>
            <div className="flex items-center gap-2">
              <Video size={16} className="text-[#E0A526]" />
              <span>Videollamada en vivo (enlace automático)</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-[#E0A526]" />
              <span>Plan de acción personalizado tras la llamada</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-xs space-y-1">
            <span className="font-bold text-[#2B2622] dark:text-[#F4EFE8]">Especialidades:</span>
            <ul className="list-disc list-inside space-y-0.5 text-[#6B625A] dark:text-[#B9B2C9]">
              {currentCoach.specialties.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right Side: Booking embed placeholder / iframe configurable via env */}
        <div className="lg:col-span-2 bg-white dark:bg-[#1E1B3A] rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] p-6 sm:p-8 flex flex-col justify-between shadow-sm">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-serif text-xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                Selecciona Fecha y Hora
              </h4>
              <span className="text-xs px-2.5 py-1 rounded-full bg-[#E4EDE6] text-[#5A7A60] dark:text-[#9DBFA2] font-semibold">
                Zona horaria automática
              </span>
            </div>

            <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-6">
              Esta sección está integrada con Cal.com / Google Calendar (configurable mediante la variable de entorno <code className="bg-black/5 dark:bg-white/10 px-1.5 py-0.5 rounded font-mono text-xs">NEXT_PUBLIC_CALCOM_URL</code>).
            </p>

            {/* Embed Frame / Mock Interactive scheduler */}
            <div className="w-full h-80 sm:h-96 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border-2 border-dashed border-[#E0A526]/40 flex flex-col items-center justify-center p-6 text-center space-y-4">
              <Calendar size={40} className="text-[#E0A526] animate-pulse-slow" />
              <div>
                <h5 className="font-serif font-bold text-lg text-[#2B2622] dark:text-[#F4EFE8] mb-1">
                  Calendario de Disponibilidad: {currentCoach.name}
                </h5>
                <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] max-w-sm mx-auto">
                  Para agendar en vivo en tu navegador o abrir directamente en Cal.com:
                </p>
              </div>

              <a
                href={calUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-[#2B2622] font-bold text-xs uppercase tracking-wider flex items-center gap-2 shadow hover:scale-105 transition-all no-underline"
              >
                Abrir Agenda de {currentCoach.name.split(' ')[0]} en Cal.com <ExternalLink size={14} />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
