'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, Sparkles, BookOpen, Calendar, UserCheck } from 'lucide-react';

const BOTTOM_ITEMS = [
  { href: '/', label: 'Inicio', icon: Home },
  { href: '/biblioteca', label: 'Biblioteca', icon: Sparkles },
  { href: '/animo', label: 'Ánimo', icon: UserCheck },
  { href: '/agenda', label: 'Agenda', icon: Calendar },
  { href: '/membresia', label: 'Membresía', icon: BookOpen },
];

export default function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-[#FFF9F1]/95 dark:bg-[#14122B]/95 backdrop-blur-md border-t border-[#F0E6D8] dark:border-[#2E2A54] h-16 flex items-center justify-around px-2">
      {BOTTOM_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-col items-center justify-center flex-1 py-1 no-underline transition-colors ${
              isActive
                ? 'text-[#E0A526] font-bold'
                : 'text-[#6B625A] dark:text-[#B9B2C9] hover:text-[#2B2622] dark:hover:text-white'
            }`}
          >
            <Icon size={20} className={isActive ? 'stroke-[2.5]' : 'stroke-2'} />
            <span className="text-[10px] mt-1 tracking-tight">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
