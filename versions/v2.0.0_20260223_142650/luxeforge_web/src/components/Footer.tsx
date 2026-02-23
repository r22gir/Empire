import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="bg-[#2C2C2C] text-gray-400 py-12 px-4">
      <div className="max-w-6xl mx-auto grid md:grid-cols-4 gap-8">
        <div>
          <h3 className="text-[#C9A84C] font-bold text-xl mb-3">LuxeForge</h3>
          <p className="text-sm leading-relaxed">
            AI-powered software for custom workrooms. Quotes, production, and client management — all in one place.
          </p>
        </div>
        <div>
          <h4 className="text-white font-semibold mb-3">Product</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/features" className="hover:text-[#C9A84C] transition">Features</Link></li>
            <li><Link href="/pricing" className="hover:text-[#C9A84C] transition">Pricing</Link></li>
            <li><Link href="/contact" className="hover:text-[#C9A84C] transition">Request Demo</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-white font-semibold mb-3">For Workrooms</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/features#quotes" className="hover:text-[#C9A84C] transition">Auto Quoting</Link></li>
            <li><Link href="/features#production" className="hover:text-[#C9A84C] transition">Production Queue</Link></li>
            <li><Link href="/features#portal" className="hover:text-[#C9A84C] transition">Client Portal</Link></li>
          </ul>
        </div>
        <div>
          <h4 className="text-white font-semibold mb-3">Company</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/contact" className="hover:text-[#C9A84C] transition">Contact</Link></li>
            <li><Link href="/pricing" className="hover:text-[#C9A84C] transition">Pricing</Link></li>
          </ul>
        </div>
      </div>
      <div className="max-w-6xl mx-auto mt-8 pt-8 border-t border-gray-700 text-center text-sm">
        <p>&copy; 2026 LuxeForge. All rights reserved.</p>
      </div>
    </footer>
  )
}
