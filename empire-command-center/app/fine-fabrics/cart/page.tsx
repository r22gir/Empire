'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { fabricsApi, swatchSrc } from '../api';
import { cartLines, money, setYards } from '../cartStore';
import type { CartLine, ShippingEstimate } from '../types';

export default function CartPage() {
  const [lines, setLines] = useState<CartLine[]>([]);
  const [shipping, setShipping] = useState<ShippingEstimate | null>(null);

  useEffect(() => {
    const sync = () => setLines(cartLines());
    sync();
    window.addEventListener('ff-cart', sync);
    return () => window.removeEventListener('ff-cart', sync);
  }, []);

  useEffect(() => {
    if (!lines.length) {
      setShipping(null);
      return;
    }
    fabricsApi
      .estimateShipping({ items: lines.map((line) => ({ product_id: line.product_id, yards: line.yards })) })
      .then(setShipping)
      .catch(() => setShipping(null));
  }, [lines]);

  const subtotal = lines.reduce((sum, line) => sum + line.yards * line.price_per_yard, 0);
  const ship = shipping?.shipping_total || 0;
  const total = subtotal + ship;

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
                <img src={swatchSrc({ image_url: line.image_url, has_owner_photo: Boolean(line.image_url), placeholder: !line.image_url })} alt="" />
                <div>
                  <strong>{line.display_title || line.pattern}</strong>
                  <div className="ff-note">{line.sku ? `SKU ${line.sku}` : line.color} · Empire {line.empire_code}</div>
                  <div className="ff-note">{money(line.price_per_yard)} / {line.unit_label || 'yd'}</div>
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
          <div className="ff-totals">
            <p>Subtotal {money(subtotal)}</p>
            <p>Vendor shipping (pass-through) {shipping ? money(ship) : '…'}</p>
            {shipping?.handling_total ? <p className="ff-note">Includes handling {money(shipping.handling_total)}</p> : null}
            <p><strong>Total {shipping ? money(total) : '…'}</strong></p>
            <p className="ff-note">Shipping is whatever the mill charges us, plus handling. It is never free. Samples are charged.</p>
          </div>
          <div className="ff-actions">
            <Link className="ff-btn" href="/fine-fabrics/checkout">Checkout (Stripe test)</Link>
            <Link className="ff-btn-ghost" href="/fine-fabrics/samples">Request samples instead</Link>
          </div>
        </>
      )}
    </main>
  );
}
