'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from '@/context/ThemeContext';
import {
  Sun, Moon, Menu, X, Sparkles, ArrowRight
} from 'lucide-react';

const NAV_LINKS = [
  { href: '/', label: 'Inicio' },
  { href: '/conocenos', label: 'Mentores' },
  { href: '/servicios', label: 'Servicios' },
  { href: '/biblioteca', label: 'Biblioteca' },
  { href: '/animo', label: 'Ánimo Diario' },
  { href: '/blog', label: 'Blog' },
  { href: '/agenda', label: 'Agenda' },
  { href: '/membresia', label: 'Membresía' },
];

export default function SiteHeader() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 glass-header transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-3 no-underline group focus:outline-none focus:ring-2 focus:ring-[#E0A526] rounded-xl p-1">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-[#E0A526] via-[#F28C6B] to-[#7E9F84] flex items-center justify-center text-white shadow-lg shadow-[#E0A526]/25 group-hover:scale-105 group-hover:rotate-3 transition-all duration-300">
            <Sparkles size={20} className="animate-pulse-slow" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-serif font-extrabold text-xl md:text-2xl text-[#1E1A17] dark:text-[#F6F3EE] tracking-tight block leading-tight">
                AMP
              </span>
              <span className="inline-block px-1.5 py-0.5 text-[9px] font-bold tracking-widest uppercase rounded bg-[#E0A526]/20 text-[#C68C14] dark:text-[#F2C14E]">
                Edición Oficial
              </span>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-widest text-[#E0A526] block leading-none mt-0.5">
              El Portal de la Alegría
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden lg:flex items-center gap-1 bg-black/[0.03] dark:bg-white/[0.04] p-1.5 rounded-full border border-black/5 dark:border-white/5">
          {NAV_LINKS.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wide transition-all duration-200 no-underline ${
                  isActive
                    ? 'bg-white dark:bg-[#1E1B3A] text-[#1E1A17] dark:text-[#F6F3EE] shadow-sm font-bold scale-[1.02]'
                    : 'text-[#5C544D] dark:text-[#B4ACC5] hover:text-[#1E1A17] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          {/* Theme switcher */}
          <button
            onClick={toggleTheme}
            aria-label={`Cambiar a modo ${theme === 'dark' ? 'claro' : 'oscuro'}`}
            className="w-10 h-10 rounded-full flex items-center justify-center text-[#5C544D] dark:text-[#B4ACC5] hover:text-[#1E1A17] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-[#E0A526]"
          >
            {theme === 'dark' ? <Sun size={19} className="text-[#F2C14E]" /> : <Moon size={19} />}
          </button>

          {/* Primary CTA */}
          <Link
            href="/onboarding"
            className="hidden sm:inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white text-xs font-bold uppercase tracking-wider shadow-md hover:shadow-xl hover:scale-105 active:scale-95 transition-all duration-200 no-underline"
          >
            Empieza Gratis <ArrowRight size={14} />
          </Link>

          {/* Mobile hamburger button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Abrir menú"
            className="lg:hidden p-2.5 rounded-xl text-[#1E1A17] dark:text-[#F6F3EE] hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden glass-card border-t border-[#EFE6D8] dark:border-[#2B254E] px-5 py-6 space-y-2 animate-fade-up">
          {NAV_LINKS.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-xl text-sm font-semibold transition-colors no-underline ${
                  isActive
                    ? 'bg-[#E0A526]/15 text-[#C68C14] dark:text-[#F2C14E] font-bold'
                    : 'text-[#5C544D] dark:text-[#B4ACC5] hover:bg-black/5 dark:hover:bg-white/5'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <div className="pt-4 border-t border-black/5 dark:border-white/5">
            <Link
              href="/onboarding"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white text-sm font-bold uppercase tracking-wider shadow-md no-underline"
            >
              Comienza tu Camino Gratis <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
