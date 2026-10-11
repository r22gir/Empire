'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Sparkles, BookOpen, Calendar, Smile } from 'lucide-react';

const BOTTOM_ITEMS = [
  { href: '/', label: 'Inicio', icon: Home },
  { href: '/biblioteca', label: 'Biblioteca', icon: Sparkles },
  { href: '/animo', label: 'Ánimo', icon: Smile },
  { href: '/agenda', label: 'Agenda', icon: Calendar },
  { href: '/membresia', label: 'Membresía', icon: BookOpen },
];

export default function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 glass-header bg-white/95 dark:bg-[#0E0C1C]/95 backdrop-blur-xl border-t border-[#EFE6D8] dark:border-[#2B254E] h-16 flex items-center justify-around px-2 shadow-[0_-4px_20px_rgba(0,0,0,0.05)]">
      {BOTTOM_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-col items-center justify-center flex-1 py-1 no-underline transition-all duration-200 ${
              isActive
                ? 'text-[#E0A526] font-bold scale-105'
                : 'text-[#5C544D] dark:text-[#B4ACC5] hover:text-[#1E1A17] dark:hover:text-white'
            }`}
          >
            <Icon size={20} className={isActive ? 'stroke-[2.5]' : 'stroke-2'} />
            <span className="text-[10px] mt-1 tracking-tight font-medium">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
