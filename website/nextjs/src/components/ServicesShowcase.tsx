import Link from 'next/link';
import ServiceCard from '@/components/ServiceCard';
import { SERVICES } from '@/lib/constants';

export default function ServicesShowcase() {
  return (
    <section className="py-20 bg-white">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">Our Services</h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Expert support, education, and specialized services to accelerate your success.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
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
        <div className="text-center">
          <Link
            href="/services"
            className="inline-block bg-accent-500 text-white font-bold py-3 px-8 rounded-lg hover:bg-orange-600 transition-colors"
          >
            View All Services
          </Link>
        </div>
      </div>
    </section>
  );
}
