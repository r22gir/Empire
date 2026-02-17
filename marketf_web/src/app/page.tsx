'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { productAPI } from '@/lib/api';
import ProductCard from '@/components/product/ProductCard';
import CategoryNav from '@/components/layout/CategoryNav';

export default function HomePage() {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadFeaturedProducts() {
      try {
        const data = await productAPI.list({ page: 1, per_page: 8 });
        setFeaturedProducts(data.products || []);
      } catch (error) {
        console.error('Failed to load products:', error);
      } finally {
        setLoading(false);
      }
    }
    loadFeaturedProducts();
  }, []);

  return (
    <div>
      {/* Hero Section */}
      <section className="bg-gradient-to-r from-primary to-primary-dark text-white py-20">
        <div className="container">
          <div className="max-w-3xl">
            <h1 className="text-5xl font-bold mb-6">
              Buy & Sell with Only 8% Fees
            </h1>
            <p className="text-xl mb-8">
              Built-in shipping via ShipForge. Secure escrow payments. 
              Save $4.90 per $100 sale vs eBay.
            </p>
            <div className="flex gap-4">
              <Link href="/search" className="btn btn-secondary">
                Start Shopping
              </Link>
              <Link href="/seller/dashboard" className="btn bg-white text-primary hover:bg-gray-100">
                Start Selling
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Category Navigation */}
      <CategoryNav />

      {/* Featured Products */}
      <section className="py-12">
        <div className="container">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-3xl font-bold">🔥 Featured Deals</h2>
            <Link href="/search" className="text-primary hover:underline">
              See All →
            </Link>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="card animate-pulse">
                  <div className="bg-gray-200 h-48 mb-4 rounded"></div>
                  <div className="bg-gray-200 h-4 mb-2 rounded"></div>
                  <div className="bg-gray-200 h-4 w-2/3 rounded"></div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {featuredProducts.map((product: any) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Why MarketF */}
      <section className="bg-gray-50 py-16">
        <div className="container">
          <h2 className="text-3xl font-bold text-center mb-12">Why MarketF?</h2>
          <div className="grid md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-4xl mb-4">💰</div>
              <h3 className="text-xl font-bold mb-2">Only 8% Fees</h3>
              <p className="text-gray-600">
                vs eBay's 12.9% - save $4.90 per $100 sale
              </p>
            </div>
            <div className="text-center">
              <div className="text-4xl mb-4">📦</div>
              <h3 className="text-xl font-bold mb-2">Built-in Shipping</h3>
              <p className="text-gray-600">
                Integrated with ShipForge for easy shipping
              </p>
            </div>
            <div className="text-center">
              <div className="text-4xl mb-4">🔒</div>
              <h3 className="text-xl font-bold mb-2">Secure Escrow</h3>
              <p className="text-gray-600">
                Funds held until delivery confirmed
              </p>
            </div>
            <div className="text-center">
              <div className="text-4xl mb-4">⭐</div>
              <h3 className="text-xl font-bold mb-2">Verified Sellers</h3>
              <p className="text-gray-600">
                Ratings and reviews you can trust
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
