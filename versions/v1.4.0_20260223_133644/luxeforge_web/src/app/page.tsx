import Link from 'next/link'
import { MessageSquare, Camera, Calculator, ClipboardList, Users, BookOpen, ArrowRight, Star, TrendingUp, Award } from 'lucide-react'

export default function HomePage() {
  const features = [
    {
      icon: MessageSquare,
      title: 'AI Chat Intake',
      description: 'Conversational project intake collects window specs, fabric preferences, and timeline without manual forms.',
    },
    {
      icon: Camera,
      title: 'Photo Measurements',
      description: 'Upload a photo of any window and our AI extracts measurements automatically — no tape measure needed.',
    },
    {
      icon: Calculator,
      title: 'Auto-Quote Generation',
      description: 'Per-width drapery pricing, per-sqft roman shades, hardware markup, and installation — calculated instantly.',
    },
    {
      icon: ClipboardList,
      title: 'Production Queue',
      description: 'Drag-and-drop production board tracks every project from fabric order to final delivery.',
    },
    {
      icon: Users,
      title: 'Client Portal',
      description: 'Clients review and approve estimates online, pay deposits, and track order status in real time.',
    },
    {
      icon: BookOpen,
      title: 'Fabric & Hardware Catalog',
      description: 'Integrated Rowley Co. and Kravet catalogs with automatic markup applied at checkout.',
    },
  ]

  const stats = [
    { label: 'Workrooms', value: '500+', icon: Award },
    { label: 'Quotes Generated', value: '2M+', icon: Calculator },
    { label: 'Faster Production', value: '30%', icon: TrendingUp },
    { label: 'Client Satisfaction', value: '4.9★', icon: Star },
  ]

  const tiers = [
    { name: 'Solo', price: '$79', period: '/mo', description: 'Perfect for independent workroom owners', highlight: false },
    { name: 'Pro', price: '$249', period: '/mo', description: 'For growing workrooms with a small team', highlight: true },
    { name: 'Enterprise', price: '$599', period: '/mo', description: 'Multi-location and high-volume operations', highlight: false },
  ]

  return (
    <>
      {/* Hero */}
      <section className="bg-[#2C2C2C] text-white py-24 px-4">
        <div className="max-w-6xl mx-auto text-center">
          <div className="inline-block bg-[#C9A84C]/20 text-[#C9A84C] text-sm font-semibold px-4 py-1.5 rounded-full mb-6">
            Purpose-built for custom workrooms
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            Run Your Workroom<br />
            <span className="text-[#C9A84C]">Like a Pro</span>
          </h1>
          <p className="text-xl md:text-2xl text-gray-300 mb-4 max-w-3xl mx-auto">
            AI-powered quoting, production management, and client portal — built specifically for drapery and window treatment workrooms.
          </p>
          <p className="text-gray-400 mb-10 max-w-2xl mx-auto">
            Stop using spreadsheets. Start quoting in minutes, not hours.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/contact"
              className="bg-[#C9A84C] hover:bg-[#A07A2E] text-[#2C2C2C] font-bold px-8 py-4 rounded-lg text-lg transition flex items-center gap-2"
            >
              Request a Demo <ArrowRight size={20} />
            </Link>
            <Link
              href="/pricing"
              className="border-2 border-[#C9A84C] text-[#C9A84C] hover:bg-[#C9A84C]/10 font-bold px-8 py-4 rounded-lg text-lg transition"
            >
              View Pricing
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-[#1A1A1A] text-white py-10 px-4">
        <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-3xl font-bold text-[#C9A84C]">{s.value}</div>
              <div className="text-gray-400 text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <h2 className="text-4xl font-bold text-[#2C2C2C] mb-4">Everything Your Workroom Needs</h2>
            <p className="text-gray-500 text-lg max-w-2xl mx-auto">
              From first client contact to final invoice, LuxeForge handles every step of your workflow.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((f) => (
              <div key={f.title} className="rounded-xl border border-gray-100 p-7 hover:shadow-lg hover:border-[#C9A84C]/30 transition group">
                <div className="w-12 h-12 bg-[#C9A84C]/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-[#C9A84C]/20 transition">
                  <f.icon size={24} className="text-[#C9A84C]" />
                </div>
                <h3 className="text-xl font-bold text-[#2C2C2C] mb-2">{f.title}</h3>
                <p className="text-gray-500 leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-10">
            <Link href="/features" className="text-[#C9A84C] font-semibold hover:underline flex items-center gap-1 justify-center">
              Explore all features <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* Pricing Teaser */}
      <section className="py-20 px-4 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-[#2C2C2C] mb-4">Simple, Transparent Pricing</h2>
            <p className="text-gray-500 text-lg">Start free, scale as you grow.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            {tiers.map((t) => (
              <div
                key={t.name}
                className={`rounded-xl p-8 text-center ${
                  t.highlight
                    ? 'bg-[#2C2C2C] text-white ring-2 ring-[#C9A84C]'
                    : 'bg-white text-[#2C2C2C] border border-gray-200'
                }`}
              >
                {t.highlight && (
                  <div className="text-xs font-bold text-[#C9A84C] uppercase tracking-widest mb-3">Most Popular</div>
                )}
                <div className="text-xl font-bold mb-1">{t.name}</div>
                <div className="text-4xl font-bold mb-1">
                  {t.price}<span className={`text-base font-normal ${t.highlight ? 'text-gray-400' : 'text-gray-500'}`}>{t.period}</span>
                </div>
                <p className={`text-sm mt-2 mb-6 ${t.highlight ? 'text-gray-300' : 'text-gray-500'}`}>{t.description}</p>
                <Link
                  href="/pricing"
                  className={`block font-semibold py-2 px-6 rounded-lg transition ${
                    t.highlight
                      ? 'bg-[#C9A84C] hover:bg-[#A07A2E] text-[#2C2C2C]'
                      : 'border border-[#C9A84C] text-[#C9A84C] hover:bg-[#C9A84C]/10'
                  }`}
                >
                  Get Started
                </Link>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <Link href="/pricing" className="text-[#C9A84C] font-semibold hover:underline flex items-center gap-1 justify-center">
              See full pricing details <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-[#C9A84C] py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-bold text-[#2C2C2C] mb-4">Ready to streamline your workroom?</h2>
          <p className="text-[#2C2C2C]/80 text-lg mb-8">Join hundreds of workrooms already using LuxeForge to quote faster and produce more.</p>
          <Link
            href="/contact"
            className="bg-[#2C2C2C] hover:bg-[#1A1A1A] text-white font-bold px-8 py-4 rounded-lg text-lg transition inline-flex items-center gap-2"
          >
            Start Free Trial <ArrowRight size={20} />
          </Link>
        </div>
      </section>
    </>
  )
}
