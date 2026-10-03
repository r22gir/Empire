'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Sparkles, ArrowRight, CheckCircle2, User, Mail, Lock, Phone } from 'lucide-react';

const QUIZ_QUESTIONS = [
  {
    id: 'goal',
    title: '¿Cuál es tu principal anhelo en este momento?',
    subtitle: 'Selecciona lo que resuena más fuerte con tu corazón hoy',
    options: [
      { label: 'Calmar la ansiedad y encontrar paz interior', tag: 'ansiedad' },
      { label: 'Superar un momento de duelo, separación o dolor', tag: 'duelo' },
      { label: 'Aumentar mi amor propio y merecimiento', tag: 'autoestima' },
      { label: 'Liderar mi vida y proyectos con propósito', tag: 'liderazgo' },
      { label: 'Aprender a educar a mis hijos con amor y calma', tag: 'familia' },
    ],
  },
  {
    id: 'experience',
    title: '¿Cuál es tu experiencia con la meditación o el coaching?',
    subtitle: 'No se requiere experiencia previa para empezar',
    options: [
      { label: 'Soy principiante absoluto, busco una guía sencilla', tag: 'principiante' },
      { label: 'He meditado antes pero me cuesta mantener el hábito', tag: 'intermedio' },
      { label: 'Practico con frecuencia y busco profundizar con coaches', tag: 'avanzado' },
    ],
  },
  {
    id: 'time',
    title: '¿Cuánto tiempo puedes dedicar a tu bienestar al día?',
    subtitle: 'Pequeñas dosis consistentes logran milagros',
    options: [
      { label: '5 a 10 minutos por la mañana o antes de dormir', tag: '5_10min' },
      { label: '15 a 20 minutos con una pausa consciente', tag: '15_20min' },
      { label: 'Más de 30 minutos (quiero sumarme a retos profundos)', tag: '30min+' },
    ],
  },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(0); // 0, 1, 2 = quiz, 3 = signup form, 4 = complete
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    phone: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const currentQuestion = QUIZ_QUESTIONS[step];

  const handleSelectOption = (tag: string) => {
    setAnswers({ ...answers, [currentQuestion.id]: tag });
    if (step < QUIZ_QUESTIONS.length - 1) {
      setStep(step + 1);
    } else {
      setStep(3); // Go to signup step
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMessage('');

    try {
      // 1. Post to LeadForge / CRM leads intake
      const leadPayload = {
        first_name: formData.name.split(' ')[0] || formData.name,
        last_name: formData.name.split(' ').slice(1).join(' ') || '',
        email: formData.email,
        phone: formData.phone || undefined,
        source: 'amp_public_onboarding_quiz',
        business_unit: 'empire_saas',
        tags: ['amp', 'onboarding_quiz', answers.goal, answers.experience],
        notes: `Quiz answers: Meta=${answers.goal}, Experiencia=${answers.experience}, Tiempo=${answers.time}`,
      };

      try {
        await fetch('http://localhost:8000/api/v1/leads/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(leadPayload),
        });
      } catch {
        // Continue gracefully even if CRM is offline in dev
      }

      // 2. Post to existing AMP Auth signup API
      try {
        const authPayload = {
          email: formData.email,
          password: formData.password,
          full_name: formData.name,
          phone: formData.phone || undefined,
        };

        const res = await fetch('http://localhost:8000/api/v1/amp/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(authPayload),
        });

        if (res.ok) {
          const authData = await res.json();
          if (authData.token) {
            localStorage.setItem('amp_token', authData.token);
          }
        }
      } catch {
        // Local fallback
      }

      // Save user session in localStorage for client-side persistence
      localStorage.setItem('amp-user-email', formData.email);
      localStorage.setItem('amp-user-name', formData.name);
      localStorage.setItem('amp-quiz-profile', JSON.stringify(answers));

      setStep(4); // completed state
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Error al completar el registro.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12 md:py-20">
      {/* Step progress bar */}
      <div className="mb-12">
        <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-[#E0A526] mb-2.5">
          <span>Paso {Math.min(step + 1, 4)} de 4</span>
          <span>{step === 3 ? 'Crea tu Cuenta' : step === 4 ? '¡Listo!' : 'Diagnóstico Personal'}</span>
        </div>
        <div className="w-full h-2 bg-black/5 dark:bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#E0A526] via-[#F28C6B] to-[#7E9F84] transition-all duration-300"
            style={{ width: `${((step + 1) / 4) * 100}%` }}
          />
        </div>
      </div>

      {/* ── QUIZ QUESTIONS (Steps 0, 1, 2) ── */}
      {step < 3 && (
        <div className="glass-card p-8 sm:p-12 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] shadow-xl animate-fade-up">
          <div className="text-center mb-10">
            <span className="text-xs font-bold uppercase tracking-widest text-[#E0A526] block mb-2">
              Pregunta {step + 1}
            </span>
            <h2 className="font-serif text-3xl sm:text-4xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-3">
              {currentQuestion.title}
            </h2>
            <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5]">
              {currentQuestion.subtitle}
            </p>
          </div>

          <div className="space-y-3.5">
            {currentQuestion.options.map((opt) => (
              <button
                key={opt.tag}
                onClick={() => handleSelectOption(opt.tag)}
                className="w-full p-5 rounded-2xl border border-[#EFE6D8] dark:border-[#2B254E] bg-white/70 dark:bg-white/5 text-left text-sm sm:text-base font-semibold text-[#1E1A17] dark:text-[#F6F3EE] hover:border-[#E0A526] hover:bg-[#E0A526]/10 transition-all flex items-center justify-between group shadow-sm hover:scale-[1.01]"
              >
                <span>{opt.label}</span>
                <ArrowRight size={18} className="text-[#E0A526] group-hover:translate-x-1.5 transition-transform" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── SIGNUP FORM (Step 3) ── */}
      {step === 3 && (
        <div className="glass-card p-8 sm:p-12 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] shadow-xl animate-fade-up">
          <div className="text-center mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#E0A526] to-[#F28C6B] flex items-center justify-center text-white mx-auto mb-4 shadow-lg">
              <Sparkles size={28} />
            </div>
            <h2 className="font-serif text-3xl sm:text-4xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-2">
              Crea tu Perfil Gratuito
            </h2>
            <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5]">
              Guardaremos tus respuestas para recomendarte tu ruta personalizada de 21 días.
            </p>
          </div>

          {errorMessage && (
            <div className="p-3.5 mb-6 rounded-2xl bg-red-50 text-red-700 text-xs font-semibold border border-red-200">
              {errorMessage}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE] block mb-1">
                Nombre Completo
              </label>
              <div className="relative">
                <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5C544D] dark:text-[#B4ACC5]" />
                <input
                  type="text"
                  required
                  placeholder="Tu nombre y apellido"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full pl-10 pr-4 py-3.5 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE] block mb-1">
                Correo Electrónico
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5C544D] dark:text-[#B4ACC5]" />
                <input
                  type="email"
                  required
                  placeholder="ejemplo@correo.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full pl-10 pr-4 py-3.5 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE] block mb-1">
                Teléfono / WhatsApp (opcional)
              </label>
              <div className="relative">
                <Phone size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5C544D] dark:text-[#B4ACC5]" />
                <input
                  type="tel"
                  placeholder="+57 300 123 4567"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full pl-10 pr-4 py-3.5 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE] block mb-1">
                Contraseña
              </label>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5C544D] dark:text-[#B4ACC5]" />
                <input
                  type="password"
                  required
                  placeholder="Crea una contraseña segura"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full pl-10 pr-4 py-3.5 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white font-bold text-xs uppercase tracking-wider shadow-xl hover:scale-[1.01] transition-transform mt-4"
            >
              {submitting ? 'Generando tu portal...' : 'Crear Cuenta y Ver Mi Ruta'}
            </button>
          </form>
        </div>
      )}

      {/* ── COMPLETE SUCCESS (Step 4) ── */}
      {step === 4 && (
        <div className="glass-card p-8 sm:p-12 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] shadow-xl text-center animate-fade-up">
          <div className="w-16 h-16 rounded-full bg-[#7E9F84]/20 text-[#7E9F84] flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 size={36} />
          </div>

          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-2">
            ¡Bienvenido a El Portal de la Alegría, {formData.name.split(' ')[0]}!
          </h2>

          <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed max-w-md mx-auto mb-8">
            Tu cuenta ha sido creada exitosamente y tus respuestas han quedado registradas en tu perfil de transformación.
          </p>

          <div className="p-6 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-left mb-8 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-[#E0A526] block">
              Tu Primera Recomendación
            </span>
            <p className="font-serif font-bold text-base text-[#1E1A17] dark:text-[#F6F3EE]">
              Práctica de Bienvenida: Respiración Consciente para la Calma (5 min)
            </p>
            <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5]">
              Comienza hoy dedicando una breve pausa para serenar tu mente.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/biblioteca"
              className="px-8 py-3.5 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white font-bold text-xs uppercase tracking-wider shadow-md hover:scale-105 transition-all no-underline"
            >
              Ir a la Biblioteca Sonora
            </Link>
            <Link
              href="/"
              className="px-8 py-3.5 rounded-full border-2 border-[#E0A526] text-[#C68C14] dark:text-[#F2C14E] font-bold text-xs uppercase tracking-wider hover:bg-[#E0A526]/10 transition-colors no-underline"
            >
              Ir al Inicio
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
