'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { fabricsApi, productTitle, swatchSrc } from './api';
import { addToCart, money } from './cartStore';
import SeeOnItem from './SeeOnItem';
import type { FabricProduct } from './types';

export default function ProductClient({ product }: { product: FabricProduct }) {
  const router = useRouter();
  const [yards, setYards] = useState(2);
  const [preview, setPreview] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const unit = product.unit_label || 'yard';
  const title = productTitle(product);

  const specs: Array<[string, string]> = [];
  if (product.brand) specs.push(['Brand', product.brand]);
  if (product.sku) specs.push(['Vendor SKU', product.sku]);
  specs.push(['Pattern', product.pattern]);
  specs.push(['Color', product.color || '—']);
  if (product.product_type === 'collection') specs.push(['Type', 'Collection / book']);
  specs.push(
    ['Empire code', product.empire_code],
    ['Width', product.width || '—'],
    ['Content', product.content || '—'],
    ['Repeat', product.repeat || '—'],
    ['Durability', product.durability || '—'],
    ['Care', product.care || '—'],
    ['Price', `${money(product.price_per_unit || product.price_per_yard)} per ${unit}`],
  );

  return (
    <main className="ff-main" id="cloth" style={{ paddingTop: 36 }}>
      <div className="ff-product">
        <div className="ff-swatch">
          <img src={swatchSrc(product)} alt={title} />
        </div>
        <div>
          <p className="ff-eyebrow">{product.category}</p>
          <h1>{title}</h1>
          <p className="ff-note">
            {product.sku ? `Vendor SKU ${product.sku}` : product.color}
            {product.empire_code ? ` · Empire ${product.empire_code}` : ''}
          </p>
          {product.description ? <p className="ff-note">{product.description}</p> : null}
          <p style={{ fontSize: '1.4rem', margin: '16px 0 0' }}>
            {money(product.price_per_unit || product.price_per_yard)} <span className="ff-note">/ {unit}</span>
          </p>
          <ul className="ff-specs">
            {specs.map(([label, value]) => (
              <li key={label}><span>{label}</span><strong>{value}</strong></li>
            ))}
          </ul>
          <label className="ff-note">
            {unit === 'yard' ? 'Yards' : unit}
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
          {product.placeholder ? (
            <p className="ff-note" style={{ marginTop: 16 }}>
              Placeholder swatch — mill or owner photograph has not been added yet.
            </p>
          ) : null}
          <p className="ff-note" style={{ marginTop: 16 }}>
            Shipping is a pass-through of vendor freight plus handling. It is never free.
          </p>
        </div>
      </div>
      <SeeOnItem product={product} />
    </main>
  );
}
