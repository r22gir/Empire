'use client';

import { useEffect, useState } from 'react';
import { fabricsApi } from '../api';
import { cartLines, clearCart, money } from '../cartStore';
import type { CartLine, ShippingEstimate } from '../types';

export default function CheckoutPage() {
  const [lines, setLines] = useState<CartLine[]>([]);
  const [shipping, setShipping] = useState<ShippingEstimate | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => setLines(cartLines()), []);

  useEffect(() => {
    if (!lines.length) return;
    fabricsApi
      .estimateShipping({ items: lines.map((line) => ({ product_id: line.product_id, yards: line.yards })) })
      .then(setShipping)
      .catch(() => setShipping(null));
  }, [lines]);

  const subtotal = lines.reduce((sum, line) => sum + line.yards * line.price_per_yard, 0);
  const ship = shipping?.shipping_total || 0;

  return (
    <main className="ff-main" id="cloth" style={{ paddingTop: 36 }}>
      <p className="ff-eyebrow">Checkout</p>
      <h1>Stripe test mode</h1>
      <p className="ff-note">
        Yardage is billed through the existing Empire quote → deposit pay-link
        path. Live Stripe keys are refused. Shipping is a pass-through of vendor
        freight plus handling — never free, no threshold.
      </p>
      {lines.length === 0 ? <p className="ff-empty">Nothing to settle.</p> : (
        <form
          className="ff-form"
          onSubmit={async (event) => {
            event.preventDefault();
            setBusy(true);
            setMessage('');
            try {
              const origin = window.location.origin;
              const result = await fabricsApi.checkout({
                name,
                email,
                phone,
                address,
                items: lines.map((line) => ({ product_id: line.product_id, yards: line.yards })),
                success_url: `${origin}/fine-fabrics/checkout?paid=1`,
                cancel_url: `${origin}/fine-fabrics/checkout?cancel=1`,
              });
              const url = (result.pay_link as { checkout_url?: string } | undefined)?.checkout_url;
              clearCart();
              if (url) {
                window.location.href = url;
                return;
              }
              const charged = result.shipping_total != null ? ` Shipping collected: ${money(Number(result.shipping_total))}.` : '';
              setMessage(
                result.pay_link
                  ? `Quote ${result.quote_id} is ready.${charged} Stripe is not configured in this environment — no live charge was made.`
                  : `Order recorded in test mode.${charged}`,
              );
            } catch (err) {
              setMessage(err instanceof Error ? err.message : 'Checkout failed');
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="ff-totals">
            <p>Subtotal {money(subtotal)}</p>
            <p>Vendor shipping (pass-through) {shipping ? money(ship) : '…'}</p>
            <p><strong>Due {shipping ? money(subtotal + ship) : '…'}</strong></p>
          </div>
          <label>Name<input required value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label>Email<input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>Phone<input value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
          <label>Address<textarea value={address} onChange={(e) => setAddress(e.target.value)} rows={3} /></label>
          <button className="ff-btn" type="submit" disabled={busy}>Pay deposit (test)</button>
        </form>
      )}
      {message ? <p className="ff-banner" style={{ marginTop: 18 }}>{message}</p> : null}
    </main>
  );
}
