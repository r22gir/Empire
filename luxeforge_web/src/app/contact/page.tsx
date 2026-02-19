'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Mail, Phone, MapPin, Clock, CheckCircle } from 'lucide-react';

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
            <Link href="/pricing" className="text-gray-600 hover:text-charcoal font-medium transition-colors">
              Pricing
            </Link>
            <Link href="/contact" className="font-medium transition-colors" style={{ color: '#C9A84C' }}>
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

type FormState = {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  company: string;
  employees: string;
  message: string;
};

export default function ContactPage() {
  const [form, setForm] = useState<FormState>({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    company: '',
    employees: '',
    message: '',
  });
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Header */}
      <section className="pt-32 pb-16 px-4 sm:px-6 lg:px-8 text-center bg-gradient-to-br from-white via-gray-50 to-amber-50/30">
        <h1 className="text-5xl font-extrabold text-charcoal mb-4">Request a Demo</h1>
        <p className="text-xl text-gray-500 max-w-xl mx-auto">
          See LuxeForge in action with a personalized 30-minute walkthrough built around your workroom.
        </p>
      </section>

      {/* Two-column layout */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-16">

          {/* Left: Form */}
          <div>
            {submitted ? (
              <div className="text-center py-16">
                <CheckCircle size={64} style={{ color: '#C9A84C' }} className="mx-auto mb-6" />
                <h2 className="text-3xl font-bold text-charcoal mb-3">You&apos;re on the list!</h2>
                <p className="text-gray-500 text-lg">
                  Thanks, <strong>{form.firstName}</strong>! We&apos;ll reach out within 1 business day to schedule your demo.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label className="block text-sm font-semibold text-charcoal mb-1.5" htmlFor="firstName">
                      First Name <span style={{ color: '#C9A84C' }}>*</span>
                    </label>
                    <input
                      id="firstName"
                      name="firstName"
                      type="text"
                      required
                      value={form.firstName}
                      onChange={handleChange}
                      className="w-full px-4 py-3 border border-gray-200 rounded-lg text-charcoal placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all"
                      placeholder="Jane"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-charcoal mb-1.5" htmlFor="lastName">
                      Last Name <span style={{ color: '#C9A84C' }}>*</span>
                    </label>
                    <input
                      id="lastName"
                      name="lastName"
                      type="text"
                      required
                      value={form.lastName}
                      onChange={handleChange}
                      className="w-full px-4 py-3 border border-gray-200 rounded-lg text-charcoal placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all"
                      placeholder="Smith"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-charcoal mb-1.5" htmlFor="email">
                    Email Address <span style={{ color: '#C9A84C' }}>*</span>
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    value={form.email}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-charcoal placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all"
                    placeholder="jane@yourworkroom.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-charcoal mb-1.5" htmlFor="phone">
                    Phone Number
                  </label>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    value={form.phone}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-charcoal placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all"
                    placeholder="(555) 000-0000"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-charcoal mb-1.5" htmlFor="company">
                    Company / Workroom Name <span style={{ color: '#C9A84C' }}>*</span>
                  </label>
                  <input
                    id="company"
                    name="company"
                    type="text"
                    required
                    value={form.company}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-charcoal placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all"
                    placeholder="Luxe Drapery Studio"
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-charcoal mb-1.5" htmlFor="employees">
                    Number of Employees <span style={{ color: '#C9A84C' }}>*</span>
                  </label>
                  <select
                    id="employees"
                    name="employees"
                    required
                    value={form.employees}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-charcoal focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all bg-white"
                  >
                    <option value="" disabled>Select team size</option>
                    <option value="1-2">1–2 (Solo / Partner)</option>
                    <option value="3-10">3–10 (Small Studio)</option>
                    <option value="11-50">11–50 (Growing Team)</option>
                    <option value="50+">50+ (Enterprise)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-charcoal mb-1.5" htmlFor="message">
                    How can we help?
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    rows={4}
                    value={form.message}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg text-charcoal placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent transition-all resize-none"
                    placeholder="Tell us about your workroom and what you're looking to improve..."
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-4 rounded-md font-bold text-white text-lg transition-all hover:opacity-90 shadow-md"
                  style={{ backgroundColor: '#C9A84C' }}
                >
                  Request My Demo
                </button>
                <p className="text-center text-xs text-gray-400">
                  No credit card required. We&apos;ll contact you within 1 business day.
                </p>
              </form>
            )}
          </div>

          {/* Right: Info */}
          <div className="space-y-8">
            {/* Contact Info */}
            <div>
              <h2 className="text-2xl font-bold text-charcoal mb-5">Get in touch</h2>
              <div className="space-y-4">
                <div className="flex items-center gap-3 text-gray-600">
                  <Mail size={20} style={{ color: '#C9A84C' }} />
                  <span>hello@luxeforge.com</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <Phone size={20} style={{ color: '#C9A84C' }} />
                  <span>(888) 595-3674</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <MapPin size={20} style={{ color: '#C9A84C' }} />
                  <span>Los Angeles, CA (Remote-first team)</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <Clock size={20} style={{ color: '#C9A84C' }} />
                  <span>Mon–Fri, 9am–6pm PT</span>
                </div>
              </div>
            </div>

            {/* What to expect */}
            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100">
              <h3 className="font-bold text-charcoal text-lg mb-4">What to expect from your demo</h3>
              <ul className="space-y-4">
                {[
                  { step: '01', title: '30-Minute Walkthrough', desc: 'A focused demo of LuxeForge tailored to your workroom size and workflow.' },
                  { step: '02', title: 'Personalized Setup', desc: 'We\'ll pre-configure your pricing rules, markup settings, and branding before you start.' },
                  { step: '03', title: '14-Day Free Trial', desc: 'Walk away with full access — no credit card, no commitment, no pressure.' },
                ].map((item) => (
                  <li key={item.step} className="flex items-start gap-4">
                    <span
                      className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                      style={{ backgroundColor: '#C9A84C' }}
                    >
                      {item.step}
                    </span>
                    <div>
                      <div className="font-semibold text-charcoal text-sm">{item.title}</div>
                      <div className="text-gray-500 text-sm mt-0.5">{item.desc}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Testimonial */}
            <div
              className="rounded-2xl p-6 border-l-4"
              style={{ backgroundColor: '#FDF8EE', borderLeftColor: '#C9A84C' }}
            >
              <p className="text-gray-700 italic leading-relaxed mb-4">
                &ldquo;LuxeForge cut our quote turnaround from 3 days to 20 minutes. Our clients are amazed,
                and we&apos;ve increased our close rate by 35% since switching.&rdquo;
              </p>
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm"
                  style={{ backgroundColor: '#C9A84C' }}
                >
                  SL
                </div>
                <div>
                  <div className="font-semibold text-charcoal text-sm">Sarah L.</div>
                  <div className="text-gray-500 text-xs">Owner, Atelier Drapery Studio — Chicago, IL</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
