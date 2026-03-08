'use client';
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X, Sun } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', label: 'Inicio' },
  { href: '/daily', label: 'Diario' },
  { href: '/retos', label: 'Retos' },
  { href: '/animo', label: 'Ánimo' },
  { href: '/perfil', label: 'Perfil' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-warmwhite/90 backdrop-blur-md border-b border-gold-light/50">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 no-underline">
          <Sun size={22} className="text-gold" />
          <span className="font-serif font-bold text-lg text-gold-dark tracking-tight">AMP</span>
        </Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-1">
          {NAV_ITEMS.map(item => (
            <Link key={item.href} href={item.href}
              className={`px-3 py-2 rounded-lg text-sm font-semibold no-underline transition-all
                ${pathname === item.href
                  ? 'bg-gold/10 text-gold-dark'
                  : 'text-[#5C5650] hover:text-gold-dark hover:bg-gold/5'}`}>
              {item.label}
            </Link>
          ))}
        </div>

        <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-[#5C5650] hover:text-gold-dark">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden border-t border-gold-light/30 bg-warmwhite px-4 py-3 space-y-1">
          {NAV_ITEMS.map(item => (
            <Link key={item.href} href={item.href} onClick={() => setOpen(false)}
              className={`block px-4 py-3 rounded-xl text-sm font-semibold no-underline transition-all
                ${pathname === item.href
                  ? 'bg-gold/10 text-gold-dark'
                  : 'text-[#5C5650] hover:bg-gold/5'}`}>
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
