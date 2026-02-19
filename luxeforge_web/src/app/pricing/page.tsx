import Link from 'next/link';
import { Check, HelpCircle } from 'lucide-react';

function Navbar() {
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
            <Link href="/pricing" className="font-medium transition-colors" style={{ color: '#C9A84C' }}>
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

function Footer() {
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

const tiers = [
  {
    name: 'Solo',
    price: '$79',
    tagline: 'Perfect for independent workrooms',
    popular: false,
    features: [
      'Up to 2 users',
      '50 quotes/month',
      'AI chat intake',
      'Photo measurements',
      'Auto-quote generation',
      'Email support',
    ],
  },
  {
    name: 'Pro',
    price: '$249',
    tagline: 'For growing studios',
    popular: true,
    features: [
      'Up to 10 users',
      'Unlimited quotes',
      'Everything in Solo',
      'Production queue',
      'Client portal',
      'Priority support',
      'Custom branding',
    ],
  },
  {
    name: 'Enterprise',
    price: '$599',
    tagline: 'For large operations',
    popular: false,
    features: [
      'Unlimited users',
      'Everything in Pro',
      'Custom integrations',
      'Fabric/hardware catalog (Rowley, Kravet)',
      'Dedicated account manager',
      'SLA guarantee',
      'Custom training',
    ],
  },
];

const faqs = [
  {
    q: 'Is there a free trial?',
    a: 'Yes — every plan comes with a 14-day free trial. No credit card required to start.',
  },
  {
    q: 'Can I switch plans later?',
    a: 'Absolutely. You can upgrade or downgrade at any time. Changes take effect on your next billing cycle.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept all major credit cards (Visa, Mastercard, Amex) and ACH bank transfers for annual plans.',
  },
  {
    q: 'How does the photo measurement feature work?',
    a: 'Simply upload a photo of the window from your phone or camera. Our AI analyzes the image and extracts measurements within seconds — no special hardware needed.',
  },
  {
    q: 'Do you integrate with QuickBooks or other accounting tools?',
    a: 'QuickBooks integration is available on the Enterprise plan. Pro plan users can export invoices as PDF or CSV for manual import.',
  },
];

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Header */}
      <section className="pt-32 pb-16 px-4 sm:px-6 lg:px-8 text-center bg-gradient-to-br from-white via-gray-50 to-amber-50/30">
        <h1 className="text-5xl font-extrabold text-charcoal mb-4">Simple, Transparent Pricing</h1>
        <p className="text-xl text-gray-500 max-w-xl mx-auto">
          Choose the plan that fits your workroom. No hidden fees. Cancel anytime.
        </p>
      </section>

      {/* Pricing Cards */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`rounded-2xl p-8 border-2 relative ${
                  tier.popular ? 'border-yellow-400 shadow-2xl' : 'border-gray-100'
                }`}
                style={tier.popular ? { backgroundColor: '#FFFBF0' } : {}}
              >
                {tier.popular && (
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 px-5 py-1.5 rounded-full text-xs font-bold text-white whitespace-nowrap"
                    style={{ backgroundColor: '#C9A84C' }}
                  >
                    MOST POPULAR
                  </div>
                )}
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-charcoal">{tier.name}</h2>
                  <p className="text-gray-500 text-sm mt-1">{tier.tagline}</p>
                  <div className="mt-5">
                    <span className="text-5xl font-extrabold text-charcoal">{tier.price}</span>
                    <span className="text-gray-400 ml-2 text-lg">/month</span>
                  </div>
                  <p className="text-xs text-gray-400 mt-1">Billed monthly. Save 20% annually.</p>
                </div>
                <ul className="space-y-3 mb-8">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-sm text-gray-700">
                      <Check size={16} style={{ color: '#C9A84C' }} className="flex-shrink-0 mt-0.5" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/contact"
                  className={`block text-center py-3.5 rounded-md font-semibold transition-all ${
                    tier.popular
                      ? 'text-white hover:opacity-90'
                      : 'border-2 border-gray-200 text-charcoal hover:border-yellow-400'
                  }`}
                  style={tier.popular ? { backgroundColor: '#C9A84C' } : {}}
                >
                  {tier.name === 'Enterprise' ? 'Contact Sales' : 'Start Free Trial'}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Model Info */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-charcoal mb-8 text-center">How LuxeForge Calculates Your Quotes</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { label: 'Drapery', value: '$95 – $150/width', note: 'Standard per-width pricing' },
              { label: 'Roman Shades', value: '$15 – $20/sqft', note: 'Based on finished dimensions' },
              { label: 'Fabric Markup', value: '30 – 50%', note: 'Fully customizable per project' },
              { label: 'Hardware Markup', value: '50%', note: 'Applied to wholesale cost' },
              { label: 'Installation', value: '$45 – $195/window', note: 'Varies by complexity' },
              { label: 'Deposit Terms', value: '50% upfront', note: 'Configurable per client' },
            ].map((item) => (
              <div key={item.label} className="bg-white rounded-xl p-5 border border-gray-100">
                <div className="text-sm text-gray-500 font-medium mb-1">{item.label}</div>
                <div className="text-xl font-bold text-charcoal mb-1" style={{ color: '#C9A84C' }}>{item.value}</div>
                <div className="text-xs text-gray-400">{item.note}</div>
              </div>
            ))}
          </div>
          <p className="text-center text-sm text-gray-400 mt-6">
            All pricing defaults are fully customizable inside LuxeForge to match your workroom&apos;s actual rates.
          </p>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-charcoal mb-10 text-center">Frequently Asked Questions</h2>
          <div className="space-y-6">
            {faqs.map((faq) => (
              <div key={faq.q} className="border border-gray-100 rounded-xl p-6">
                <div className="flex items-start gap-3">
                  <HelpCircle size={20} style={{ color: '#C9A84C' }} className="flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-charcoal mb-2">{faq.q}</h3>
                    <p className="text-gray-500 text-sm leading-relaxed">{faq.a}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
