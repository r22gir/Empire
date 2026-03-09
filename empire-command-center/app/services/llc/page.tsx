'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Globe,
  Building2,
  Shield,
  FileText,
  Stamp,
  MapPin,
  Sparkles,
  Check,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Phone,
  Mail,
  Zap,
  Users,
  Car,
  Award,
  Clock,
} from 'lucide-react';

/* ───────────────────── DATA ───────────────────── */

const services = [
  { icon: Building2, title: 'Business Formation', desc: 'LLC, Corp, Nonprofit, DBA', color: '#16a34a' },
  { icon: Shield, title: 'Tax & Compliance', desc: 'EIN, Tax Registration, BOI', color: '#2563eb' },
  { icon: FileText, title: 'Document Services', desc: 'Apostille, Legalization, Certificates', color: '#9333ea' },
  { icon: Stamp, title: 'Notary Services', desc: 'Mobile Notary, Remote Online', color: '#b8960c' },
  { icon: MapPin, title: 'Registered Agent', desc: 'DC, MD, VA coverage', color: '#dc2626' },
  { icon: Sparkles, title: 'Additional Services', desc: 'Trademark, Operating Agreements', color: '#0891b2' },
];

const packages = [
  {
    name: 'Starter',
    price: '$0',
    note: '+ state fees',
    badge: null,
    features: [
      'LLC formation filing',
      'Basic Operating Agreement template',
      'Digital confirmation',
    ],
    cta: 'Get Started Free',
    highlight: false,
  },
  {
    name: 'Professional',
    price: '$149',
    note: '+ state fees',
    badge: 'MOST POPULAR',
    features: [
      'Everything in Starter',
      'EIN filing',
      'Custom AI Operating Agreement',
      '1 year Registered Agent',
      'BOI filing',
      'Compliance reminders',
    ],
    cta: 'Choose Professional',
    highlight: true,
  },
  {
    name: 'Empire',
    price: '$349',
    note: '+ state fees',
    badge: 'BEST VALUE',
    features: [
      'Everything in Professional',
      'Business License application',
      'Apostille for Articles',
      'Certificate of Good Standing',
      'Bank account guidance',
      'Priority processing',
      '30-min consultation',
    ],
    cta: 'Choose Empire',
    highlight: false,
  },
];

const stateData: Record<string, { fee: string; time: string; annualDeadline: string; annualFee: string; authority: string; requirements: string[] }> = {
  DC: {
    fee: '$220',
    time: '3-5 business days',
    annualDeadline: 'April 1 (biennial)',
    annualFee: '$300 (biennial)',
    authority: 'DC Department of Licensing and Consumer Protection (DLCP)',
    requirements: [
      'Registered Agent with DC address required',
      'Articles of Organization filed with DLCP',
      'Biennial report filed every 2 years',
      'Business license required for most activities',
    ],
  },
  Maryland: {
    fee: '$100',
    time: '7-10 business days (expedite available)',
    annualDeadline: 'April 15',
    annualFee: '$300',
    authority: 'Maryland State Department of Assessments and Taxation (SDAT)',
    requirements: [
      'Resident Agent with MD address required',
      'Articles of Organization filed with SDAT',
      'Annual report + personal property return',
      'Trade name registration if using DBA',
    ],
  },
  Virginia: {
    fee: '$100',
    time: '3-5 business days',
    annualDeadline: 'Last day of anniversary month',
    annualFee: '$50',
    authority: 'Virginia State Corporation Commission (SCC)',
    requirements: [
      'Registered Agent with VA street address required',
      'Articles of Organization filed with SCC',
      'Annual registration fee due each year',
      'Local business license may be required by county/city',
    ],
  },
};

const advantages = [
  { icon: Users, title: 'Bilingual EN/ES', desc: 'Serving the DMV\'s diverse community with full Spanish-language support.' },
  { icon: FileText, title: 'Apostille + Notary Bundled', desc: 'One provider for all document authentication needs.' },
  { icon: Zap, title: 'AI-Powered Documents', desc: 'Custom operating agreements generated in minutes, not days.' },
  { icon: Globe, title: 'Local + Nationwide', desc: 'DMV-based experts with 50-state filing reach.' },
  { icon: Car, title: 'Mobile Notary', desc: 'We come to you — home, office, or anywhere in the DMV.' },
  { icon: Award, title: 'Embassy Legalization', desc: 'Full authentication chain for international document use.' },
];

const steps = [
  { num: '1', title: 'Choose Your Package', desc: 'Select services and your filing state.' },
  { num: '2', title: 'Submit Your Info', desc: 'Business name, members, and details.' },
  { num: '3', title: 'We File & Process', desc: 'Same-day filing and document generation.' },
  { num: '4', title: 'Receive Your Documents', desc: 'Digital delivery with real-time tracking.' },
];

const faqs = [
  {
    q: 'How long does it take to form an LLC?',
    a: 'Processing times vary by state. DC typically takes 3-5 business days, Maryland 7-10 days (expedite available), and Virginia 3-5 business days. We offer same-day filing submission for all states.',
  },
  {
    q: "What's included in the state filing fee?",
    a: 'The state filing fee covers the government charge for processing your Articles of Organization. It does not include our service fee, registered agent, or additional services like EIN filing or operating agreements.',
  },
  {
    q: 'Do I need a registered agent?',
    a: 'Yes. DC, Maryland, and Virginia all require LLCs to maintain a registered agent with a physical address in the state. Our Professional and Empire packages include one year of registered agent service.',
  },
  {
    q: 'What is an apostille?',
    a: 'An apostille is an official certificate that authenticates the origin of a public document (such as Articles of Organization) for use in countries that are part of the Hague Convention. We handle the full apostille process with the Secretary of State.',
  },
  {
    q: 'Can you help with embassy legalization?',
    a: 'Yes. For countries that are not part of the Hague Convention, we provide full embassy/consulate legalization services, including document preparation, authentication chain, and submission.',
  },
  {
    q: 'Do you offer services in Spanish?',
    a: 'Absolutely. Our entire team is bilingual (English/Spanish). We can assist you through every step of the process in Spanish, including document preparation and consultations.',
  },
];

/* ───────────────────── COMPONENT ───────────────────── */

export default function LLCFactoryPage() {
  const [activeState, setActiveState] = useState<string>('DC');
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const stateKeys = Object.keys(stateData);
  const currentState = stateData[activeState];

  return (
    <div className="min-h-screen bg-[#f5f2ed]">

      {/* ── NAV ── */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-[#e8e4dc] sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#16a34a] flex items-center justify-center">
              <Globe size={16} className="text-white" />
            </div>
            <span className="font-bold text-[15px] text-[#1a1a1a] tracking-tight">LLC Factory</span>
          </div>
          <div className="flex items-center gap-3">
            <a href="#pricing" className="text-[12px] text-[#666] hover:text-[#16a34a] transition-colors font-medium hidden sm:block">
              Pricing
            </a>
            <a href="#faq" className="text-[12px] text-[#666] hover:text-[#16a34a] transition-colors font-medium hidden sm:block">
              FAQ
            </a>
            <Link
              href="/intake/signup"
              className="px-5 py-2 text-[12px] font-semibold bg-[#b8960c] text-white rounded-lg hover:bg-[#a3850b] transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="py-20 sm:py-28 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#16a34a]/10 border border-[#16a34a]/20 text-[#16a34a] text-[12px] font-semibold mb-8">
            <Globe size={14} /> LLC Factory
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-[#1a1a1a] mb-5 leading-tight">
            Your One-Stop Business Formation<br className="hidden sm:block" /> & Document Services
          </h1>
          <p className="text-base sm:text-lg text-[#666] max-w-2xl mx-auto mb-10 leading-relaxed">
            LLC formation, apostille, notary, and registered agent services for DC, Maryland & Virginia.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <Link
              href="/intake/signup"
              className="inline-flex items-center gap-2 px-8 py-3.5 text-sm font-bold bg-[#b8960c] text-white rounded-xl hover:bg-[#a3850b] transition-all hover:shadow-lg group"
            >
              Get Started — $0 <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
            </Link>
            <a
              href="#pricing"
              className="inline-flex items-center gap-2 px-8 py-3.5 text-sm font-bold text-[#1a1a1a] border-2 border-[#d5d0c8] rounded-xl hover:border-[#16a34a] hover:text-[#16a34a] transition-all"
            >
              View Pricing
            </a>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
            {[
              { icon: Shield, label: 'DC \u00b7 MD \u00b7 VA Licensed' },
              { icon: Clock, label: 'Same-Day Filing' },
              { icon: Zap, label: 'AI-Powered Documents' },
              { icon: Users, label: 'Bilingual EN/ES' },
            ].map((b, i) => (
              <div key={i} className="flex items-center gap-1.5 text-[12px] text-[#888] font-medium">
                <b.icon size={13} className="text-[#16a34a]" />
                {b.label}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SERVICES OVERVIEW ── */}
      <section className="py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1a1a1a] mb-3">Our Services</h2>
            <p className="text-[#888] text-sm max-w-lg mx-auto">Comprehensive business formation and document services, all under one roof.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {services.map((s, i) => (
              <div
                key={i}
                className="bg-white rounded-2xl border border-[#ece8e0] p-6 hover:border-[#d5d0c8] hover:shadow-[0_4px_20px_rgba(0,0,0,0.04)] hover:-translate-y-[2px] transition-all"
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                  style={{ background: s.color + '12', border: `1px solid ${s.color}25` }}
                >
                  <s.icon size={22} style={{ color: s.color }} />
                </div>
                <h3 className="font-semibold text-[15px] text-[#1a1a1a] mb-1.5">{s.title}</h3>
                <p className="text-[13px] text-[#888] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PRICING ── */}
      <section id="pricing" className="py-16 px-4 bg-white/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1a1a1a] mb-3">Simple, Transparent Pricing</h2>
            <p className="text-[#888] text-sm max-w-lg mx-auto">Choose the package that fits your needs. No hidden fees, ever.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {packages.map((pkg, i) => (
              <div
                key={i}
                className={`relative rounded-2xl p-7 transition-all ${
                  pkg.highlight
                    ? 'bg-white border-2 border-[#16a34a] shadow-[0_8px_40px_rgba(22,163,74,0.12)]'
                    : 'bg-white border border-[#ece8e0] hover:border-[#d5d0c8]'
                }`}
              >
                {pkg.badge && (
                  <div
                    className={`absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-[10px] font-bold tracking-wider text-white ${
                      pkg.badge === 'MOST POPULAR' ? 'bg-[#16a34a]' : 'bg-[#b8960c]'
                    }`}
                  >
                    {pkg.badge}
                  </div>
                )}
                <div className="mb-6 pt-2">
                  <h3 className="text-[13px] font-semibold text-[#888] uppercase tracking-wider mb-2">{pkg.name}</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-[#1a1a1a]">{pkg.price}</span>
                    <span className="text-[13px] text-[#aaa]">{pkg.note}</span>
                  </div>
                </div>
                <ul className="space-y-3 mb-8">
                  {pkg.features.map((f, j) => (
                    <li key={j} className="flex items-start gap-2.5 text-[13px] text-[#555]">
                      <Check size={15} className="text-[#16a34a] mt-0.5 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/intake/signup"
                  className={`block text-center py-3 rounded-xl text-[13px] font-bold transition-all ${
                    pkg.highlight
                      ? 'bg-[#16a34a] text-white hover:bg-[#15803d]'
                      : 'bg-[#1a1a1a] text-white hover:bg-[#333]'
                  }`}
                >
                  {pkg.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── STATE-SPECIFIC INFO ── */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1a1a1a] mb-3">State Filing Details</h2>
            <p className="text-[#888] text-sm max-w-lg mx-auto">Each state has different requirements and fees. Here is what you need to know.</p>
          </div>
          {/* Tabs */}
          <div className="flex justify-center gap-2 mb-8">
            {stateKeys.map((st) => (
              <button
                key={st}
                onClick={() => setActiveState(st)}
                className={`px-6 py-2.5 rounded-xl text-[13px] font-semibold transition-all ${
                  activeState === st
                    ? 'bg-[#16a34a] text-white shadow-md'
                    : 'bg-white text-[#666] border border-[#ece8e0] hover:border-[#16a34a] hover:text-[#16a34a]'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
          {/* Content */}
          <div className="bg-white rounded-2xl border border-[#ece8e0] p-6 sm:p-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
              <div>
                <div className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider mb-1">State Filing Fee</div>
                <div className="text-xl font-bold text-[#1a1a1a]">{currentState.fee}</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider mb-1">Processing Time</div>
                <div className="text-xl font-bold text-[#1a1a1a]">{currentState.time}</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider mb-1">Annual Report Deadline</div>
                <div className="text-xl font-bold text-[#1a1a1a]">{currentState.annualDeadline}</div>
              </div>
              <div>
                <div className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider mb-1">Annual Report Fee</div>
                <div className="text-xl font-bold text-[#1a1a1a]">{currentState.annualFee}</div>
              </div>
            </div>
            <div className="mb-5">
              <div className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider mb-1">Filing Authority</div>
              <div className="text-[14px] font-semibold text-[#1a1a1a]">{currentState.authority}</div>
            </div>
            <div>
              <div className="text-[11px] font-semibold text-[#aaa] uppercase tracking-wider mb-3">Key Requirements</div>
              <ul className="space-y-2">
                {currentState.requirements.map((r, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-[13px] text-[#555]">
                    <Check size={14} className="text-[#16a34a] mt-0.5 flex-shrink-0" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ── WHY LLC FACTORY ── */}
      <section className="py-16 px-4 bg-white/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1a1a1a] mb-3">Why LLC Factory</h2>
            <p className="text-[#888] text-sm max-w-lg mx-auto">Built for the DMV community with services you will not find bundled anywhere else.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {advantages.map((a, i) => (
              <div key={i} className="bg-white rounded-2xl border border-[#ece8e0] p-6 hover:border-[#d5d0c8] hover:shadow-sm transition-all">
                <div className="w-10 h-10 rounded-xl bg-[#16a34a]/10 border border-[#16a34a]/20 flex items-center justify-center mb-4">
                  <a.icon size={18} className="text-[#16a34a]" />
                </div>
                <h3 className="font-semibold text-[15px] text-[#1a1a1a] mb-1.5">{a.title}</h3>
                <p className="text-[13px] text-[#888] leading-relaxed">{a.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1a1a1a] mb-3">How It Works</h2>
            <p className="text-[#888] text-sm max-w-lg mx-auto">Four simple steps from start to business owner.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-14 h-14 rounded-full bg-[#16a34a] text-white text-xl font-bold flex items-center justify-center mx-auto mb-4 shadow-[0_4px_16px_rgba(22,163,74,0.25)]">
                  {s.num}
                </div>
                <h3 className="font-semibold text-[15px] text-[#1a1a1a] mb-1.5">{s.title}</h3>
                <p className="text-[13px] text-[#888] leading-relaxed">{s.desc}</p>
                {i < steps.length - 1 && (
                  <div className="hidden lg:block absolute right-0 top-1/2 -translate-y-1/2">
                    <ArrowRight size={16} className="text-[#d5d0c8]" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="py-16 px-4 bg-white/50">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1a1a1a] mb-3">Frequently Asked Questions</h2>
            <p className="text-[#888] text-sm max-w-lg mx-auto">Everything you need to know about forming your business.</p>
          </div>
          <div className="space-y-3">
            {faqs.map((faq, i) => (
              <div
                key={i}
                className="bg-white rounded-xl border border-[#ece8e0] overflow-hidden transition-all"
              >
                <button
                  onClick={() => setOpenFaq(openFaq === i ? null : i)}
                  className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-[#faf9f7] transition-colors"
                >
                  <span className="text-[14px] font-semibold text-[#1a1a1a] pr-4">{faq.q}</span>
                  {openFaq === i ? (
                    <ChevronUp size={18} className="text-[#aaa] flex-shrink-0" />
                  ) : (
                    <ChevronDown size={18} className="text-[#aaa] flex-shrink-0" />
                  )}
                </button>
                {openFaq === i && (
                  <div className="px-6 pb-5">
                    <p className="text-[13px] text-[#666] leading-relaxed">{faq.a}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER CTA ── */}
      <section className="py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-[#1a1a1a] mb-4">Ready to Start Your Business?</h2>
          <p className="text-[#888] text-sm mb-8 max-w-md mx-auto">
            Join hundreds of entrepreneurs who trust LLC Factory for fast, affordable business formation.
          </p>
          <Link
            href="/intake/signup"
            className="inline-flex items-center gap-2 px-10 py-4 text-sm font-bold bg-[#b8960c] text-white rounded-xl hover:bg-[#a3850b] transition-all hover:shadow-lg group"
          >
            Get Started <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
          </Link>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-6 mt-10 text-[13px] text-[#888]">
            <a href="mailto:hello@llcfactory.com" className="flex items-center gap-2 hover:text-[#16a34a] transition-colors">
              <Mail size={14} /> hello@llcfactory.com
            </a>
            <a href="tel:+12025551234" className="flex items-center gap-2 hover:text-[#16a34a] transition-colors">
              <Phone size={14} /> (202) 555-1234
            </a>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[#e8e4dc] py-8 px-4">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-[#16a34a] flex items-center justify-center">
              <Globe size={12} className="text-white" />
            </div>
            <span className="text-[12px] font-semibold text-[#888]">LLC Factory</span>
            <span className="text-[11px] text-[#bbb]">by Empire</span>
          </div>
          <p className="text-[11px] text-[#bbb]">&copy; {new Date().getFullYear()} LLC Factory. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
