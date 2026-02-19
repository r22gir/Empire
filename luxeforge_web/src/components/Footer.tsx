import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="bg-charcoal text-gray-300 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div>
            <div className="text-2xl font-bold text-white mb-3">
              Luxe<span style={{ color: '#C9A84C' }}>Forge</span>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">
              The AI-powered platform built for custom workroom excellence.
            </p>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Product</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/features" className="hover:text-white transition-colors">Features</Link></li>
              <li><Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link></li>
              <li><Link href="/contact" className="hover:text-white transition-colors">Request Demo</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Company</h4>
            <ul className="space-y-2 text-sm">
              <li><span className="text-gray-500">About</span></li>
              <li><span className="text-gray-500">Blog</span></li>
              <li><span className="text-gray-500">Careers</span></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-semibold mb-3">Support</h4>
            <ul className="space-y-2 text-sm">
              <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
              <li><span className="text-gray-500">Documentation</span></li>
              <li><span className="text-gray-500">Status</span></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-gray-700 pt-8 flex flex-col sm:flex-row justify-between items-center">
          <p className="text-sm text-gray-500">© 2024 LuxeForge. All rights reserved.</p>
          <div className="flex space-x-6 mt-4 sm:mt-0 text-sm text-gray-500">
            <span>Privacy Policy</span>
            <span>Terms of Service</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
