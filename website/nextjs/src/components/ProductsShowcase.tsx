import Link from 'next/link';
import ProductCard from '@/components/ProductCard';
import { PRODUCTS } from '@/lib/constants';

export default function ProductsShowcase() {
  return (
    <section className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-heading font-bold text-gray-900 mb-4">Our Products</h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Everything you need to run a successful reselling business — all in one ecosystem.
          </p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
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
        <div className="text-center">
          <Link
            href="/products"
            className="inline-block bg-primary-700 text-white font-bold py-3 px-8 rounded-lg hover:bg-primary-800 transition-colors"
          >
            View All Products
          </Link>
        </div>
      </div>
    </section>
  );
}
