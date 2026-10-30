'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { fabricsApi, swatchSrc } from '../api';
import { addToCart, money } from '../cartStore';
import type { FabricProduct } from '../types';

export default function FabricProductPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [product, setProduct] = useState<FabricProduct | null>(null);
  const [error, setError] = useState('');
  const [yards, setYards] = useState(2);
  const [preview, setPreview] = useState<string>('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fabricsApi.product(params.id)
      .then(setProduct)
      .catch(() => setError('This cloth is not offered online.'));
  }, [params.id]);

  if (error) return <main className="ff-main"><p className="ff-empty">{error}</p></main>;
  if (!product) return <main className="ff-main"><p className="ff-empty">Loading…</p></main>;

  const specs = [
    ['Pattern', product.pattern],
    ['Color', product.color],
    ['Empire code', product.empire_code],
    ['Width', product.width || '—'],
    ['Content', product.content || '—'],
    ['Repeat', product.repeat || '—'],
    ['Durability', product.durability || '—'],
    ['Care', product.care || '—'],
    ['Price', `${money(product.price_per_yard)} per yard`],
  ];
  if (product.brand) specs.splice(3, 0, ['Brand', product.brand]);

  return (
    <main className="ff-main" id="cloth" style={{ paddingTop: 36 }}>
      <div className="ff-product">
        <div className="ff-swatch">
          <img src={swatchSrc(product)} alt={`${product.pattern} ${product.color}`} />
        </div>
        <div>
          <p className="ff-eyebrow">{product.category}</p>
          <h1>{product.pattern}</h1>
          <p className="ff-note">{product.color} · {product.empire_code}</p>
          <p style={{ fontSize: '1.4rem', margin: '16px 0 0' }}>{money(product.price_per_yard)} <span className="ff-note">/ yard</span></p>
          <ul className="ff-specs">
            {specs.map(([label, value]) => (
              <li key={label}><span>{label}</span><strong>{value}</strong></li>
            ))}
          </ul>
          <label className="ff-note">
            Yards
            <input
              className="ff-qty"
              type="number"
              min={0.5}
              step={0.5}
              value={yards}
              onChange={(e) => setYards(Number(e.target.value))}
              style={{ display: 'block', marginTop: 6 }}
            />
          </label>
          <div className="ff-actions">
            <button
              className="ff-btn"
              type="button"
              onClick={() => {
                addToCart(product, yards);
                router.push('/fine-fabrics/cart');
              }}
            >
              Add to cart
            </button>
            <button
              className="ff-btn-ghost"
              type="button"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  const result = await fabricsApi.preview(product.id);
                  if (result.stub) {
                    setPreview(String(result.todo || 'Preview stub'));
                  } else {
                    setPreview('Handed to the drawing engine. Open the workroom mockup to continue.');
                  }
                } catch (err) {
                  setPreview(err instanceof Error ? err.message : 'Preview unavailable');
                } finally {
                  setBusy(false);
                }
              }}
            >
              Preview on drawing
            </button>
            <a className="ff-btn-ghost" href={`/fine-fabrics/samples?id=${product.id}`}>Request sample</a>
          </div>
          {preview ? <p className="ff-banner" style={{ marginTop: 18 }}>{preview}</p> : null}
          {!product.has_owner_photo ? (
            <p className="ff-note" style={{ marginTop: 16 }}>
              Placeholder swatch — owner photograph has not been added. Vendor images are never used.
            </p>
          ) : null}
        </div>
      </div>
    </main>
  );
}
