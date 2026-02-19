'use client';

import { useState } from 'react';
import Link from 'next/link';
import { PRODUCTS, SERVICES } from '@/lib/constants';

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [productsOpen, setProductsOpen] = useState(false);
  const [servicesOpen, setServicesOpen] = useState(false);

  return (
    <nav className="sticky top-0 bg-white shadow-md z-50">
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <Link href="/" className="text-2xl font-bold text-gray-900">
            ⬛ EmpireBox
          </Link>

          {/* Desktop Menu */}
          <ul className="hidden md:flex space-x-8 items-center">
            <li>
              <Link href="/" className="text-gray-700 font-medium hover:text-primary-700 transition-colors">
                Home
              </Link>
            </li>

            {/* Products Dropdown */}
            <li className="relative">
              <button
                className="flex items-center gap-1 text-gray-700 font-medium hover:text-primary-700 transition-colors"
                onMouseEnter={() => { setProductsOpen(true); setServicesOpen(false); }}
                onMouseLeave={() => setProductsOpen(false)}
                onClick={() => { setProductsOpen(!productsOpen); setServicesOpen(false); }}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setProductsOpen(!productsOpen); setServicesOpen(false); } }}
                aria-expanded={productsOpen}
                aria-haspopup="true"
              >
                Products
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {productsOpen && (
                <div
                  className="absolute left-0 top-full mt-1 w-56 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50"
                  onMouseEnter={() => setProductsOpen(true)}
                  onMouseLeave={() => setProductsOpen(false)}
                >
                  <Link href="/products" className="block px-4 py-2 text-sm font-semibold text-gray-900 hover:bg-gray-50">
                    All Products
                  </Link>
                  <div className="border-t border-gray-100 my-1" />
                  {PRODUCTS.map((p) => (
                    <Link
                      key={p.id}
                      href={p.href}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-700"
                      onClick={() => setProductsOpen(false)}
                    >
                      <span>{p.icon}</span>
                      <span>{p.name}</span>
                    </Link>
                  ))}
                </div>
              )}
            </li>

            {/* Services Dropdown */}
            <li className="relative">
              <button
                className="flex items-center gap-1 text-gray-700 font-medium hover:text-primary-700 transition-colors"
                onMouseEnter={() => { setServicesOpen(true); setProductsOpen(false); }}
                onMouseLeave={() => setServicesOpen(false)}
                onClick={() => { setServicesOpen(!servicesOpen); setProductsOpen(false); }}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setServicesOpen(!servicesOpen); setProductsOpen(false); } }}
                aria-expanded={servicesOpen}
                aria-haspopup="true"
              >
                Services
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {servicesOpen && (
                <div
                  className="absolute left-0 top-full mt-1 w-56 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50"
                  onMouseEnter={() => setServicesOpen(true)}
                  onMouseLeave={() => setServicesOpen(false)}
                >
                  <Link href="/services" className="block px-4 py-2 text-sm font-semibold text-gray-900 hover:bg-gray-50">
                    All Services
                  </Link>
                  <div className="border-t border-gray-100 my-1" />
                  {SERVICES.map((s) => (
                    <Link
                      key={s.id}
                      href={s.href}
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-700"
                      onClick={() => setServicesOpen(false)}
                    >
                      <span>{s.icon}</span>
                      <span>{s.name}</span>
                    </Link>
                  ))}
                </div>
              )}
            </li>

            <li>
              <Link href="/pricing" className="text-gray-700 font-medium hover:text-primary-700 transition-colors">
                Pricing
              </Link>
            </li>
            <li>
              <Link href="/faq" className="text-gray-700 font-medium hover:text-primary-700 transition-colors">
                FAQ
              </Link>
            </li>
            <li>
              <Link href="/contact" className="text-gray-700 font-medium hover:text-primary-700 transition-colors">
                Contact
              </Link>
            </li>
          </ul>

          {/* Mobile Menu Toggle */}
          <button
            className="md:hidden text-3xl"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle mobile menu"
          >
            {mobileMenuOpen ? '✕' : '☰'}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden mt-4 pb-4 space-y-2">
            <Link
              href="/"
              className="block py-2 text-gray-700 font-medium hover:text-primary-700"
              onClick={() => setMobileMenuOpen(false)}
            >
              Home
            </Link>

            {/* Mobile Products */}
            <div>
              <button
                className="flex items-center gap-1 py-2 text-gray-700 font-medium hover:text-primary-700 w-full text-left"
                onClick={() => { setProductsOpen(!productsOpen); setServicesOpen(false); }}
              >
                Products
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={productsOpen ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
                </svg>
              </button>
              {productsOpen && (
                <div className="pl-4 space-y-1">
                  <Link href="/products" className="block py-1.5 text-sm text-gray-600 hover:text-primary-700" onClick={() => setMobileMenuOpen(false)}>
                    All Products
                  </Link>
                  {PRODUCTS.map((p) => (
                    <Link
                      key={p.id}
                      href={p.href}
                      className="flex items-center gap-2 py-1.5 text-sm text-gray-600 hover:text-primary-700"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <span>{p.icon}</span>
                      <span>{p.name}</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Mobile Services */}
            <div>
              <button
                className="flex items-center gap-1 py-2 text-gray-700 font-medium hover:text-primary-700 w-full text-left"
                onClick={() => { setServicesOpen(!servicesOpen); setProductsOpen(false); }}
              >
                Services
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={servicesOpen ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'} />
                </svg>
              </button>
              {servicesOpen && (
                <div className="pl-4 space-y-1">
                  <Link href="/services" className="block py-1.5 text-sm text-gray-600 hover:text-primary-700" onClick={() => setMobileMenuOpen(false)}>
                    All Services
                  </Link>
                  {SERVICES.map((s) => (
                    <Link
                      key={s.id}
                      href={s.href}
                      className="flex items-center gap-2 py-1.5 text-sm text-gray-600 hover:text-primary-700"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      <span>{s.icon}</span>
                      <span>{s.name}</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            <Link
              href="/pricing"
              className="block py-2 text-gray-700 font-medium hover:text-primary-700"
              onClick={() => setMobileMenuOpen(false)}
            >
              Pricing
            </Link>
            <Link
              href="/faq"
              className="block py-2 text-gray-700 font-medium hover:text-primary-700"
              onClick={() => setMobileMenuOpen(false)}
            >
              FAQ
            </Link>
            <Link
              href="/contact"
              className="block py-2 text-gray-700 font-medium hover:text-primary-700"
              onClick={() => setMobileMenuOpen(false)}
            >
              Contact
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
