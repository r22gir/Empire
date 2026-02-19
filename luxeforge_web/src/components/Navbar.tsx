import Link from 'next/link';

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-100 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center space-x-2">
            <span className="text-2xl font-bold text-charcoal">
              Luxe<span style={{ color: '#C9A84C' }}>Forge</span>
            </span>
          </Link>
          <div className="hidden md:flex items-center space-x-8">
            <Link href="/features" className="text-gray-600 hover:text-charcoal font-medium transition-colors">
              Features
            </Link>
            <Link href="/pricing" className="text-gray-600 hover:text-charcoal font-medium transition-colors">
              Pricing
            </Link>
            <Link href="/contact" className="text-gray-600 hover:text-charcoal font-medium transition-colors">
              Contact
            </Link>
            <Link
              href="/contact"
              className="px-5 py-2 rounded-md font-semibold text-white transition-all hover:opacity-90"
              style={{ backgroundColor: '#C9A84C' }}
            >
              Get Demo
            </Link>
          </div>
          {/* Mobile menu button placeholder */}
          <div className="md:hidden">
            <Link
              href="/contact"
              className="px-4 py-2 rounded-md text-sm font-semibold text-white"
              style={{ backgroundColor: '#C9A84C' }}
            >
              Get Demo
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
