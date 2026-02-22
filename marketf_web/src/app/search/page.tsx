'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import ProductGrid from '@/components/product/ProductGrid';
import { productAPI } from '@/lib/api';

function SearchResults() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  const [products, setProducts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function search() {
      if (!query) { setLoading(false); return; }
      try {
        const data = await productAPI.list({ q: query, page: 1, per_page: 24 });
        setProducts((data as any).products || []);
        setTotal((data as any).total || 0);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setLoading(false);
      }
    }
    search();
  }, [query]);

  if (loading) return <div className="p-8 text-center">Searching...</div>;
  if (!query) return <div className="p-8 text-center">Enter a search term</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-4">Results for "{query}"</h1>
      <p className="text-gray-600 mb-6">{total} items found</p>
      <ProductGrid products={products} />
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center">Loading...</div>}>
      <SearchResults />
    </Suspense>
  );
}
