import { Quote } from "lucide-react";

const testimonials = [
  {
    name: "María García",
    role: "Emprendedora, Ciudad de México",
    quote:
      "AMP cambió completamente mi perspectiva. Las meditaciones diarias y los retos de 21 días me dieron la disciplina que necesitaba para lanzar mi negocio. Hoy facturo 3x más y duermo mejor.",
    avatar: "MG",
  },
  {
    name: "Carlos Rodríguez",
    role: "Gerente de Operaciones, Bogotá",
    quote:
      "Como líder de un equipo de 50 personas, las masterclass de liderazgo han transformado mi estilo de gestión. Mi equipo está más motivado y nuestros resultados hablan por sí mismos.",
    avatar: "CR",
  },
  {
    name: "Ana Martínez",
    role: "Profesora, Buenos Aires",
    quote:
      "Sufría de ansiedad severa. Después de 3 meses con AMP, aprendí técnicas que me devolvieron la paz. La comunidad es increíble — no te sientes solo en el camino.",
    avatar: "AM",
  },
];

export default function Testimonials() {
  return (
    <section id="testimonios" className="py-20 sm:py-28">
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-16 reveal">
          <span className="text-gold text-sm font-semibold uppercase tracking-widest">
            Historias Reales
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif text-white mt-3 mb-4">
            Vidas <span className="text-gold">Transformadas</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Miles de personas ya están viviendo con una actitud mental positiva.
            Estas son sus historias.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {testimonials.map((t, i) => (
            <div
              key={t.name}
              className="reveal glass-card rounded-2xl p-8 flex flex-col"
              style={{ transitionDelay: `${i * 0.15}s` }}
            >
              <Quote className="w-8 h-8 text-gold/40 mb-4" />
              <p className="text-gray-300 leading-relaxed flex-1 mb-6 italic">
                &ldquo;{t.quote}&rdquo;
              </p>
              <div className="flex items-center gap-3 pt-4 border-t border-gray-700/50">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center text-navy-dark font-bold text-sm">
                  {t.avatar}
                </div>
                <div>
                  <p className="text-white font-semibold text-sm">{t.name}</p>
                  <p className="text-gray-400 text-xs">{t.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
