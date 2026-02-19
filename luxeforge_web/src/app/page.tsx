import Link from 'next/link';
import {
  MessageSquare,
  Camera,
  FileText,
  LayoutDashboard,
  Users,
  BookOpen,
  ArrowRight,
  Check,
  Star,
} from 'lucide-react';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

const features = [
  {
    icon: MessageSquare,
    title: 'AI Chat Intake',
    description: 'Conversational AI captures every project detail — room dimensions, fabric preferences, hardware selections — automatically.',
  },
  {
    icon: Camera,
    title: 'Photo Measurements',
    description: 'Upload a photo and our AI extracts accurate window measurements, eliminating costly site-visit errors.',
  },
  {
    icon: FileText,
    title: 'Auto-Quote Generation',
    description: 'Generate professional PDF quotes in seconds using your custom markup rules and live fabric pricing.',
  },
  {
    icon: LayoutDashboard,
    title: 'Production Queue',
    description: 'Visual kanban board keeps your workroom on track — prioritize jobs, assign staff, track orders.',
  },
  {
    icon: Users,
    title: 'Client Portal',
    description: 'Branded client portal for estimate approvals, e-signatures, deposit payments, and project updates.',
  },
  {
    icon: BookOpen,
    title: 'Fabric Catalog',
    description: 'Live integration with Rowley Co and Kravet — browse, price, and order fabrics without leaving LuxeForge.',
  },
];

const pricingTiers = [
  {
    name: 'Solo',
    price: '$79',
    tagline: 'For independent workrooms',
    features: ['Up to 2 users', '50 quotes/month', 'AI chat intake', 'Photo measurements', 'Auto-quote generation', 'Email support'],
    popular: false,
  },
  {
    name: 'Pro',
    price: '$249',
    tagline: 'For growing studios',
    features: ['Up to 10 users', 'Unlimited quotes', 'Everything in Solo', 'Production queue', 'Client portal', 'Priority support', 'Custom branding'],
    popular: true,
  },
  {
    name: 'Enterprise',
    price: '$599',
    tagline: 'For large operations',
    features: ['Unlimited users', 'Everything in Pro', 'Custom integrations', 'Fabric/hardware catalog', 'Dedicated account manager', 'SLA guarantee'],
    popular: false,
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-white via-gray-50 to-amber-50/30">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-medium mb-6 border"
            style={{ color: '#A07830', borderColor: '#E8C97A', backgroundColor: '#FDF8EE' }}
          >
            <Star size={14} fill="#C9A84C" stroke="#C9A84C" />
            Trusted by 500+ Custom Workrooms
          </div>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-charcoal leading-tight mb-6">
            The AI-Powered Platform
            <br />
            <span style={{ color: '#C9A84C' }}>for Custom Workrooms</span>
          </h1>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto mb-10 leading-relaxed">
            Transform your quoting process with conversational AI intake, photo-based measurements,
            and instant professional quotes — all in one luxury-grade platform.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/contact"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-md font-semibold text-white text-lg transition-all hover:opacity-90 shadow-lg"
              style={{ backgroundColor: '#C9A84C' }}
            >
              Start Free Trial <ArrowRight size={20} />
            </Link>
            <Link
              href="/features"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-md font-semibold text-charcoal text-lg border-2 border-gray-200 hover:border-gray-300 transition-all"
            >
              Watch Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="py-12 border-y border-gray-100 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { value: '500+', label: 'Workrooms' },
              { value: '$2M+', label: 'Quotes Generated' },
              { value: '40%', label: 'Faster Turnaround' },
              { value: '98%', label: 'Quote Accuracy' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-4xl font-extrabold" style={{ color: '#C9A84C' }}>{stat.value}</div>
                <div className="text-gray-500 font-medium mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-charcoal mb-4">
              Everything Your Workroom Needs
            </h2>
            <p className="text-xl text-gray-500 max-w-xl mx-auto">
              From first client contact to final installation — LuxeForge handles every step.
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="bg-white rounded-xl p-8 border border-gray-100 hover:border-yellow-200 hover:shadow-lg transition-all group"
                >
                  <div
                    className="w-12 h-12 rounded-lg flex items-center justify-center mb-5"
                    style={{ backgroundColor: '#FDF8EE' }}
                  >
                    <Icon size={24} style={{ color: '#C9A84C' }} />
                  </div>
                  <h3 className="text-lg font-bold text-charcoal mb-2">{feature.title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
          <div className="text-center mt-10">
            <Link
              href="/features"
              className="inline-flex items-center gap-2 font-semibold transition-colors"
              style={{ color: '#C9A84C' }}
            >
              See all features <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing Teaser */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-charcoal mb-4">Simple, Transparent Pricing</h2>
            <p className="text-xl text-gray-500">No hidden fees. Cancel anytime.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {pricingTiers.map((tier) => (
              <div
                key={tier.name}
                className={`rounded-xl p-8 border-2 relative ${
                  tier.popular
                    ? 'border-yellow-400 shadow-xl scale-105'
                    : 'border-gray-100'
                }`}
                style={tier.popular ? { backgroundColor: '#FFFBF0' } : { backgroundColor: '#FAFAFA' }}
              >
                {tier.popular && (
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-bold text-white"
                    style={{ backgroundColor: '#C9A84C' }}
                  >
                    MOST POPULAR
                  </div>
                )}
                <div className="mb-6">
                  <h3 className="text-xl font-bold text-charcoal">{tier.name}</h3>
                  <p className="text-gray-500 text-sm mt-1">{tier.tagline}</p>
                  <div className="mt-4">
                    <span className="text-4xl font-extrabold text-charcoal">{tier.price}</span>
                    <span className="text-gray-400 ml-1">/month</span>
                  </div>
                </div>
                <ul className="space-y-3 mb-8">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                      <Check size={16} style={{ color: '#C9A84C' }} className="flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/contact"
                  className={`block text-center py-3 rounded-md font-semibold transition-all ${
                    tier.popular
                      ? 'text-white hover:opacity-90'
                      : 'border-2 border-gray-200 text-charcoal hover:border-yellow-400'
                  }`}
                  style={tier.popular ? { backgroundColor: '#C9A84C' } : {}}
                >
                  Get Started
                </Link>
              </div>
            ))}
          </div>
          <div className="text-center mt-10">
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 font-semibold transition-colors"
              style={{ color: '#C9A84C' }}
            >
              View full pricing details <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section
        className="py-24 px-4 sm:px-6 lg:px-8"
        style={{ background: 'linear-gradient(135deg, #2C2C2C 0%, #1A1A1A 100%)' }}
      >
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl sm:text-5xl font-extrabold text-white mb-6">
            Ready to transform your workroom?
          </h2>
          <p className="text-xl text-gray-300 mb-10">
            Join 500+ workrooms already using LuxeForge to win more clients and deliver faster.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/contact"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-md font-semibold text-charcoal text-lg transition-all hover:opacity-90 shadow-lg"
              style={{ backgroundColor: '#C9A84C' }}
            >
              Start Your Free Trial <ArrowRight size={20} />
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-md font-semibold text-white text-lg border-2 border-gray-600 hover:border-gray-400 transition-all"
            >
              View Pricing
            </Link>
          </div>
          <p className="text-gray-500 text-sm mt-6">No credit card required · 14-day free trial · Cancel anytime</p>
        </div>
      </section>

      <Footer />
    </div>
  );
}
