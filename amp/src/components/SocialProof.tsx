import { Users, Globe, Star, BookOpen } from "lucide-react";

const stats = [
  { icon: Users, value: "10,000+", label: "Personas Transformando Su Vida" },
  { icon: Globe, value: "25+", label: "Países" },
  { icon: Star, value: "4.9", label: "Calificación Promedio" },
  { icon: BookOpen, value: "100+", label: "Sesiones Disponibles" },
];

export default function SocialProof() {
  return (
    <section className="relative py-12 bg-navy-dark/50 border-y border-gold/10">
      <div className="max-w-6xl mx-auto px-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="reveal flex flex-col items-center text-center"
            >
              <stat.icon className="w-8 h-8 text-gold mb-3" />
              <span className="text-2xl sm:text-3xl font-bold text-white font-serif">
                {stat.value}
              </span>
              <span className="text-sm text-gray-400 mt-1">{stat.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
