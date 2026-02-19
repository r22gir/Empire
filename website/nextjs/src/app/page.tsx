import Link from 'next/link';
import Navbar from '@/components/Navbar';
import Hero from '@/components/Hero';
import Features from '@/components/Features';
import Testimonials from '@/components/Testimonials';
import HowItWorks from '@/components/HowItWorks';
import Pricing from '@/components/Pricing';
import FAQ from '@/components/FAQ';
import CTA from '@/components/CTA';
import ProductsShowcase from '@/components/ProductsShowcase';
import ServicesShowcase from '@/components/ServicesShowcase';

export default function Home() {
  return (
    <main>
      <Navbar />
      <Hero />
      
      {/* Quick Links Section */}
      <section className="py-16 bg-gradient-to-br from-primary-700 to-primary-800 text-white">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-4xl font-bold mb-6">Get Started Today</h2>
            <p className="text-xl mb-12 opacity-90">
              Your Complete Reselling Business in a Box
            </p>

            <div className="grid md:grid-cols-2 gap-6 mb-12">
              <Link
                href="/setup"
                className="bg-white text-primary-700 font-bold py-8 px-6 rounded-xl hover:shadow-2xl transition-shadow"
              >
                <h3 className="text-2xl mb-2">Setup Portal</h3>
                <p className="text-sm opacity-75">
                  Activate your hardware bundle with a license key
                </p>
              </Link>

              <Link
                href="/bundles"
                className="bg-accent-500 text-white font-bold py-8 px-6 rounded-xl hover:shadow-2xl transition-shadow"
              >
                <h3 className="text-2xl mb-2">Hardware Bundles</h3>
                <p className="text-sm opacity-90">
                  Pre-order complete bundles shipping March 2026
                </p>
              </Link>
            </div>

            <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-xl p-8">
              <h3 className="text-xl font-semibold mb-4">What&apos;s Included:</h3>
              <ul className="text-left max-w-2xl mx-auto space-y-2">
                <li>✅ Professional reselling phone (factory sealed)</li>
                <li>✅ MarketForge Pro subscription (12 months)</li>
                <li>✅ QR code instant setup</li>
                <li>✅ Secure crypto wallet (Seeker models)</li>
                <li>✅ AI-powered listing tools</li>
                <li>✅ Multi-marketplace integration</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <Features />
      <ProductsShowcase />
      <ServicesShowcase />
      <Testimonials />
      <HowItWorks />
      <Pricing />
      <FAQ />
      <CTA />
    </main>
  );
}