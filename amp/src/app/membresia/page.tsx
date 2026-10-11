'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Sparkles, Check, HelpCircle } from 'lucide-react';

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
      alert('Modo de prueba de Stripe: Configura STRIPE_SECRET_KEY y STRIPE_PRICE_PRO para redirigir a Checkout en vivo.');
    } catch {
      alert('Modo de prueba: El servidor local de pagos procesa la suscripción con éxito simulado.');
    } finally {
      setLoadingTier(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 md:py-20">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-4">
          <Sparkles size={14} /> Membresía El Portal de la Alegría
        </div>
        <h1 className="font-serif text-3xl sm:text-5xl md:text-6xl font-extrabold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
          Invierte en tu Paz Mental y Crecimiento
        </h1>
        <p className="text-sm sm:text-base text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
          Comienza gratis para siempre con nuestras prácticas fundamentales, o profundiza con acceso total a toda la biblioteca de meditaciones y retos de 21 días.
        </p>

        {/* Monthly / Annual Toggle */}
        <div className="inline-flex items-center bg-black/5 dark:bg-white/5 p-1.5 rounded-full mt-8 border border-[#EFE6D8] dark:border-[#2B254E]">
          <button
            onClick={() => setBillingCycle('monthly')}
            className={`px-6 py-2.5 rounded-full text-xs font-bold transition-all ${
              billingCycle === 'monthly'
                ? 'bg-[#E0A526] text-white shadow-md'
                : 'text-[#5C544D] dark:text-[#B4ACC5]'
            }`}
          >
            Facturación Mensual
          </button>
          <button
            onClick={() => setBillingCycle('annual')}
            className={`px-6 py-2.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 ${
              billingCycle === 'annual'
                ? 'bg-[#E0A526] text-white shadow-md'
                : 'text-[#5C544D] dark:text-[#B4ACC5]'
            }`}
          >
            Anual <span className="text-[10px] bg-[#7E9F84] text-white px-2 py-0.5 rounded-full font-extrabold">Ahorra 33%</span>
          </button>
        </div>
      </div>

      {/* ── PRICING CARDS ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-24">
        {/* FREE PLAN */}
        <div className="glass-card rounded-3xl p-8 sm:p-10 border border-[#EFE6D8] dark:border-[#2B254E] shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-serif text-2xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                  Gratis
                </h3>
                <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5]">Para iniciar tu camino de bienestar</p>
              </div>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-black/5 dark:bg-white/5 text-[#5C544D] dark:text-[#B4ACC5]">
                Para siempre
              </span>
            </div>

            <div className="my-6">
              <span className="text-5xl font-serif font-bold text-[#1E1A17] dark:text-[#F6F3EE]">$0</span>
              <span className="text-xs text-[#5C544D] dark:text-[#B4ACC5] ml-1.5">USD / mes</span>
            </div>

            <ul className="space-y-3.5 text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5] mb-8">
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> Check-in de ánimo diario con recomendaciones
              </li>
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> Afirmación del día y 1 meditación diaria
              </li>
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> Reto básico de 21 días de Gratitud
              </li>
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> Artículos del blog y reflexiones abiertas
              </li>
            </ul>
          </div>

          <Link
            href="/onboarding"
            className="w-full py-4 rounded-2xl border-2 border-[#E0A526] text-[#C68C14] dark:text-[#F2C14E] font-bold text-xs uppercase tracking-wider text-center hover:bg-[#E0A526]/10 transition-colors no-underline block"
          >
            Registrarme Gratis
          </Link>
        </div>

        {/* PREMIUM PLAN */}
        <div className="glass-card rounded-3xl p-8 sm:p-10 border-2 border-[#E0A526] shadow-2xl relative flex flex-col justify-between">
          <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-[#E0A526] via-[#F28C6B] to-[#E0A526] text-white font-extrabold text-[11px] uppercase tracking-wider px-5 py-1.5 rounded-full shadow-lg">
            7 Días de Prueba Gratis
          </div>

          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-serif text-2xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                  Premium Alegría
                </h3>
                <p className="text-xs text-[#E0A526] font-semibold">Acceso total e ilimitado</p>
              </div>
              <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#E0A526]/20 text-[#C68C14] dark:text-[#F2C14E]">
                Más elegido
              </span>
            </div>

            <div className="my-6">
              <span className="text-5xl font-serif font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                {billingCycle === 'monthly' ? '$9.99' : '$79.99'}
              </span>
              <span className="text-xs text-[#5C544D] dark:text-[#B4ACC5] ml-1.5">
                USD / {billingCycle === 'monthly' ? 'mes' : 'año (ahorras 33%)'}
              </span>
            </div>

            <ul className="space-y-3.5 text-xs sm:text-sm text-[#1E1A17] dark:text-[#F6F3EE] mb-8 font-medium">
              <li className="flex items-center gap-2.5 font-bold text-[#E0A526]">
                <Check size={18} className="text-[#E0A526] shrink-0" /> Todo lo incluido en el plan Gratuito
              </li>
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> Biblioteca completa de audios temáticos
              </li>
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> Todos los retos de transformación de 14 y 21 días
              </li>
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> Encuentro grupal mensual en vivo con los coaches
              </li>
              <li className="flex items-center gap-2.5">
                <Check size={18} className="text-[#7E9F84] shrink-0" /> 15% de descuento en sesiones de coaching individual 1:1
              </li>
            </ul>
          </div>

          <button
            onClick={() => handleSubscribe('premium')}
            disabled={loadingTier === 'premium'}
            className="w-full py-4 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white font-bold text-xs uppercase tracking-wider text-center shadow-lg hover:scale-102 active:scale-98 transition-all disabled:opacity-50"
          >
            {loadingTier === 'premium' ? 'Conectando con Stripe...' : 'Comenzar 7 Días Gratis'}
          </button>
        </div>
      </div>

      {/* ── COMPARISON TABLE (Mindvalley style) ── */}
      <div className="max-w-4xl mx-auto mb-20">
        <h3 className="font-serif text-2xl font-bold text-center text-[#1E1A17] dark:text-[#F6F3EE] mb-8">
          Comparativa de Beneficios
        </h3>

        <div className="glass-card rounded-3xl overflow-hidden border border-[#EFE6D8] dark:border-[#2B254E]">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-black/5 dark:bg-white/5 border-b border-[#EFE6D8] dark:border-[#2B254E]">
              <tr>
                <th className="p-4 sm:p-5 font-bold text-[#1E1A17] dark:text-[#F6F3EE]">Beneficio</th>
                <th className="p-4 sm:p-5 text-center font-bold text-[#5C544D] dark:text-[#B4ACC5]">Gratis</th>
                <th className="p-4 sm:p-5 text-center font-bold text-[#E0A526]">Premium</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-black/5 dark:divide-white/5 text-[#5C544D] dark:text-[#B4ACC5]">
              <tr>
                <td className="p-4 sm:p-5">Check-in diario de ánimo con recomendaciones</td>
                <td className="p-4 sm:p-5 text-center">✓</td>
                <td className="p-4 sm:p-5 text-center text-[#7E9F84] font-bold">✓</td>
              </tr>
              <tr>
                <td className="p-4 sm:p-5">Acceso a biblioteca sonora (+100 audios)</td>
                <td className="p-4 sm:p-5 text-center text-gray-400">Limitado (1 audio/día)</td>
                <td className="p-4 sm:p-5 text-center text-[#7E9F84] font-bold">Ilimitado</td>
              </tr>
              <tr>
                <td className="p-4 sm:p-5">Programas estructurados de 21 días</td>
                <td className="p-4 sm:p-5 text-center text-gray-400">Solo Gratitud</td>
                <td className="p-4 sm:p-5 text-center text-[#7E9F84] font-bold">Todos (Ansiedad, Crianza, Duelo)</td>
              </tr>
              <tr>
                <td className="p-4 sm:p-5">Sesión mensual en vivo de preguntas con coaches</td>
                <td className="p-4 sm:p-5 text-center text-gray-400">—</td>
                <td className="p-4 sm:p-5 text-center text-[#7E9F84] font-bold">✓ Incluido</td>
              </tr>
              <tr>
                <td className="p-4 sm:p-5">Descuento en coaching personalizado 1:1</td>
                <td className="p-4 sm:p-5 text-center text-gray-400">—</td>
                <td className="p-4 sm:p-5 text-center text-[#7E9F84] font-bold">15% OFF</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ── FAQ ACCORDION ── */}
      <div className="max-w-2xl mx-auto space-y-4">
        <h3 className="font-serif text-2xl font-bold text-center text-[#1E1A17] dark:text-[#F6F3EE] mb-6">
          Preguntas Frecuentes
        </h3>

        {[
          {
            q: '¿Cómo funciona la prueba gratuita de 7 días?',
            a: 'Puedes registrarte hoy con tu tarjeta en modo seguro vía Stripe. No se te cobrará ningún valor durante los primeros 7 días. Si decides no continuar, puedes cancelar con un solo clic desde tu panel.'
          },
          {
            q: '¿Puedo cancelar mi suscripción en cualquier momento?',
            a: 'Sí, absolutamente. No tenemos contratos forzosos. Puedes cancelar cuando quieras sin penalidad alguna.'
          },
          {
            q: '¿Las sesiones de coaching 1:1 están incluidas?',
            a: 'La membresía incluye descuentos del 15% en las sesiones individuales con Juan Diego, Andrea, Dericielo o Lina. Las sesiones 1:1 se agendan de manera separada según la disponibilidad del mentor.'
          }
        ].map((faq, idx) => (
          <div key={idx} className="glass-card p-5 rounded-2xl border border-[#EFE6D8] dark:border-[#2B254E]">
            <h4 className="font-serif font-bold text-sm text-[#1E1A17] dark:text-[#F6F3EE] mb-2 flex items-center gap-2">
              <HelpCircle size={16} className="text-[#E0A526]" /> {faq.q}
            </h4>
            <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed pl-6">
              {faq.a}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
