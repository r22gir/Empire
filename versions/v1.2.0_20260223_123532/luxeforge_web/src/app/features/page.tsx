import Link from 'next/link'
import { MessageSquare, Camera, Calculator, ClipboardList, Users, BookOpen, ArrowRight } from 'lucide-react'

export default function FeaturesPage() {
  const features = [
    {
      id: 'intake',
      icon: MessageSquare,
      title: 'AI Conversational Intake',
      subtitle: 'No more intake forms',
      description:
        "LuxeForge's AI assistant guides clients through project scoping via natural conversation. It collects window dimensions, fabric preferences, lining requirements, rod styles, and timeline — then auto-populates the quote.",
      bullets: [
        'Works via SMS, web chat, or client portal',
        'Handles multiple windows per project',
        "Learns your workroom's product vocabulary",
      ],
    },
    {
      id: 'measurements',
      icon: Camera,
      title: 'Photo-Based Measurements',
      subtitle: 'Measure from any device',
      description:
        "Clients or installers upload a photo of the window. LuxeForge's vision model detects edges, applies a reference scale, and extracts width and height to within ¼ inch accuracy. No tape measure, no callbacks.",
      bullets: [
        'Works with smartphone photos',
        'Supports multiple windows per image',
        'Exports measurements directly to quote',
      ],
    },
    {
      id: 'quotes',
      icon: Calculator,
      title: 'Auto-Quote Generation',
      subtitle: 'Quote in minutes, not hours',
      description:
        'Configure your per-width drapery rates, per-sqft roman shade pricing, fabric markup, hardware markup, and installation fees once. LuxeForge applies them automatically every time, with line-item breakdowns clients can actually read.',
      bullets: [
        'Drapery: $95–$150/width configurable',
        'Roman shades: $15–$20/sqft',
        'Fabric 30–50% / Hardware 50% markup',
        '50% deposit terms built in',
      ],
    },
    {
      id: 'production',
      icon: ClipboardList,
      title: 'Production Queue',
      subtitle: 'Keep every order on track',
      description:
        'A Kanban-style production board gives your workroom team visibility into every active order. Drag projects across stages — Fabric Ordered, In Production, Ready for Installation, Delivered — and flag delays instantly.',
      bullets: [
        'Per-window and per-project tracking',
        'Automated status notifications to clients',
        'Attach fabric swatches and cut sheets',
      ],
    },
    {
      id: 'portal',
      icon: Users,
      title: 'Client Portal',
      subtitle: 'Approvals without the phone tag',
      description:
        'Every client gets a private link to review their estimate, select fabric options from your catalog, approve the quote with a digital signature, and pay their 50% deposit — all without calling your shop.',
      bullets: [
        'Mobile-friendly estimate review',
        'Integrated Stripe payment for deposits',
        'Real-time order status tracking',
      ],
    },
    {
      id: 'catalog',
      icon: BookOpen,
      title: 'Fabric & Hardware Catalog',
      subtitle: 'Rowley and Kravet, built in',
      description:
        "Browse and search the full Rowley Company and Kravet fabric and hardware catalogs directly inside LuxeForge. Select a fabric and your markup is applied automatically. Custom catalogs can be imported via CSV.",
      bullets: [
        'Rowley Co. & Kravet integrations',
        "COM (Customer's Own Material) workflow",
        'Custom catalog import via CSV',
      ],
    },
  ]

  return (
    <>
      {/* Hero */}
      <section className="bg-[#2C2C2C] text-white py-20 px-4 text-center">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold mb-4">
            Built for <span className="text-[#C9A84C]">Custom Workrooms</span>
          </h1>
          <p className="text-gray-300 text-lg">
            Every feature in LuxeForge was designed around how workrooms actually operate — not generic project management software.
          </p>
        </div>
      </section>

      {/* Feature Sections */}
      {features.map((feature, index) => (
        <section
          key={feature.id}
          id={feature.id}
          className={`py-20 px-4 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}
        >
          <div className="max-w-6xl mx-auto">
            <div className={`flex flex-col ${index % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'} items-center gap-12`}>
              {/* Icon / Visual Placeholder */}
              <div className="flex-1 flex justify-center">
                <div className="w-64 h-64 bg-[#2C2C2C] rounded-2xl flex flex-col items-center justify-center shadow-xl">
                  <feature.icon size={64} className="text-[#C9A84C] mb-4" />
                  <span className="text-white font-semibold text-center px-4">{feature.title}</span>
                </div>
              </div>
              {/* Text */}
              <div className="flex-1">
                <div className="text-[#C9A84C] font-semibold text-sm uppercase tracking-widest mb-2">{feature.subtitle}</div>
                <h2 className="text-4xl font-bold text-[#2C2C2C] mb-4">{feature.title}</h2>
                <p className="text-gray-600 text-lg leading-relaxed mb-6">{feature.description}</p>
                <ul className="space-y-2">
                  {feature.bullets.map((b) => (
                    <li key={b} className="flex items-start gap-2 text-gray-600">
                      <span className="text-[#C9A84C] font-bold mt-0.5">✓</span>
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>
      ))}

      {/* CTA */}
      <section className="bg-[#C9A84C] py-16 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-[#2C2C2C] mb-4">See LuxeForge in action</h2>
          <p className="text-[#2C2C2C]/80 mb-8">Schedule a 20-minute demo and we&apos;ll walk through every feature with your real use cases.</p>
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
