import { Zap, Instagram, Youtube, Facebook } from "lucide-react";

const footerLinks = {
  Plataforma: [
    { label: "Funciones", href: "#funciones" },
    { label: "Precios", href: "#precios" },
    { label: "Testimonios", href: "#testimonios" },
    { label: "AMP Empresas", href: "#empieza" },
  ],
  Recursos: [
    { label: "Blog", href: "#" },
    { label: "Podcast", href: "#" },
    { label: "Guía de Liderazgo", href: "#" },
    { label: "FAQ", href: "#" },
  ],
  Legal: [
    { label: "Términos de Uso", href: "#" },
    { label: "Política de Privacidad", href: "#" },
    { label: "Contacto", href: "#" },
  ],
};

const socials = [
  { icon: Instagram, href: "#", label: "Instagram" },
  { icon: Youtube, href: "#", label: "YouTube" },
  { icon: Facebook, href: "#", label: "Facebook" },
];

export default function Footer() {
  return (
    <footer className="bg-navy-deeper border-t border-gold/10 pt-16 pb-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1">
            <a href="#" className="flex items-center gap-2 mb-4">
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center">
                <Zap className="w-5 h-5 text-navy-dark" />
              </div>
              <span className="text-xl font-bold font-serif text-white">
                AMP
              </span>
            </a>
            <p className="text-gray-400 text-sm leading-relaxed mb-4">
              Actitud Mental Positiva — La plataforma #1 en español para
              desarrollo personal, liderazgo y bienestar mental.
            </p>
            <div className="flex gap-3">
              {socials.map((social) => (
                <a
                  key={social.label}
                  href={social.href}
                  aria-label={social.label}
                  className="w-9 h-9 rounded-lg bg-navy-light border border-gray-700 flex items-center justify-center text-gray-400 hover:text-gold hover:border-gold/30 transition-colors"
                >
                  <social.icon className="w-4 h-4" />
                </a>
              ))}
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([heading, links]) => (
            <div key={heading}>
              <h4 className="text-white font-semibold text-sm mb-4">
                {heading}
              </h4>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-gray-400 text-sm hover:text-gold transition-colors"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom */}
        <div className="border-t border-gray-800 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-gray-500 text-sm">
            &copy; 2026 AMP — Actitud Mental Positiva. Todos los derechos
            reservados.
          </p>
          <p className="text-gray-600 text-xs">
            Inspirado en Napoleon Hill, W. Clement Stone y John Maxwell
          </p>
        </div>
      </div>
    </footer>
  );
}
