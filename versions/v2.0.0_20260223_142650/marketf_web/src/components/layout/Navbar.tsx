'use client';

import Link from 'next/link';
import { useState } from 'react';
import SearchBar from './SearchBar';

export default function Navbar() {
  const [cartCount] = useState(0);

  return (
    <nav className="bg-white shadow-md">
      <div className="container">
        <div className="flex items-center justify-between py-4">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🛒</span>
            <span className="text-2xl font-bold text-primary">MarketF</span>
          </Link>

          {/* Search Bar */}
          <div className="flex-1 max-w-2xl mx-8">
            <SearchBar />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-4">
            <Link href="/cart" className="relative">
              <span className="text-2xl">🛒</span>
              {cartCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-secondary text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {cartCount}
                </span>
              )}
            </Link>
            <Link href="/orders" className="text-gray-700 hover:text-primary">
              Orders
            </Link>
            <Link href="/seller/dashboard" className="text-gray-700 hover:text-primary">
              Sell
            </Link>
            <Link href="/auth/login" className="btn btn-primary text-sm">
              Login
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
