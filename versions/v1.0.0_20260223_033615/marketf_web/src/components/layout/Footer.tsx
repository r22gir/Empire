import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="bg-dark text-white py-12 mt-20">
      <div className="container">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div>
            <h4 className="text-xl font-bold mb-4">MarketF</h4>
            <p className="text-gray-400">
              The marketplace with only 8% fees
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="font-bold mb-4">Quick Links</h4>
            <ul className="space-y-2 text-gray-400">
              <li><Link href="/" className="hover:text-white">Home</Link></li>
              <li><Link href="/search" className="hover:text-white">Browse</Link></li>
              <li><Link href="/seller/dashboard" className="hover:text-white">Sell</Link></li>
              <li><Link href="/about" className="hover:text-white">About</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="font-bold mb-4">Support</h4>
            <ul className="space-y-2 text-gray-400">
              <li><Link href="/help" className="hover:text-white">Help Center</Link></li>
              <li><Link href="/contact" className="hover:text-white">Contact Us</Link></li>
              <li><Link href="/shipping" className="hover:text-white">Shipping Info</Link></li>
              <li><Link href="/returns" className="hover:text-white">Returns</Link></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="font-bold mb-4">Legal</h4>
            <ul className="space-y-2 text-gray-400">
              <li><Link href="/terms" className="hover:text-white">Terms of Service</Link></li>
              <li><Link href="/privacy" className="hover:text-white">Privacy Policy</Link></li>
              <li><Link href="/fees" className="hover:text-white">Fee Structure</Link></li>
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="border-t border-gray-700 pt-8 text-center text-gray-400">
          <p>© 2026 MarketF by EmpireBox. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
