import {
  Target,
  Headphones,
  Video,
  MessageCircle,
  Award,
  Building2,
} from "lucide-react";

const features = [
  {
    icon: Target,
    title: "Retos de 21 Días",
    description:
      "Programas estructurados con lecciones diarias de 15-20 minutos para crear hábitos positivos que duran.",
  },
  {
    icon: Headphones,
    title: "Meditaciones Guiadas",
    description:
      "Más de 100 sesiones de meditación, mindfulness y relajación guiadas por expertos certificados.",
  },
  {
    icon: Video,
    title: "Masterclass de Liderazgo",
    description:
      "Clases semanales en video sobre los principios de liderazgo de John Maxwell y desarrollo profesional.",
  },
  {
    icon: MessageCircle,
    title: "Comunidad AMP",
    description:
      "Grupos de WhatsApp exclusivos, sesiones en vivo y una comunidad que te apoya en tu transformación.",
  },
  {
    icon: Award,
    title: "Certificación Coach AMP",
    description:
      "Conviértete en un coach certificado AMP y guía a otros en su camino de desarrollo personal.",
  },
  {
    icon: Building2,
    title: "AMP Empresas",
    description:
      "Soluciones corporativas de bienestar y liderazgo para equipos que quieren crecer juntos.",
  },
];

export default function Features() {
  return (
    <section
      id="funciones"
      className="py-20 sm:py-28 bg-navy-dark/30"
    >
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-16 reveal">
          <span className="text-gold text-sm font-semibold uppercase tracking-widest">
            Todo lo que necesitas
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif text-white mt-3 mb-4">
            Funciones que <span className="text-gold">Transforman</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Herramientas diseñadas para tu crecimiento diario, con contenido
            100% en español por expertos de clase mundial.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <div
              key={feature.title}
              className="reveal glass-card rounded-2xl p-6 group transition-all duration-500 hover:-translate-y-1"
              style={{ transitionDelay: `${i * 0.1}s` }}
            >
              <div className="w-12 h-12 rounded-xl bg-gold/10 border border-gold/20 flex items-center justify-center mb-4 group-hover:bg-gold/20 transition-colors">
                <feature.icon className="w-6 h-6 text-gold" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">
                {feature.title}
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
