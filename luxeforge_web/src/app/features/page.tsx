import Link from 'next/link';
import { MessageSquare, Camera, FileText, LayoutDashboard, Users, BookOpen, ArrowRight } from 'lucide-react';

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
            <Link href="/features" className="font-medium transition-colors" style={{ color: '#C9A84C' }}>
              Features
            </Link>
            <Link href="/pricing" className="text-gray-600 hover:text-charcoal font-medium transition-colors">
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

const featureSections = [
  {
    icon: MessageSquare,
    title: 'AI Conversational Project Intake',
    tagline: 'Never miss a detail again',
    description:
      'LuxeForge replaces your intake forms with a natural conversation. The AI asks exactly the right questions — room dimensions, fabric preferences, hardware selections, lining options — and auto-populates every field of your quote. Clients feel heard, and you get complete data every time.',
    highlights: [
      'Chat-based intake that connects with clients naturally',
      'Auto-populates all quote fields from conversation',
      'Handles complex multi-window, multi-room projects',
      'Available 24/7 — clients can start at their own pace',
    ],
    reverse: false,
  },
  {
    icon: Camera,
    title: 'Photo-Based Window Measurements',
    tagline: 'Measure from anywhere, on any device',
    description:
      'Upload a photo of the window from any smartphone or camera. Our computer vision AI analyzes the image, identifies the frame and surrounding architecture, and returns accurate measurements in seconds. Reduces costly re-measure visits and measurement errors that delay production.',
    highlights: [
      'Works with any device camera — phone, tablet, DSLR',
      'AI identifies window frame and extracts dimensions',
      'Flags low-confidence measurements for manual review',
      'Reduces on-site errors by up to 80%',
    ],
    reverse: true,
  },
  {
    icon: FileText,
    title: 'Auto-Quote Generation',
    tagline: 'Professional quotes in seconds',
    description:
      'Once intake is complete, LuxeForge generates a polished, itemized quote instantly. Apply your custom per-width drapery pricing, fabric and hardware markup rules, and installation rates. Clients receive a branded PDF with a one-click approval and 50% deposit payment link.',
    highlights: [
      'Per-width drapery pricing ($95–$150/width)',
      'Configurable fabric markup (30–50%) and hardware markup (50%)',
      'Branded PDF export with your logo',
      'Client approval workflow with e-signature and deposit',
    ],
    reverse: false,
  },
  {
    icon: LayoutDashboard,
    title: 'Production Queue Management',
    tagline: 'Keep your workroom on track',
    description:
      'A visual kanban board gives you complete visibility over every project in production. Drag and drop to prioritize by deadline, assign jobs to specific workroom staff, and track fabric and hardware order status — all in one place. No more lost sticky notes or missed deadlines.',
    highlights: [
      'Visual kanban: Intake → Ordered → In Production → Ready → Installed',
      'Assign tasks to workroom staff with deadlines',
      'Track fabric and hardware order status per project',
      'Deadline alerts and overdue notifications',
    ],
    reverse: true,
  },
  {
    icon: Users,
    title: 'Client Portal',
    tagline: 'A premium experience for every client',
    description:
      'Give clients a branded, secure portal where they can review estimates, approve projects with an e-signature, pay their deposit, and track the status of their order through installation. Reduce back-and-forth emails and give your business a high-end, professional image.',
    highlights: [
      'Branded with your workroom logo and colors',
      'Estimate review and one-click e-signature approval',
      'Secure 50% deposit payment via Stripe',
      'Real-time project status updates through installation',
    ],
    reverse: false,
  },
  {
    icon: BookOpen,
    title: 'Fabric & Hardware Catalog Integration',
    tagline: 'Order without leaving LuxeForge',
    description:
      'Browse live fabric and hardware pricing directly from Rowley Company and Kravet inside LuxeForge. Add items to your project, apply your markup automatically, and place orders with one click. No more switching between tabs or manually entering item codes.',
    highlights: [
      'Live integration with Rowley Co and Kravet catalogs',
      'Real-time pricing with automatic markup applied',
      'One-click order submission per project',
      'Order history and tracking within LuxeForge',
    ],
    reverse: true,
  },
];

export default function FeaturesPage() {
  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Header */}
      <section className="pt-32 pb-16 px-4 sm:px-6 lg:px-8 text-center bg-gradient-to-br from-white via-gray-50 to-amber-50/30">
        <h1 className="text-5xl font-extrabold text-charcoal mb-4">
          Powerful Features for Every Workroom
        </h1>
        <p className="text-xl text-gray-500 max-w-2xl mx-auto">
          Every tool you need — from first client contact to final installation invoice — designed for the luxury custom window treatment industry.
        </p>
      </section>

      {/* Feature Sections */}
      <div className="py-8">
        {featureSections.map((feature, index) => {
          const Icon = feature.icon;
          return (
            <section
              key={feature.title}
              className={`py-20 px-4 sm:px-6 lg:px-8 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}
            >
              <div className="max-w-6xl mx-auto">
                <div className={`flex flex-col ${feature.reverse ? 'lg:flex-row-reverse' : 'lg:flex-row'} gap-16 items-center`}>
                  {/* Text */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-4">
                      <div
                        className="w-10 h-10 rounded-lg flex items-center justify-center"
                        style={{ backgroundColor: '#FDF8EE' }}
                      >
                        <Icon size={20} style={{ color: '#C9A84C' }} />
                      </div>
                      <span className="text-sm font-semibold uppercase tracking-wider" style={{ color: '#A07830' }}>
                        {feature.tagline}
                      </span>
                    </div>
                    <h2 className="text-3xl sm:text-4xl font-bold text-charcoal mb-4">{feature.title}</h2>
                    <p className="text-gray-500 leading-relaxed mb-8">{feature.description}</p>
                    <ul className="space-y-3">
                      {feature.highlights.map((h) => (
                        <li key={h} className="flex items-start gap-3 text-sm text-gray-700">
                          <span
                            className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-white text-xs font-bold"
                            style={{ backgroundColor: '#C9A84C' }}
                          >
                            ✓
                          </span>
                          {h}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {/* Visual placeholder */}
                  <div className="flex-1 w-full">
                    <div
                      className="w-full h-72 rounded-2xl flex items-center justify-center border border-gray-100"
                      style={{ background: 'linear-gradient(135deg, #FDF8EE 0%, #F5E6C8 100%)' }}
                    >
                      <Icon size={64} style={{ color: '#C9A84C', opacity: 0.4 }} />
                    </div>
                  </div>
                </div>
              </div>
            </section>
          );
        })}
      </div>

      {/* CTA */}
      <section
        className="py-20 px-4 sm:px-6 lg:px-8 text-center"
        style={{ background: 'linear-gradient(135deg, #2C2C2C 0%, #1A1A1A 100%)' }}
      >
        <h2 className="text-4xl font-extrabold text-white mb-4">See it all in action</h2>
        <p className="text-xl text-gray-300 mb-8 max-w-xl mx-auto">
          Book a 30-minute personalized demo and we&apos;ll walk through every feature with your real workflow.
        </p>
        <Link
          href="/contact"
          className="inline-flex items-center gap-2 px-8 py-4 rounded-md font-semibold text-charcoal text-lg transition-all hover:opacity-90"
          style={{ backgroundColor: '#C9A84C' }}
        >
          Request a Demo <ArrowRight size={20} />
        </Link>
      </section>

      <Footer />
    </div>
  );
}
