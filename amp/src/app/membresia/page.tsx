'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Sparkles, Check } from 'lucide-react';

export default function MembresiaPage() {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
  const [loadingTier, setLoadingTier] = useState<string | null>(null);

  const handleSubscribe = async (tier: string) => {
    setLoadingTier(tier);
    try {
      const returnBase = window.location.origin;
      const res = await fetch('http://localhost:8000/api/v1/payments/create-checkout-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tier: tier,
          success_url: `${returnBase}/membresia?status=success`,
          cancel_url: `${returnBase}/membresia?status=cancel`,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
          return;
        }
      }
      // If Stripe backend not set or test mode simulation:
      alert('Modo de prueba de Stripe: Configura STRIPE_SECRET_KEY y STRIPE_PRICE_PRO para redirigir a Checkout en vivo.');
    } catch {
      alert('Modo de prueba: El servidor local de pagos procesa la suscripción con éxito simulado.');
    } finally {
      setLoadingTier(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-12 md:py-16">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-14">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Membresía El Portal de la Alegría
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
          Invierte en tu Paz Mental y Crecimiento
        </h1>
        <p className="text-sm sm:text-base text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
          Comienza gratis para siempre con nuestras prácticas fundamentales, o profundiza con acceso total a toda la biblioteca de meditaciones y retos de 21 días.
        </p>

        {/* Monthly / Annual Toggle */}
        <div className="inline-flex items-center bg-black/5 dark:bg-white/5 p-1 rounded-full mt-6 border border-[#F0E6D8] dark:border-[#2E2A54]">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`px-5 py-2 rounded-full text-xs font-bold transition-all ${
              billingCycle === 'monthly'
                ? 'bg-[#E0A526] text-white shadow-sm'
                : 'text-[#6B625A] dark:text-[#B9B2C9]'
            }`}
          >
            Facturación Mensual
          </button>
          <button
            onClick={() => setBillingCycle('annual')}
            className={`px-5 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
              billingCycle === 'annual'
                ? 'bg-[#E0A526] text-white shadow-sm'
                : 'text-[#6B625A] dark:text-[#B9B2C9]'
            }`}
          >
            Anual <span className="text-[10px] bg-[#7E9F84] text-white px-2 py-0.5 rounded-full">Ahorra 33%</span>
          </button>
        </div>
      </div>

      {/* ── PRICING CARDS ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-20">
        {/* FREE PLAN */}
        <div className="bg-white dark:bg-[#1E1B3A] rounded-3xl p-8 border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                  Gratis
                </h3>
                <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9]">Para iniciar tu camino de bienestar</p>
              </div>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-black/5 dark:bg-white/5 text-[#6B625A] dark:text-[#B9B2C9]">
                Para siempre
              </span>
            </div>

            <div className="my-6">
              <span className="text-4xl font-serif font-bold text-[#2B2622] dark:text-[#F4EFE8]">$0</span>
              <span className="text-xs text-[#6B625A] dark:text-[#B9B2C9] ml-1">USD / mes</span>
            </div>

            <ul className="space-y-3 text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] mb-8">
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#7E9F84]" /> Check-in de ánimo diario con recomendaciones
              </li>
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#7E9F84]" /> Afirmación del día y 1 meditación diaria
              </li>
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#7E9F84]" /> Reto básico de 21 días de Gratitud
              </li>
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#7E9F84]" /> Artículos del blog y reflexiones abiertas
              </li>
            </ul>
          </div>

          <Link
            href="/onboarding"
            className="w-full py-3.5 rounded-2xl border-2 border-[#E0A526] text-[#B8860B] dark:text-[#F2C14E] font-bold text-xs uppercase tracking-wider text-center hover:bg-[#E0A526]/10 transition-colors"
          >
            Registrarme Gratis
          </Link>
        </div>

        {/* PREMIUM PLAN */}
        <div className="bg-white dark:bg-[#1E1B3A] rounded-3xl p-8 border-2 border-[#E0A526] shadow-xl relative flex flex-col justify-between">
          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-[#2B2622] font-bold text-[11px] uppercase tracking-wider px-4 py-1 rounded-full shadow">
            7 Días de Prueba Gratis
          </div>

          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                  Premium Alegría
                </h3>
                <p className="text-xs text-[#E0A526] font-semibold">Acceso total e ilimitado</p>
              </div>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#E0A526]/15 text-[#B8860B] dark:text-[#F2C14E]">
                Más elegido
              </span>
            </div>

            <div className="my-6">
              {billingCycle === 'monthly' ? (
                <>
                  <span className="text-4xl font-serif font-bold text-[#2B2622] dark:text-[#F4EFE8]">$9.99</span>
                  <span className="text-xs text-[#6B625A] dark:text-[#B9B2C9] ml-1">USD / mes</span>
                </>
              ) : (
                <>
                  <span className="text-4xl font-serif font-bold text-[#2B2622] dark:text-[#F4EFE8]">$79.99</span>
                  <span className="text-xs text-[#6B625A] dark:text-[#B9B2C9] ml-1">USD / año ($6.66/mes)</span>
                </>
              )}
            </div>

            <ul className="space-y-3 text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] mb-8">
              <li className="flex items-center gap-2 font-semibold text-[#2B2622] dark:text-[#F4EFE8]">
                <Check size={16} className="text-[#E0A526]" /> Todo lo incluido en el plan Gratuito
              </li>
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#E0A526]" /> Biblioteca completa de audios temáticos (ansiedad, sueño, duelo, liderazgo)
              </li>
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#E0A526]" /> Todos los retos de transformación de 14 y 21 días
              </li>
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#E0A526]" /> Encuentro grupal mensual en vivo por videollamada con los coaches
              </li>
              <li className="flex items-center gap-2">
                <Check size={16} className="text-[#E0A526]" /> 15% de descuento en sesiones de coaching individual 1:1
              </li>
            </ul>
          </div>

          <button
            onClick={() => handleSubscribe('pro')}
            disabled={loadingTier !== null}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-[#2B2622] font-bold text-xs uppercase tracking-wider shadow-lg hover:scale-[1.02] transition-transform"
          >
            {loadingTier === 'pro' ? 'Conectando con Stripe...' : 'Comenzar 7 Días Gratis'}
          </button>
        </div>
      </div>

      {/* ── FAQ ACCORDION ── */}
      <div className="max-w-3xl mx-auto">
        <h2 className="font-serif text-2xl sm:text-3xl font-bold text-center text-[#2B2622] dark:text-[#F4EFE8] mb-8">
          Preguntas Frecuentes
        </h2>

        <div className="space-y-4">
          <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-2xl border border-[#F0E6D8] dark:border-[#2E2A54]">
            <h4 className="font-serif font-bold text-base text-[#2B2622] dark:text-[#F4EFE8] mb-2">
              ¿Cómo funciona la prueba gratuita de 7 días?
            </h4>
            <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
              Tienes acceso completo a toda la plataforma durante una semana sin costo alguno. Puedes cancelar en cualquier momento con un solo clic desde tu perfil antes del séptimo día y no se te cobrará nada.
            </p>
          </div>

          <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-2xl border border-[#F0E6D8] dark:border-[#2E2A54]">
            <h4 className="font-serif font-bold text-base text-[#2B2622] dark:text-[#F4EFE8] mb-2">
              ¿Qué métodos de pago aceptan?
            </h4>
            <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
              Aceptamos todas las tarjetas de crédito y débito internacionales (Visa, Mastercard, American Express) a través de Stripe con cifrado de grado bancario. Para Colombia, también habilitamos PSE y transferencia bancaria para paquetes y talleres.
            </p>
          </div>

          <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-2xl border border-[#F0E6D8] dark:border-[#2E2A54]">
            <h4 className="font-serif font-bold text-base text-[#2B2622] dark:text-[#F4EFE8] mb-2">
              ¿Puedo agendar sesiones 1:1 sin ser miembro Premium?
            </h4>
            <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
              Sí, las sesiones individuales están abiertas para cualquier persona a través de nuestra sección de Agenda. Sin embargo, los miembros Premium disfrutan de tarifas preferenciales.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
