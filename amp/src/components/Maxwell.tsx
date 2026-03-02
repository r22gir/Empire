import { BookOpen, ArrowRight } from "lucide-react";

export default function Maxwell() {
  return (
    <section className="py-20 sm:py-28 bg-navy-dark/30 relative overflow-hidden">
      {/* Decorative */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-gold/[0.03] rounded-full blur-3xl" />

      <div className="max-w-5xl mx-auto px-4">
        <div className="reveal glass-card rounded-3xl p-8 sm:p-12 md:p-16 relative">
          <div className="flex flex-col md:flex-row items-center gap-10">
            {/* Icon / Visual */}
            <div className="flex-shrink-0">
              <div className="w-32 h-32 rounded-2xl bg-gradient-to-br from-gold/20 to-amber-600/20 border border-gold/30 flex items-center justify-center">
                <BookOpen className="w-16 h-16 text-gold" />
              </div>
            </div>

            {/* Content */}
            <div className="text-center md:text-left flex-1">
              <span className="text-gold text-sm font-semibold uppercase tracking-widest">
                Inspiración y Filosofía
              </span>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold font-serif text-white mt-3 mb-4">
                Inspirado en los Principios de{" "}
                <span className="text-gold">John Maxwell</span>
              </h2>

              <blockquote className="text-xl sm:text-2xl text-gray-300 italic mb-6 font-serif border-l-4 border-gold/40 pl-6">
                &ldquo;El liderazgo comienza contigo mismo. No puedes liderar a
                otros hasta que primero te lideres a ti.&rdquo;
              </blockquote>

              <p className="text-gray-400 leading-relaxed mb-8">
                AMP fusiona los principios atemporales de liderazgo de John
                Maxwell con el concepto original de &ldquo;Actitud Mental
                Positiva&rdquo; de Napoleon Hill y W. Clement Stone. Nuestro
                contenido está diseñado para ayudarte a desarrollar las 21 leyes
                del liderazgo mientras cultivas una mentalidad de crecimiento
                imparable.
              </p>

              <a
                href="#empieza"
                className="inline-flex items-center gap-2 px-6 py-3 bg-gold text-navy-dark font-bold rounded-xl hover:bg-gold-light transition-colors group"
              >
                Explora el Contenido
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
