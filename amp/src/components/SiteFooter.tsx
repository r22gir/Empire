import Link from 'next/link';
import { Sparkles, Heart, Shield, PhoneCall } from 'lucide-react';

export default function SiteFooter() {
  return (
    <footer className="bg-[#FDF8F0] dark:bg-[#0B0918] border-t border-[#EFE6D8] dark:border-[#2B254E] text-[#5C544D] dark:text-[#B4ACC5] pt-16 pb-28 md:pb-16 mt-auto transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-14">
          {/* Col 1 */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#E0A526] via-[#F28C6B] to-[#7E9F84] flex items-center justify-center text-white shadow-md">
                <Sparkles size={18} />
              </div>
              <div>
                <span className="font-serif font-extrabold text-xl text-[#1E1A17] dark:text-[#F6F3EE] block leading-none">
                  AMP
                </span>
                <span className="text-[10px] uppercase font-bold tracking-widest text-[#E0A526] block leading-none mt-1">
                  El Portal de la Alegría
                </span>
              </div>
            </div>
            <p className="text-xs sm:text-sm leading-relaxed">
              La plataforma de transformación y bienestar guiada por Juan Diego Giraldo y su equipo de mentores en español. Práctica diaria, comunidad y serenidad interior.
            </p>
          </div>

          {/* Col 2 */}
          <div>
            <h4 className="font-serif font-bold text-[#1E1A17] dark:text-[#F6F3EE] text-sm uppercase tracking-wider mb-4">
              Explora
            </h4>
            <ul className="space-y-2.5 text-xs sm:text-sm">
              <li><Link href="/" className="hover:text-[#E0A526] transition-colors no-underline">Inicio</Link></li>
              <li><Link href="/conocenos" className="hover:text-[#E0A526] transition-colors no-underline">Mentores & Filosofía</Link></li>
              <li><Link href="/servicios" className="hover:text-[#E0A526] transition-colors no-underline">Servicios & Coaching</Link></li>
              <li><Link href="/biblioteca" className="hover:text-[#E0A526] transition-colors no-underline">Biblioteca Sonora</Link></li>
              <li><Link href="/blog" className="hover:text-[#E0A526] transition-colors no-underline">Artículos & Blog</Link></li>
            </ul>
          </div>

          {/* Col 3 */}
          <div>
            <h4 className="font-serif font-bold text-[#1E1A17] dark:text-[#F6F3EE] text-sm uppercase tracking-wider mb-4">
              Membresía & Agenda
            </h4>
            <ul className="space-y-2.5 text-xs sm:text-sm">
              <li><Link href="/membresia" className="hover:text-[#E0A526] transition-colors no-underline">Planes y Precios</Link></li>
              <li><Link href="/agenda" className="hover:text-[#E0A526] transition-colors no-underline">Reserva de Sesión 1:1</Link></li>
              <li><Link href="/onboarding" className="hover:text-[#E0A526] transition-colors no-underline">Diagnóstico de 3 Pasos</Link></li>
              <li><Link href="/animo" className="hover:text-[#E0A526] transition-colors no-underline">Check-in de Ánimo Diario</Link></li>
            </ul>
          </div>

          {/* Col 4 Ethical & Crisis Note */}
          <div className="glass-card p-5 rounded-3xl border border-[#7E9F84]/30 space-y-2.5 text-xs">
            <div className="flex items-center gap-1.5 font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
              <Shield size={16} className="text-[#7E9F84]" />
              Aviso de Seguridad Emocional
            </div>
            <p className="leading-relaxed text-[#5C544D] dark:text-[#B4ACC5]">
              Las prácticas y contenidos de AMP potencian el bienestar pero no sustituyen el diagnóstico médico ni la atención clínica especializada.
            </p>
            <p className="font-semibold text-[#5A7A60] dark:text-[#9DBFA2] flex items-center gap-1">
              <PhoneCall size={14} /> Líneas de Ayuda en Crisis:
            </p>
            <p className="text-[11px] text-[#5C544D] dark:text-[#B4ACC5]">
              Colombia: Línea 106 · USA: 988 (Español)
            </p>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="pt-8 border-t border-black/5 dark:border-white/5 flex flex-col sm:flex-row items-center justify-between text-xs text-[#5C544D] dark:text-[#B4ACC5] gap-4">
          <p>© {new Date().getFullYear()} Actitud Mental Positiva (AMP) · Todos los derechos reservados.</p>
          <div className="flex items-center gap-1 text-[11px]">
            <span>Diseñado con</span>
            <Heart size={12} className="text-[#F28C6B] fill-current" />
            <span>para inspirar a toda la comunidad hispana.</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
