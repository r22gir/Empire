import { Brain, Heart, Crown } from "lucide-react";

const pillars = [
  {
    icon: Brain,
    title: "Mentalidad",
    description:
      "Entrena tu mente con afirmaciones diarias, visualización guiada y técnicas de programación neurolingüística para desarrollar una actitud mental positiva inquebrantable.",
    color: "from-blue-500/20 to-purple-500/20",
    border: "border-blue-500/30",
  },
  {
    icon: Heart,
    title: "Bienestar",
    description:
      "Reduce el estrés y la ansiedad con meditaciones guiadas, ejercicios de respiración y prácticas de mindfulness diseñadas para hispanohablantes.",
    color: "from-emerald-500/20 to-teal-500/20",
    border: "border-emerald-500/30",
  },
  {
    icon: Crown,
    title: "Liderazgo",
    description:
      "Desarrolla las habilidades de liderazgo que transforman tu carrera y tus relaciones, inspiradas en los principios probados de John Maxwell y los grandes líderes.",
    color: "from-gold/20 to-amber-500/20",
    border: "border-gold/30",
  },
];

export default function Pillars() {
  return (
    <section id="que-es-amp" className="py-20 sm:py-28">
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-16 reveal">
          <span className="text-gold text-sm font-semibold uppercase tracking-widest">
            Nuestros Pilares
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif text-white mt-3 mb-4">
            ¿Qué es <span className="text-gold">AMP</span>?
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            AMP — Actitud Mental Positiva — es tu plataforma integral para
            crecimiento personal, bienestar y liderazgo en español.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {pillars.map((pillar, i) => (
            <div
              key={pillar.title}
              className={`reveal glass-card rounded-2xl p-8 transition-all duration-500 hover:-translate-y-2 hover:shadow-lg hover:shadow-gold/5`}
              style={{ transitionDelay: `${i * 0.15}s` }}
            >
              <div
                className={`w-14 h-14 rounded-xl bg-gradient-to-br ${pillar.color} ${pillar.border} border flex items-center justify-center mb-6`}
              >
                <pillar.icon className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-xl font-bold font-serif text-white mb-3">
                {pillar.title}
              </h3>
              <p className="text-gray-400 leading-relaxed">
                {pillar.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
