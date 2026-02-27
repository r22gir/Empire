import { ArrowRight, Play } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center gradient-bg overflow-hidden">
      {/* Decorative orbs */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-gold/5 rounded-full blur-3xl" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-gold/3 rounded-full blur-3xl" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gold/[0.02] rounded-full blur-3xl" />

      <div className="relative z-10 max-w-5xl mx-auto px-4 text-center pt-24 pb-16">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-gold/30 bg-gold/5 mb-8 animate-fade-in">
          <span className="w-2 h-2 bg-gold rounded-full animate-pulse" />
          <span className="text-gold text-sm font-medium">
            Plataforma #1 en Español para Desarrollo Personal
          </span>
        </div>

        {/* Headline */}
        <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold font-serif text-white leading-tight mb-6 animate-fade-in-up">
          Transforma Tu Mente.
          <br />
          <span className="gold-shimmer">Transforma Tu Vida.</span>
        </h1>

        {/* Subtitle */}
        <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
          Desarrollo personal, liderazgo y bienestar mental —
          meditaciones guiadas, retos de 21 días, y masterclass inspiradas en
          los principios de John Maxwell.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-in-up" style={{ animationDelay: "0.4s" }}>
          <a
            href="#empieza"
            className="group px-8 py-4 bg-gold text-navy-dark font-bold rounded-xl text-lg hover:bg-gold-light transition-all hover:scale-105 animate-pulse-gold flex items-center gap-2"
          >
            Empieza Gratis
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </a>
          <a
            href="#que-es-amp"
            className="px-8 py-4 border-2 border-gray-600 text-gray-300 font-semibold rounded-xl text-lg hover:border-gold/50 hover:text-white transition-all flex items-center gap-2"
          >
            <Play className="w-5 h-5" />
            Ver Demo
          </a>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 rounded-full border-2 border-gray-600 flex items-start justify-center p-2">
            <div className="w-1.5 h-3 bg-gold rounded-full" />
          </div>
        </div>
      </div>
    </section>
  );
}
