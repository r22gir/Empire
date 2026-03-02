'use client'
import Link from 'next/link'
import { useState } from 'react'
import { Menu, X } from 'lucide-react'

export default function Navbar() {
  const [open, setOpen] = useState(false)

  return (
    <nav className="bg-[#2C2C2C] text-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="text-2xl font-bold text-[#C9A84C] tracking-tight">
          LuxeForge
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8 text-sm font-medium">
          <Link href="/features" className="hover:text-[#C9A84C] transition">Features</Link>
          <Link href="/pricing" className="hover:text-[#C9A84C] transition">Pricing</Link>
          <Link href="/contact" className="hover:text-[#C9A84C] transition">Contact</Link>
          <Link
            href="/contact"
            className="bg-[#C9A84C] hover:bg-[#A07A2E] text-[#2C2C2C] font-semibold px-5 py-2 rounded-lg transition"
          >
            Request Demo
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu">
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-[#1A1A1A] px-4 pb-4 flex flex-col gap-4 text-sm font-medium">
          <Link href="/features" onClick={() => setOpen(false)} className="hover:text-[#C9A84C] transition py-2">Features</Link>
          <Link href="/pricing" onClick={() => setOpen(false)} className="hover:text-[#C9A84C] transition py-2">Pricing</Link>
          <Link href="/contact" onClick={() => setOpen(false)} className="hover:text-[#C9A84C] transition py-2">Contact</Link>
          <Link
            href="/contact"
            onClick={() => setOpen(false)}
            className="bg-[#C9A84C] text-[#2C2C2C] font-semibold px-5 py-2 rounded-lg text-center transition"
          >
            Request Demo
          </Link>
        </div>
      )}
    </nav>
  )
}
