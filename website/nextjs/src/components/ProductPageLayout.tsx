import Link from 'next/link';
import Navbar from '@/components/Navbar';
import LegalFooter from '@/components/LegalFooter';

interface PricingTier {
  name: string;
  price: string;
  period: string;
  features: string[];
  featured?: boolean;
}

interface ProductPageLayoutProps {
  icon: string;
  name: string;
  tagline: string;
  description: string;
  features: string[];
  pricingTiers: PricingTier[];
  ctaText?: string;
  ctaHref?: string;
}

export default function ProductPageLayout({
  icon,
  name,
  tagline,
  description,
  features,
  pricingTiers,
  ctaText = 'Start Free Trial',
  ctaHref = '/setup',
}: ProductPageLayoutProps) {
  return (
    <main>
      <Navbar />
      <div className="min-h-screen bg-gray-50">
        {/* Hero */}
        <section className="bg-primary-700 text-white py-20">
          <div className="max-w-4xl mx-auto px-4 text-center">
            <div className="text-6xl mb-4">{icon}</div>
            <h1 className="text-4xl font-heading font-bold mb-4">{name}</h1>
            <p className="text-xl font-semibold mb-4 opacity-90">{tagline}</p>
            <p className="text-lg opacity-80 max-w-2xl mx-auto mb-8">{description}</p>
            <Link
              href={ctaHref}
              className="inline-block bg-white text-primary-700 font-bold py-3 px-8 rounded-lg hover:bg-gray-100 transition-colors"
            >
              {ctaText}
            </Link>
          </div>
        </section>

        {/* Features */}
        <section className="py-16 max-w-4xl mx-auto px-4">
          <h2 className="text-3xl font-heading font-bold text-gray-900 mb-8 text-center">Features</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {features.map((feature) => (
              <div key={feature} className="flex items-start bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                <span className="text-green-500 font-bold mr-3 mt-0.5">✓</span>
                <span className="text-gray-700">{feature}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Pricing */}
        <section className="py-16 bg-white">
          <div className="max-w-5xl mx-auto px-4">
            <h2 className="text-3xl font-heading font-bold text-gray-900 mb-2 text-center">Pricing</h2>
            <p className="text-center text-gray-600 mb-10">All prices in USD. Cancel anytime. No hidden fees.</p>
            <div className={`grid gap-8 ${pricingTiers.length === 1 ? 'max-w-sm mx-auto' : pricingTiers.length === 2 ? 'md:grid-cols-2' : 'md:grid-cols-3'}`}>
              {pricingTiers.map((tier) => (
                <div
                  key={tier.name}
                  className={`rounded-xl p-8 border-2 ${tier.featured ? 'border-primary-700 shadow-lg' : 'border-gray-200'} bg-white relative`}
                >
                  {tier.featured && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <span className="bg-accent-500 text-white text-xs font-bold px-3 py-1 rounded-full">Most Popular</span>
                    </div>
                  )}
                  <h3 className="text-xl font-heading font-bold text-gray-900 mb-2">{tier.name}</h3>
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-gray-900">{tier.price}</span>
                    <span className="text-gray-600 ml-1">/{tier.period}</span>
                  </div>
                  <ul className="space-y-3 mb-8">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-start text-sm">
                        <svg className="h-5 w-5 text-green-500 mr-2 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        <span className="text-gray-700">{f}</span>
                      </li>
                    ))}
                  </ul>
                  <Link
                    href={ctaHref}
                    className={`block text-center py-3 px-6 rounded-lg font-semibold transition-colors ${tier.featured ? 'bg-primary-700 text-white hover:bg-primary-800' : 'bg-gray-100 text-gray-900 hover:bg-gray-200'}`}
                  >
                    {ctaText}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Legal */}
        <section className="py-8 max-w-4xl mx-auto px-4">
          <LegalFooter />
        </section>
      </div>
    </main>
  );
}
