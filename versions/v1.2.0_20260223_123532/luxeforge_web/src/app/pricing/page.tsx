import Link from 'next/link'
import { Check, ArrowRight } from 'lucide-react'

export default function PricingPage() {
  const tiers = [
    {
      name: 'Solo',
      price: '$79',
      period: '/month',
      description: 'Built for the independent workroom owner.',
      highlight: false,
      features: [
        'Up to 50 projects/month',
        'AI chat intake',
        'Photo measurements',
        'Auto-quote generation',
        'Client portal',
        'Email support',
      ],
      cta: 'Start Solo',
    },
    {
      name: 'Pro',
      price: '$249',
      period: '/month',
      description: 'For growing workrooms with a small team.',
      highlight: true,
      features: [
        'Unlimited projects',
        'Everything in Solo',
        'Production queue management',
        'Fabric & hardware catalog (Rowley, Kravet)',
        'Team collaboration (up to 5 users)',
        'Priority support',
        'Custom pricing templates',
        'Stripe payment integration',
      ],
      cta: 'Start Pro',
    },
    {
      name: 'Enterprise',
      price: '$599',
      period: '/month',
      description: 'Multi-location and high-volume operations.',
      highlight: false,
      features: [
        'Everything in Pro',
        'Unlimited users',
        'Multiple locations',
        'Custom fabric catalog import',
        'White-label client portal',
        'Dedicated account manager',
        'API access',
        'SLA guarantee',
      ],
      cta: 'Contact Sales',
    },
  ]

  const pricingModel = [
    { item: 'Drapery (per width)', range: '$95 – $150', notes: 'Standard lined panels' },
    { item: 'Roman Shades', range: '$15 – $20 / sq ft', notes: 'Flat or hobbled' },
    { item: 'Fabric Markup', range: '30 – 50%', notes: 'Applied automatically from catalog' },
    { item: 'Hardware Markup', range: '50%', notes: 'Rods, rings, brackets' },
    { item: 'Installation', range: '$45 – $195 / window', notes: 'Based on complexity' },
    { item: 'Payment Terms', range: '50% deposit', notes: 'Balance due on delivery' },
  ]

  const faqs = [
    {
      q: 'Is there a free trial?',
      a: 'Yes — all plans include a 14-day free trial, no credit card required.',
    },
    {
      q: 'Can I change plans later?',
      a: 'Absolutely. Upgrade or downgrade at any time. Billing is prorated automatically.',
    },
    {
      q: 'Does LuxeForge work for both drapery and roman shades?',
      a: 'Yes. The pricing engine supports per-width and per-sqft calculations simultaneously, so you can mix product types on a single quote.',
    },
    {
      q: 'Are the Rowley and Kravet catalogs included?',
      a: 'The catalogs are available on Pro and Enterprise plans. Fabric and hardware markups are configurable per product or globally.',
    },
    {
      q: 'Is my client data secure?',
      a: 'All data is encrypted in transit and at rest. We are SOC 2 compliant and never sell your data.',
    },
    {
      q: 'What payment methods do you accept?',
      a: 'We accept all major credit cards via Stripe. Annual plans receive a 20% discount.',
    },
  ]

  return (
    <>
      {/* Hero */}
      <section className="bg-[#2C2C2C] text-white py-20 px-4 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold mb-4">
            Pricing for Every <span className="text-[#C9A84C]">Workroom</span>
          </h1>
          <p className="text-gray-300 text-lg">
            From solo operators to multi-location businesses — flexible plans that grow with you.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-8">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={`rounded-2xl p-8 flex flex-col ${
                tier.highlight
                  ? 'bg-[#2C2C2C] text-white ring-2 ring-[#C9A84C]'
                  : 'border border-gray-200 text-[#2C2C2C]'
              }`}
            >
              {tier.highlight && (
                <div className="text-xs font-bold text-[#C9A84C] uppercase tracking-widest mb-4">Most Popular</div>
              )}
              <h2 className="text-2xl font-bold mb-1">{tier.name}</h2>
              <div className="text-5xl font-bold my-2">
                {tier.price}
                <span className={`text-base font-normal ${tier.highlight ? 'text-gray-400' : 'text-gray-500'}`}>
                  {tier.period}
                </span>
              </div>
              <p className={`text-sm mb-6 ${tier.highlight ? 'text-gray-300' : 'text-gray-500'}`}>{tier.description}</p>
              <ul className="space-y-3 flex-1 mb-8">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check size={16} className="text-[#C9A84C] flex-shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                href="/contact"
                className={`text-center font-semibold py-3 px-6 rounded-lg transition ${
                  tier.highlight
                    ? 'bg-[#C9A84C] hover:bg-[#A07A2E] text-[#2C2C2C]'
                    : 'border-2 border-[#C9A84C] text-[#C9A84C] hover:bg-[#C9A84C]/10'
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>
        <p className="text-center text-gray-500 mt-8 text-sm">
          All plans include a 14-day free trial · No credit card required · Cancel anytime
        </p>
      </section>

      {/* Workroom Pricing Model */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-[#2C2C2C] mb-3 text-center">Workroom Pricing Reference</h2>
          <p className="text-gray-500 text-center mb-10">
            LuxeForge pre-loads these industry-standard pricing defaults. Everything is customizable.
          </p>
          <div className="overflow-x-auto rounded-xl border border-gray-200">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#2C2C2C] text-white">
                  <th className="text-left py-4 px-6 font-semibold">Item</th>
                  <th className="text-left py-4 px-6 font-semibold">Default Range</th>
                  <th className="text-left py-4 px-6 font-semibold">Notes</th>
                </tr>
              </thead>
              <tbody>
                {pricingModel.map((row, i) => (
                  <tr key={row.item} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="py-4 px-6 font-medium text-[#2C2C2C]">{row.item}</td>
                    <td className="py-4 px-6 text-[#C9A84C] font-semibold">{row.range}</td>
                    <td className="py-4 px-6 text-gray-500">{row.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-[#2C2C2C] mb-10 text-center">Frequently Asked Questions</h2>
          <div className="space-y-6">
            {faqs.map((faq) => (
              <div key={faq.q} className="border-b border-gray-100 pb-6">
                <h3 className="font-semibold text-[#2C2C2C] mb-2">{faq.q}</h3>
                <p className="text-gray-500 leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-[#C9A84C] py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-[#2C2C2C] mb-4">Ready to start quoting faster?</h2>
          <Link
            href="/contact"
            className="bg-[#2C2C2C] hover:bg-[#1A1A1A] text-white font-bold px-8 py-4 rounded-lg text-lg transition inline-flex items-center gap-2"
          >
            Request a Demo <ArrowRight size={20} />
          </Link>
        </div>
      </section>
    </>
  )
}
