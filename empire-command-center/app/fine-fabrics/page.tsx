'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { fabricsApi, swatchSrc } from './api';
import { money } from './cartStore';
import type { FabricProduct } from './types';

const CATS = ['Upholstery', 'Drapery', 'Outdoor', 'Other'] as const;

function CatalogBody() {
  const params = useSearchParams();
  const cat = params.get('cat') || '';
  const [products, setProducts] = useState<FabricProduct[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setProducts(null);
    fabricsApi.catalog(cat || undefined)
      .then((data) => setProducts(data.products))
      .catch((err) => setError(err.message || 'Catalog unavailable'));
  }, [cat]);

  return (
    <>
      <section className="ff-hero">
        <p className="ff-eyebrow">Empire Fine Fabrics</p>
        <h1>Cloth chosen <em>with care</em></h1>
        <p>
          Upholstery, drapery, and outdoor goods sold by the yard. Prices are
          Empire retail — vendor costs stay in the workroom. Swatches are
          owner photographs only.
        </p>
      </section>
      <main className="ff-main" id="cloth">
        <div className="ff-filters" role="tablist" aria-label="Categories">
          <Link className={!cat ? 'is-on' : ''} href="/fine-fabrics">All</Link>
          {CATS.map((name) => (
            <Link key={name} className={cat === name ? 'is-on' : ''} href={`/fine-fabrics?cat=${name}`}>
              {name}
            </Link>
          ))}
        </div>
        {error ? <div className="ff-banner">{error}</div> : null}
        {products && products.length === 0 ? (
          <p className="ff-empty">No cloth in this room yet. Some mills stay trade-only until the founder opens them for online sale.</p>
        ) : null}
        <div className="ff-grid">
          {(products || []).map((product) => (
            <Link key={product.id} className="ff-card" href={`/fine-fabrics/${product.id}`}>
              <figure>
                <img src={swatchSrc(product)} alt={`${product.pattern} ${product.color}`} />
              </figure>
              <figcaption>
                <strong>{product.pattern}</strong>
                <div className="meta">{product.color} · {product.empire_code}</div>
                <div className="meta">{product.category}{product.brand ? ` · ${product.brand}` : ''}</div>
                <div className="price">{money(product.price_per_unit || product.price_per_yard)} / {product.unit_label || 'yd'}</div>
              </figcaption>
            </Link>
          ))}
        </div>
      </main>
    </>
  );
}

export default function FineFabricsCatalogPage() {
  return (
    <Suspense fallback={<main className="ff-main">Loading cloth…</main>}>
      <CatalogBody />
    </Suspense>
  );
}
