'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from '@/context/ThemeContext';
import {
  Sun, Moon, Menu, X, Sparkles
} from 'lucide-react';

const NAV_LINKS = [
  { href: '/', label: 'Inicio' },
  { href: '/conocenos', label: 'Conócenos' },
  { href: '/servicios', label: 'Servicios' },
  { href: '/biblioteca', label: 'Biblioteca' },
  { href: '/blog', label: 'Blog' },
  { href: '/agenda', label: 'Agenda' },
  { href: '/membresia', label: 'Membresía' },
];

export default function SiteHeader() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-[#FFF9F1]/90 dark:bg-[#14122B]/90 backdrop-blur-md border-b border-[#F0E6D8] dark:border-[#2E2A54] transition-colors">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2.5 no-underline group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#E0A526] to-[#F28C6B] flex items-center justify-center text-white shadow-md shadow-[#E0A526]/20 group-hover:scale-105 transition-transform">
            <Sparkles size={18} />
          </div>
          <div>
            <span className="font-serif font-bold text-lg md:text-xl text-[#2B2622] dark:text-[#F4EFE8] tracking-tight block leading-tight">
              AMP
            </span>
            <span className="text-[10px] uppercase font-bold tracking-widest text-[#E0A526] block leading-none">
              El Portal de la Alegría
            </span>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden lg:flex items-center gap-1">
          {NAV_LINKS.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`px-3.5 py-1.5 rounded-full text-sm font-semibold transition-all no-underline ${
                  isActive
                    ? 'bg-[#E0A526]/15 text-[#B8860B] dark:text-[#F2C14E] font-bold'
                    : 'text-[#6B625A] dark:text-[#B9B2C9] hover:text-[#2B2622] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Light / Dark Mode Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl text-[#6B625A] dark:text-[#B9B2C9] hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            aria-label="Cambiar tema claro/oscuro"
          >
            {theme === 'dark' ? <Sun size={18} className="text-[#F2C14E]" /> : <Moon size={18} />}
          </button>

          {/* Onboarding / Portal CTA */}
          <Link
            href="/onboarding"
            className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] hover:opacity-95 text-[#2B2622] font-bold text-xs uppercase tracking-wider shadow-sm transition-all"
          >
            Empieza Gratis
          </Link>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 text-[#6B625A] dark:text-[#B9B2C9]"
            aria-label={mobileMenuOpen ? 'Cerrar menú' : 'Abrir menú'}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-[#FFF9F1] dark:bg-[#14122B] border-b border-[#F0E6D8] dark:border-[#2E2A54] px-4 py-4 space-y-2 animate-fade-up">
          {NAV_LINKS.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-4 py-2.5 rounded-2xl text-base font-semibold no-underline ${
                  isActive
                    ? 'bg-[#E0A526]/15 text-[#B8860B] dark:text-[#F2C14E] font-bold'
                    : 'text-[#6B625A] dark:text-[#B9B2C9]'
                }`}
              >
                {link.label}
              </Link>
            );
          })}
          <div className="pt-2">
            <Link
              href="/onboarding"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-center w-full py-3 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-[#2B2622] font-bold text-sm shadow"
            >
              Comenzar Onboarding Gratis
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
