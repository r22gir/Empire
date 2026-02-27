"use client";

import { useState, useEffect } from "react";
import { Menu, X, Zap } from "lucide-react";

const navLinks = [
  { href: "#que-es-amp", label: "¿Qué es AMP?" },
  { href: "#funciones", label: "Funciones" },
  { href: "#como-funciona", label: "Cómo Funciona" },
  { href: "#precios", label: "Precios" },
  { href: "#testimonios", label: "Testimonios" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? "bg-navy-deeper/95 backdrop-blur-md border-b border-gold/10 py-3"
          : "bg-transparent py-5"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2 group">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center">
            <Zap className="w-5 h-5 text-navy-dark" />
          </div>
          <span className="text-xl font-bold font-serif text-white tracking-wide">
            AMP
          </span>
        </a>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-gray-300 hover:text-gold transition-colors"
            >
              {link.label}
            </a>
          ))}
          <a
            href="#empieza"
            className="px-5 py-2 bg-gold text-navy-dark font-semibold rounded-lg text-sm hover:bg-gold-light transition-colors"
          >
            Empieza Gratis
          </a>
        </div>

        {/* Mobile toggle */}
        <button
          className="md:hidden text-gray-300 hover:text-gold"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-navy-dark/95 backdrop-blur-md border-t border-gold/10 px-4 py-4 space-y-3">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="block text-gray-300 hover:text-gold transition-colors py-2"
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </a>
          ))}
          <a
            href="#empieza"
            className="block text-center px-5 py-2 bg-gold text-navy-dark font-semibold rounded-lg hover:bg-gold-light transition-colors"
            onClick={() => setMobileOpen(false)}
          >
            Empieza Gratis
          </a>
        </div>
      )}
    </nav>
  );
}
