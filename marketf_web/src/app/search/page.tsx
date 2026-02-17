'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { productAPI } from '@/lib/api';
import ProductGrid from '@/components/product/ProductGrid';

export default function SearchPage() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    async function searchProducts() {
      setLoading(true);
      try {
        const data = await productAPI.list({ q: query, page: 1, per_page: 24 });
        setProducts(data.products || []);
        setTotal(data.total || 0);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setLoading(false);
      }
    }
    searchProducts();
  }, [query]);

  return (
    <div className="container py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">
          {query ? `Search results for "${query}"` : 'Browse Products'}
        </h1>
        <p className="text-gray-600">{total} items found</p>
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
        <ProductGrid products={products} />
      )}
    </div>
  );
}
