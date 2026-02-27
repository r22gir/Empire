"use client";

import { useState, FormEvent } from "react";
import { Mail, ArrowRight, Sparkles } from "lucide-react";

export default function EmailCapture() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubmitted(true);
      setEmail("");
    }
  };

  return (
    <section id="empieza" className="py-20 sm:py-28">
      <div className="max-w-4xl mx-auto px-4">
        <div className="reveal relative rounded-3xl overflow-hidden">
          {/* Background gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-navy via-navy-light to-navy" />
          <div className="absolute inset-0 bg-gradient-to-r from-gold/5 via-transparent to-gold/5" />
          <div className="absolute top-0 left-1/4 w-64 h-64 bg-gold/[0.04] rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-48 h-48 bg-gold/[0.06] rounded-full blur-3xl" />

          <div className="relative z-10 p-8 sm:p-12 md:p-16 text-center border border-gold/20 rounded-3xl">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-gold/30 bg-gold/5 mb-6">
              <Sparkles className="w-4 h-4 text-gold" />
              <span className="text-gold text-sm font-medium">
                Reto Gratuito de 7 Días
              </span>
            </div>

            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif text-white mb-4">
              Recibe Tu Dosis Diaria de{" "}
              <span className="text-gold">AMP</span>
            </h2>

            <p className="text-gray-400 text-lg max-w-xl mx-auto mb-8">
              Suscríbete y recibe una afirmación diaria, acceso al reto de 7
              días y contenido exclusivo directamente en tu correo.
            </p>

            {submitted ? (
              <div className="py-6 px-8 bg-gold/10 border border-gold/30 rounded-2xl max-w-md mx-auto">
                <Sparkles className="w-8 h-8 text-gold mx-auto mb-3" />
                <p className="text-white font-semibold text-lg">
                  ¡Bienvenido a AMP!
                </p>
                <p className="text-gray-400 text-sm mt-1">
                  Revisa tu correo para comenzar el reto de 7 días.
                </p>
              </div>
            ) : (
              <form
                onSubmit={handleSubmit}
                className="flex flex-col sm:flex-row gap-4 max-w-lg mx-auto"
              >
                <div className="flex-1 relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type="email"
                    placeholder="tu@correo.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full pl-12 pr-4 py-4 bg-navy-dark/80 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-gold/50 focus:ring-1 focus:ring-gold/30 transition-all"
                  />
                </div>
                <button
                  type="submit"
                  className="px-8 py-4 bg-gold text-navy-dark font-bold rounded-xl hover:bg-gold-light transition-all hover:scale-105 flex items-center justify-center gap-2 group"
                >
                  Suscribirme
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>
              </form>
            )}

            <p className="text-gray-500 text-xs mt-6">
              Sin spam. Cancela cuando quieras. Respetamos tu privacidad.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
