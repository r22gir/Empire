import { Sun, Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-[#2D2A26] text-white/70 mt-auto">
      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Sun size={20} className="text-gold" />
              <span className="font-serif font-bold text-lg text-gold">AMP</span>
            </div>
            <p className="text-sm leading-relaxed text-white/50">
              El Portal de la Alegría. Una plataforma para ayudarte a generar un cambio mental positivo,
              manifestar bienestar y compartir herramientas de sanación.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-white/90 text-sm mb-3">Explora</h4>
            <div className="space-y-2 text-sm">
              <a href="/daily" className="block hover:text-gold transition-colors">Experiencia Diaria</a>
              <a href="/retos" className="block hover:text-gold transition-colors">Retos AMP</a>
              <a href="/animo" className="block hover:text-gold transition-colors">Seguimiento de Ánimo</a>
              <a href="/perfil" className="block hover:text-gold transition-colors">Mi Perfil</a>
            </div>
          </div>
          <div>
            <h4 className="font-bold text-white/90 text-sm mb-3">Los 3 Pilares</h4>
            <div className="space-y-2 text-sm">
              <p>🧠 Mentalidad — Transforma tu mente</p>
              <p>🌿 Bienestar — Cuida tu ser</p>
              <p>⭐ Liderazgo — Lidera tu vida</p>
            </div>
          </div>
        </div>
        <div className="border-t border-white/10 mt-8 pt-6 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs text-white/40">
            &copy; {new Date().getFullYear()} Actitud Mental Positiva. Todos los derechos reservados.
          </p>
          <p className="text-xs text-white/40 flex items-center gap-1">
            Hecho con <Heart size={12} className="text-sunrise" /> desde el corazón
          </p>
        </div>
      </div>
    </footer>
  );
}
