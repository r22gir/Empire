import Navbar from '@/components/Navbar';
import Pricing from '@/components/Pricing';
import CTA from '@/components/CTA';
import Footer from '@/components/Footer';

export const metadata = {
  title: 'Pricing - EmpireBox',
  description: 'Simple, transparent pricing for resellers. Start free, scale as you grow.',
};

export default function PricingPage() {
  return (
    <main>
      <Navbar />
      <section className="py-20 bg-light">
        <div className="container mx-auto px-4 text-center mb-12">
          <h1 className="mb-4">Choose Your Plan</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Start with a free trial, then choose the plan that fits your business. 
            No hidden fees, cancel anytime.
          </p>
        </div>
      </section>
      <Pricing />
      <CTA />
      <Footer />
    </main>
  );
}
