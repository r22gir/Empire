'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { swatchSrc } from '../api';
import { cartLines, money, setYards } from '../cartStore';
import type { CartLine } from '../types';

export default function CartPage() {
  const [lines, setLines] = useState<CartLine[]>([]);

  useEffect(() => {
    const sync = () => setLines(cartLines());
    sync();
    window.addEventListener('ff-cart', sync);
    return () => window.removeEventListener('ff-cart', sync);
  }, []);

  const subtotal = lines.reduce((sum, line) => sum + line.yards * line.price_per_yard, 0);

  return (
    <main className="ff-main" id="cloth" style={{ paddingTop: 36 }}>
      <p className="ff-eyebrow">Cart</p>
      <h1>By the yard</h1>
      {lines.length === 0 ? (
        <p className="ff-empty">The cart is empty. <Link href="/fine-fabrics">Return to the cloth.</Link></p>
      ) : (
        <>
          <div className="ff-lines">
            {lines.map((line) => (
              <div className="ff-line" key={line.product_id}>
                <img src={swatchSrc({ image_url: line.image_url, has_owner_photo: Boolean(line.image_url) })} alt="" />
                <div>
                  <strong>{line.pattern}</strong>
                  <div className="ff-note">{line.color} · {line.empire_code}</div>
                  <div className="ff-note">{money(line.price_per_yard)} / yd</div>
                </div>
                <div>
                  <input
                    className="ff-qty"
                    type="number"
                    min={0}
                    step={0.5}
                    value={line.yards}
                    onChange={(e) => setYards(line.product_id, Number(e.target.value))}
                  />
                  <div className="ff-note">{money(line.yards * line.price_per_yard)}</div>
                </div>
              </div>
            ))}
          </div>
          <p>Subtotal {money(subtotal)}</p>
          <div className="ff-actions">
            <Link className="ff-btn" href="/fine-fabrics/checkout">Checkout (Stripe test)</Link>
            <Link className="ff-btn-ghost" href="/fine-fabrics/samples">Request samples instead</Link>
          </div>
        </>
      )}
    </main>
  );
}
