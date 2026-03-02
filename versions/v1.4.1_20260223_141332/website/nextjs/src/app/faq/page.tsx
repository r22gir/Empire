import Navbar from '@/components/Navbar';
import FAQ from '@/components/FAQ';
import CTA from '@/components/CTA';
import Footer from '@/components/Footer';

export const metadata = {
  title: 'FAQ - EmpireBox',
  description: 'Frequently asked questions about EmpireBox, the operating system for resellers.',
};

export default function FAQPage() {
  return (
    <main>
      <Navbar />
      <section className="py-20 bg-light">
        <div className="container mx-auto px-4 text-center mb-12">
          <h1 className="mb-4">Frequently Asked Questions</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Got questions? We&apos;ve got answers. Can&apos;t find what you&apos;re looking for? 
            Email us at hello@empirebox.com
          </p>
        </div>
      </section>
      <FAQ />
      <CTA />
      <Footer />
    </main>
  );
}
