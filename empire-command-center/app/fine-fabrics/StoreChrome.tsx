'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import { cartCount } from './cartStore';

const NAV = [
  { href: '/fine-fabrics', label: 'All' },
  { href: '/fine-fabrics?cat=Upholstery', label: 'Upholstery' },
  { href: '/fine-fabrics?cat=Drapery', label: 'Drapery' },
  { href: '/fine-fabrics?cat=Outdoor', label: 'Outdoor' },
  { href: '/fine-fabrics?cat=Other', label: 'Other' },
  { href: '/fine-fabrics/samples', label: 'Samples' },
];

export default function StoreChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [count, setCount] = useState(0);

  useEffect(() => {
    const sync = () => setCount(cartCount());
    sync();
    window.addEventListener('ff-cart', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('ff-cart', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  return (
    <div className="ff">
      <a className="ff-skip" href="#cloth">Skip to cloth</a>
      <header className="ff-top">
        <Link className="ff-word" href="/fine-fabrics">Empire Fine Fabrics</Link>
        <nav className="ff-nav" aria-label="Store">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              aria-current={pathname === item.href ? 'page' : undefined}
            >
              {item.label}
            </Link>
          ))}
          <Link href="/fine-fabrics/cart">Cart{count ? ` (${count})` : ''}</Link>
        </nav>
      </header>
      {children}
      <footer className="ff-foot">
        <span>Hyattsville, Maryland</span>
        <span>Sister to Empire Workroom · Test-mode checkout</span>
      </footer>
    </div>
  );
}
