'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { fabricsApi } from '../api';
import { money } from '../cartStore';
import type { FabricProduct, ShippingEstimate } from '../types';

function SamplesBody() {
  const params = useSearchParams();
  const preset = params.get('id');
  const [products, setProducts] = useState<FabricProduct[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [shipping, setShipping] = useState<ShippingEstimate | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    fabricsApi.catalog().then((data) => {
      setProducts(data.products);
      if (preset) setSelected([Number(preset)]);
    }).catch(() => setMessage('Catalog unavailable'));
  }, [preset]);

  useEffect(() => {
    if (!selected.length) {
      setShipping(null);
      return;
    }
    fabricsApi
      .estimateShipping({ sample_ids: selected })
      .then(setShipping)
      .catch(() => setShipping(null));
  }, [selected]);

  return (
    <main className="ff-main" id="cloth" style={{ paddingTop: 36 }}>
      <p className="ff-eyebrow">Samples</p>
      <h1>A clip of the cloth</h1>
      <p className="ff-note">
        Request cuttings. Sample shipping is a pass-through of vendor freight plus
        handling — never free. Empire confirms by hand — no customer email is sent automatically.
      </p>
      <form
        className="ff-form"
        onSubmit={async (event) => {
          event.preventDefault();
          try {
            const result = await fabricsApi.samples({
              name, email, phone, notes, product_ids: selected,
            });
            setMessage(String(result.message || 'Request received.'));
          } catch (err) {
            setMessage(err instanceof Error ? err.message : 'Request failed');
          }
        }}
      >
        <fieldset style={{ border: '1px solid var(--ff-line)', padding: 12 }}>
          <legend className="ff-note">Fabrics</legend>
          {products.map((product) => (
            <label key={product.id} className="ff-check">
              <input
                type="checkbox"
                checked={selected.includes(product.id)}
                onChange={(e) => {
                  setSelected((cur) =>
                    e.target.checked ? [...cur, product.id] : cur.filter((id) => id !== product.id),
                  );
                }}
              />
              {' '}{product.pattern} {product.color} · {product.empire_code}
            </label>
          ))}
        </fieldset>
        {shipping ? (
          <div className="ff-totals">
            <p>Sample shipping {money(shipping.shipping_total)}</p>
            <p className="ff-note">{shipping.note}</p>
          </div>
        ) : null}
        <label>Name<input required value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label>Email<input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>Phone<input value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
        <label>Notes<textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} /></label>
        <button className="ff-btn" type="submit">Request samples</button>
      </form>
      {message ? <p className="ff-banner" style={{ marginTop: 18 }}>{message}</p> : null}
    </main>
  );
}

export default function SamplesPage() {
  return (
    <Suspense fallback={<main className="ff-main">Loading…</main>}>
      <SamplesBody />
    </Suspense>
  );
}
