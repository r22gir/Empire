import { Check, Star } from "lucide-react";

interface Plan {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  popular?: boolean;
  cta: string;
  annual?: string;
}

const plans: Plan[] = [
  {
    name: "Gratis",
    price: "$0",
    period: "para siempre",
    description: "Comienza tu viaje de transformación sin costo.",
    features: [
      "Afirmación diaria",
      "1 meditación por día",
      "Acceso a la comunidad",
      "Contenido de liderazgo semanal",
    ],
    cta: "Empieza Gratis",
  },
  {
    name: "Premium",
    price: "$4.99",
    period: "/mes",
    description: "Acceso completo a todo el contenido AMP.",
    features: [
      "Todo lo de Gratis",
      "Biblioteca completa de meditaciones",
      "Todos los retos de 21 días",
      "Sesiones en vivo semanales",
      "Masterclass de liderazgo",
      "Sin anuncios",
    ],
    popular: true,
    cta: "Elegir Premium",
    annual: "$39.99/año — Ahorra 33%",
  },
  {
    name: "Pro",
    price: "$14.99",
    period: "/mes",
    description: "Para quienes buscan transformación profunda.",
    features: [
      "Todo lo de Premium",
      "Sesiones de coaching 1:1",
      "Certificación Coach AMP",
      "Contenido exclusivo Pro",
      "Grupo VIP de WhatsApp",
      "Prioridad en eventos en vivo",
    ],
    cta: "Elegir Pro",
  },
];

export default function Pricing() {
  return (
    <section id="precios" className="py-20 sm:py-28 bg-navy-dark/30">
      <div className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-16 reveal">
          <span className="text-gold text-sm font-semibold uppercase tracking-widest">
            Inversión en Ti
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif text-white mt-3 mb-4">
            Elige Tu <span className="text-gold">Plan</span>
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Comienza gratis y escala cuando estés listo. Cancela en cualquier
            momento.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 items-start">
          {plans.map((plan, i) => (
            <div
              key={plan.name}
              className={`reveal rounded-2xl p-8 transition-all duration-500 hover:-translate-y-2 ${
                plan.popular
                  ? "pricing-popular bg-navy-light relative"
                  : "glass-card"
              }`}
              style={{ transitionDelay: `${i * 0.15}s` }}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gold text-navy-dark text-sm font-bold rounded-full flex items-center gap-1">
                  <Star className="w-4 h-4" />
                  Más Popular
                </div>
              )}

              <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
              <p className="text-gray-400 text-sm mb-4">{plan.description}</p>

              <div className="mb-6">
                <span className="text-4xl font-bold text-white font-serif">
                  {plan.price}
                </span>
                <span className="text-gray-400 ml-1">{plan.period}</span>
              </div>

              {plan.annual && (
                <div className="mb-6 px-3 py-2 bg-gold/10 border border-gold/20 rounded-lg text-sm text-gold text-center">
                  {plan.annual}
                </div>
              )}

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3 text-sm">
                    <Check className="w-5 h-5 text-gold flex-shrink-0 mt-0.5" />
                    <span className="text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>

              <a
                href="#empieza"
                className={`block text-center py-3 rounded-xl font-semibold transition-all ${
                  plan.popular
                    ? "bg-gold text-navy-dark hover:bg-gold-light"
                    : "border-2 border-gray-600 text-gray-300 hover:border-gold/50 hover:text-white"
                }`}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>

        {/* B2B callout */}
        <div className="reveal mt-12 text-center glass-card rounded-2xl p-8 max-w-2xl mx-auto">
          <h3 className="text-xl font-bold text-white mb-2">
            AMP Empresas
          </h3>
          <p className="text-gray-400 mb-4">
            Soluciones de bienestar y liderazgo para tu equipo. Precios
            personalizados según el tamaño de tu organización.
          </p>
          <a
            href="#empieza"
            className="inline-block px-6 py-3 border-2 border-gold/40 text-gold font-semibold rounded-xl hover:bg-gold/10 transition-colors"
          >
            Contactar Ventas
          </a>
        </div>
      </div>
    </section>
  );
}
