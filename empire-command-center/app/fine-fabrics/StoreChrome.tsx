'use client';

import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { cartCount } from './cartStore';

const NAV = [
  { href: '/fine-fabrics', label: 'All' },
  { href: '/fine-fabrics?cat=Upholstery', label: 'Upholstery' },
  { href: '/fine-fabrics?cat=Drapery', label: 'Drapery' },
  { href: '/fine-fabrics?cat=Outdoor', label: 'Outdoor' },
  { href: '/fine-fabrics?cat=Other', label: 'Other' },
  { href: '/fine-fabrics/samples', label: 'Samples' },
];

function SearchBox() {
  const router = useRouter();
  const params = useSearchParams();
  const [q, setQ] = useState(params.get('q') || '');

  useEffect(() => {
    setQ(params.get('q') || '');
  }, [params]);

  return (
    <form
      className="ff-search"
      role="search"
      onSubmit={(event) => {
        event.preventDefault();
        const next = q.trim();
        router.push(next ? `/fine-fabrics?q=${encodeURIComponent(next)}` : '/fine-fabrics');
      }}
    >
      <label className="ff-sr" htmlFor="ff-search">Search brand, pattern, or vendor SKU</label>
      <input
        id="ff-search"
        name="q"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="SKU, pattern, brand"
        autoComplete="off"
      />
      <button type="submit">Search</button>
    </form>
  );
}

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
        <Suspense fallback={null}>
          <SearchBox />
        </Suspense>
      </header>
      {children}
      <footer className="ff-foot">
        <span>Hyattsville, Maryland</span>
        <span>Sister to Empire Workroom · Test-mode checkout</span>
      </footer>
    </div>
  );
}
