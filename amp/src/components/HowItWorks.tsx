import { Download, Target, Timer, Users, Sparkles } from "lucide-react";

const steps = [
  {
    icon: Download,
    number: "01",
    title: "Descarga o Accede",
    description: "Regístrate gratis desde la app o la web en menos de 1 minuto.",
  },
  {
    icon: Target,
    number: "02",
    title: "Elige Tu Reto",
    description:
      "Selecciona un reto de 21 días según tus objetivos: mentalidad, bienestar o liderazgo.",
  },
  {
    icon: Timer,
    number: "03",
    title: "Practica 15 Min/Día",
    description:
      "Dedica solo 15 minutos al día con lecciones cortas, meditaciones y ejercicios prácticos.",
  },
  {
    icon: Users,
    number: "04",
    title: "Conecta con la Comunidad",
    description:
      "Únete a grupos de WhatsApp, sesiones en vivo y comparte tu progreso con otros.",
  },
  {
    icon: Sparkles,
    number: "05",
    title: "Transforma Tu Vida",
    description:
      "Observa los resultados: más claridad, menos estrés, mayor liderazgo y una actitud imparable.",
  },
];

export default function HowItWorks() {
  return (
    <section id="como-funciona" className="py-20 sm:py-28">
      <div className="max-w-5xl mx-auto px-4">
        <div className="text-center mb-16 reveal">
          <span className="text-gold text-sm font-semibold uppercase tracking-widest">
            Simple y Efectivo
          </span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold font-serif text-white mt-3 mb-4">
            ¿Cómo <span className="text-gold">Funciona</span>?
          </h2>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Cinco pasos para comenzar tu transformación personal hoy mismo.
          </p>
        </div>

        <div className="relative">
          {/* Vertical line */}
          <div className="hidden md:block absolute left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-gold/0 via-gold/30 to-gold/0" />

          <div className="space-y-12">
            {steps.map((step, i) => (
              <div
                key={step.number}
                className={`reveal flex flex-col md:flex-row items-center gap-6 md:gap-12 ${
                  i % 2 === 1 ? "md:flex-row-reverse" : ""
                }`}
                style={{ transitionDelay: `${i * 0.1}s` }}
              >
                {/* Content */}
                <div
                  className={`flex-1 ${
                    i % 2 === 1 ? "md:text-left" : "md:text-right"
                  } text-center`}
                >
                  <h3 className="text-xl font-bold text-white mb-2">
                    {step.title}
                  </h3>
                  <p className="text-gray-400">{step.description}</p>
                </div>

                {/* Center icon */}
                <div className="relative flex-shrink-0">
                  <div className="w-16 h-16 rounded-full bg-navy border-2 border-gold/40 flex items-center justify-center z-10 relative">
                    <step.icon className="w-7 h-7 text-gold" />
                  </div>
                  <span className="absolute -top-2 -right-2 text-xs font-bold text-gold bg-navy-dark px-2 py-0.5 rounded-full border border-gold/30">
                    {step.number}
                  </span>
                </div>

                {/* Spacer */}
                <div className="flex-1 hidden md:block" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
