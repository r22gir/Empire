import Link from 'next/link';
import { Sparkles, Heart, Shield, PhoneCall } from 'lucide-react';

export default function SiteFooter() {
  return (
    <footer className="bg-[#FFF9F1] dark:bg-[#14122B] border-t border-[#F0E6D8] dark:border-[#2E2A54] text-[#6B625A] dark:text-[#B9B2C9] pt-12 pb-24 md:pb-12 mt-auto transition-colors">
      <div className="max-w-6xl mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Col 1 */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#E0A526] to-[#F28C6B] flex items-center justify-center text-white">
                <Sparkles size={16} />
              </div>
              <span className="font-serif font-bold text-lg text-[#2B2622] dark:text-[#F4EFE8]">
                AMP
              </span>
            </div>
            <p className="text-sm leading-relaxed">
              El Portal de la Alegría. Acompañamos tu cambio mental positivo con herramientas prácticas, meditación y coaching en español.
            </p>
          </div>

          {/* Col 2 */}
          <div>
            <h4 className="font-serif font-bold text-[#2B2622] dark:text-[#F4EFE8] text-sm uppercase tracking-wider mb-3">
              Explora
            </h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/" className="hover:text-[#E0A526] transition-colors">Inicio</Link></li>
              <li><Link href="/conocenos" className="hover:text-[#E0A526] transition-colors">Conócenos & Coaches</Link></li>
              <li><Link href="/servicios" className="hover:text-[#E0A526] transition-colors">Servicios & Sesiones</Link></li>
              <li><Link href="/biblioteca" className="hover:text-[#E0A526] transition-colors">Biblioteca de Audio</Link></li>
              <li><Link href="/blog" className="hover:text-[#E0A526] transition-colors">Blog de Bienestar</Link></li>
            </ul>
          </div>

          {/* Col 3 */}
          <div>
            <h4 className="font-serif font-bold text-[#2B2622] dark:text-[#F4EFE8] text-sm uppercase tracking-wider mb-3">
              Membresía & Agenda
            </h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/membresia" className="hover:text-[#E0A526] transition-colors">Planes y Precios</Link></li>
              <li><Link href="/agenda" className="hover:text-[#E0A526] transition-colors">Reserva tu Sesión 1:1</Link></li>
              <li><Link href="/onboarding" className="hover:text-[#E0A526] transition-colors">Quiz de Inicio</Link></li>
              <li><Link href="/animo" className="hover:text-[#E0A526] transition-colors">Check-in de Ánimo</Link></li>
            </ul>
          </div>

          {/* Col 4 Ethical & Crisis Note */}
          <div className="bg-[#E4EDE6]/60 dark:bg-[#1E1B3A] p-4 rounded-2xl border border-[#7E9F84]/20 space-y-2 text-xs">
            <div className="flex items-center gap-1.5 font-bold text-[#2B2622] dark:text-[#F4EFE8]">
              <Shield size={14} className="text-[#7E9F84]" />
              Aviso de Seguridad Emocional
            </div>
            <p className="leading-relaxed">
              Las prácticas y contenidos de AMP no sustituyen el diagnóstico ni la atención médica o psicológica profesional.
            </p>
            <p className="font-semibold text-[#5A7A60] dark:text-[#9DBFA2] flex items-center gap-1">
              <PhoneCall size={12} /> Líneas de ayuda: Marca 106 (Colombia) o 988 (EE.UU.)
            </p>
          </div>
        </div>

        <div className="border-t border-[#F0E6D8] dark:border-[#2E2A54] pt-6 flex flex-col sm:flex-row items-center justify-between text-xs gap-3">
          <p>© {new Date().getFullYear()} Actitud Mental Positiva (AMP). Todos los derechos reservados.</p>
          <p className="flex items-center gap-1">
            Hecho con <Heart size={12} className="text-[#F28C6B] fill-[#F28C6B]" /> para tu paz interior
          </p>
        </div>
      </div>
    </footer>
  );
}
