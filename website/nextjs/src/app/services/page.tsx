import { Metadata } from 'next';
import Navbar from '@/components/Navbar';
import ServiceCard from '@/components/ServiceCard';
import LegalFooter from '@/components/LegalFooter';
import { SERVICES } from '@/lib/constants';

export const metadata: Metadata = {
  title: 'Services - EmpireBox',
  description: 'Explore all EmpireBox services: EmpireAssist AI, VA Telehealth, and the Zero to Hero Program.',
};

export default function ServicesPage() {
  return (
    <main>
      <Navbar />
      <div className="min-h-screen bg-gray-50">
        <section className="bg-accent-500 text-white py-16">
          <div className="max-w-4xl mx-auto px-4 text-center">
            <h1 className="text-4xl font-heading font-bold mb-4">Our Services</h1>
            <p className="text-xl opacity-90">
              Expert support and education to help your reselling business thrive.
            </p>
          </div>
        </section>

        <section className="py-16 max-w-7xl mx-auto px-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {SERVICES.map((service) => (
              <ServiceCard
                key={service.id}
                icon={service.icon}
                name={service.name}
                tagline={service.tagline}
                price={service.price}
                href={service.href}
              />
            ))}
          </div>
        </section>

        <section className="py-8 max-w-4xl mx-auto px-4">
          <LegalFooter />
        </section>
      </div>
    </main>
  );
}
