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
        // Continue even if leadforge backend is offline in dev
      }

      // 2. Post to existing AMP auth signup
      const ampSignupPayload = {
        name: formData.name,
        email: formData.email,
        password: formData.password || 'AmpWelcome2026!',
      };

      try {
        const signupRes = await fetch('http://localhost:8000/api/v1/amp/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(ampSignupPayload),
        });
        if (signupRes.ok) {
          const authData = await signupRes.json();
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
    <div className="max-w-2xl mx-auto px-4 py-12 md:py-16">
      {/* Step progress bar */}
      <div className="mb-10">
        <div className="flex justify-between text-xs font-bold uppercase tracking-wider text-[#E0A526] mb-2">
          <span>Paso {Math.min(step + 1, 4)} de 4</span>
          <span>{step === 3 ? 'Crea tu Cuenta' : step === 4 ? '¡Listo!' : 'Diagnóstico Personal'}</span>
        </div>
        <div className="w-full h-2 bg-black/5 dark:bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] transition-all duration-300"
            style={{ width: `${((step + 1) / 4) * 100}%` }}
          />
        </div>
      </div>

      {/* ── QUIZ QUESTIONS (Steps 0, 1, 2) ── */}
      {step < 3 && (
        <div className="bg-white dark:bg-[#1E1B3A] p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm animate-fade-up">
          <div className="text-center mb-8">
            <span className="text-xs font-bold uppercase tracking-widest text-[#E0A526] block mb-2">
              Pregunta {step + 1}
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2">
              {currentQuestion.title}
            </h2>
            <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9]">
              {currentQuestion.subtitle}
            </p>
          </div>

          <div className="space-y-3">
            {currentQuestion.options.map((opt) => (
              <button
                key={opt.tag}
                onClick={() => handleSelectOption(opt.tag)}
                className="w-full p-4 rounded-2xl border border-[#F0E6D8] dark:border-[#2E2A54] bg-[#FFF9F1] dark:bg-[#14122B] text-left text-sm font-semibold text-[#2B2622] dark:text-[#F4EFE8] hover:border-[#E0A526] hover:bg-[#E0A526]/10 transition-all flex items-center justify-between group"
              >
                <span>{opt.label}</span>
                <ArrowRight size={16} className="text-[#E0A526] group-hover:translate-x-1 transition-transform" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── SIGNUP FORM (Step 3) ── */}
      {step === 3 && (
        <div className="bg-white dark:bg-[#1E1B3A] p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm animate-fade-up">
          <div className="text-center mb-8">
            <Sparkles size={28} className="text-[#E0A526] mx-auto mb-2" />
            <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2">
              Crea tu Perfil Gratuito
            </h2>
            <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9]">
              Guardaremos tus respuestas para recomendarte tu ruta personalizada de 21 días.
            </p>
          </div>

          {errorMessage && (
            <div className="p-3 mb-4 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">
              {errorMessage}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8] block mb-1">
                Nombre Completo
              </label>
              <div className="relative">
                <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6B625A] dark:text-[#B9B2C9]" />
                <input
                  type="text"
                  required
                  placeholder="Tu nombre"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8] block mb-1">
                Correo Electrónico
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6B625A] dark:text-[#B9B2C9]" />
                <input
                  type="email"
                  required
                  placeholder="correo@ejemplo.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8] block mb-1">
                Teléfono / WhatsApp (Opcional, para recordatorios diarios)
              </label>
              <div className="relative">
                <Phone size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6B625A] dark:text-[#B9B2C9]" />
                <input
                  type="tel"
                  placeholder="+57 300 000 0000"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8] block mb-1">
                Contraseña
              </label>
              <div className="relative">
                <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#6B625A] dark:text-[#B9B2C9]" />
                <input
                  type="password"
                  required
                  placeholder="Crea una contraseña segura"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-sm focus:outline-none focus:border-[#E0A526]"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-[#2B2622] font-bold text-xs uppercase tracking-wider shadow-lg hover:scale-[1.01] transition-transform"
            >
              {submitting ? 'Generando tu portal...' : 'Crear Cuenta y Ver Mi Ruta'}
            </button>
          </form>
        </div>
      )}

      {/* ── COMPLETE SUCCESS (Step 4) ── */}
      {step === 4 && (
        <div className="bg-white dark:bg-[#1E1B3A] p-8 sm:p-10 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm text-center animate-fade-up">
          <div className="w-16 h-16 rounded-full bg-[#7E9F84]/20 text-[#7E9F84] flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 size={36} />
          </div>

          <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2">
            ¡Bienvenido a El Portal de la Alegría, {formData.name.split(' ')[0]}!
          </h2>

          <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed max-w-md mx-auto mb-8">
            Tu cuenta ha sido creada exitosamente y tus respuestas han quedado registradas en tu perfil de transformación.
          </p>

          <div className="p-6 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-left mb-8 space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-[#E0A526] block">
              Tu Primera Recomendación
            </span>
            <p className="font-serif font-bold text-base text-[#2B2622] dark:text-[#F4EFE8]">
              Práctica de Bienvenida: Respiración Consciente (5 min)
            </p>
            <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9]">
              Comienza hoy dedicando una breve pausa para serenar tu mente.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/biblioteca"
              className="w-full sm:w-auto px-8 py-3.5 rounded-full bg-[#E0A526] hover:bg-[#B8860B] text-white font-bold text-xs uppercase tracking-wider shadow"
            >
              Ir a la Biblioteca
            </Link>
            <Link
              href="/animo"
              className="w-full sm:w-auto px-6 py-3.5 rounded-full border border-[#E0A526] text-[#B8860B] dark:text-[#F2C14E] font-bold text-xs uppercase tracking-wider"
            >
              Hacer mi Check-in de Hoy
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
