import { Metadata } from 'next';
import Navbar from '@/components/Navbar';
import ProductCard from '@/components/ProductCard';
import LegalFooter from '@/components/LegalFooter';
import { PRODUCTS } from '@/lib/constants';

export const metadata: Metadata = {
  title: 'Products - EmpireBox',
  description: 'Explore all EmpireBox products: MarketForge, LeadForge, LuxeForge, EMPIRE Token, and EMPIRE License NFT.',
};

export default function ProductsPage() {
  return (
    <main>
      <Navbar />
      <div className="min-h-screen bg-gray-50">
        <section className="bg-primary-700 text-white py-16">
          <div className="max-w-4xl mx-auto px-4 text-center">
            <h1 className="text-4xl font-heading font-bold mb-4">Our Products</h1>
            <p className="text-xl opacity-90">
              Powerful tools built for resellers at every stage of growth.
            </p>
          </div>
        </section>

        <section className="py-16 max-w-7xl mx-auto px-4">
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {PRODUCTS.map((product) => (
              <ProductCard
                key={product.id}
                icon={product.icon}
                name={product.name}
                tagline={product.tagline}
                price={product.price}
                href={product.href}
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
