'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState } from 'react';
import { fabricsApi, productTitle } from '../api';
import { MOCKUP_ITEMS } from '../seeOnItem';
import type { FabricProduct } from '../types';

function QuoteBody() {
  const params = useSearchParams();
  const productId = Number(params.get('product_id') || 0);
  const item = params.get('item') || 'pillow';
  const [product, setProduct] = useState<FabricProduct | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!productId) return;
    fabricsApi.product(productId).then(setProduct).catch(() => setStatus('This cloth is not offered online.'));
  }, [productId]);

  const label = MOCKUP_ITEMS.find((entry) => entry.id === item)?.label || item;

  return (
    <main className="ff-main" id="cloth" style={{ paddingTop: 36 }}>
      <p className="ff-eyebrow">Workroom quote</p>
      <h1>Get a quote for this item</h1>
      <p className="ff-note">
        {product
          ? `${productTitle(product)} · Empire ${product.empire_code} on a ${label.toLowerCase()}.`
          : 'Choose a fabric from the store, then return here.'}
        {' '}Routes to Empire Workroom / LeadForge when that intake is up; otherwise the request is stored as a stub.
      </p>
      <form
        className="ff-form"
        onSubmit={async (event) => {
          event.preventDefault();
          try {
            const result = await fabricsApi.itemQuote({
              product_id: productId,
              item_type: item,
              name,
              email,
              phone,
              message,
            });
            setStatus(String(result.message || 'Request received.'));
          } catch (err) {
            setStatus(err instanceof Error ? err.message : 'Could not send this quote request.');
          }
        }}
      >
        <label>Name<input required value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label>Email<input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>Phone<input value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
        <label>Notes<textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={4} /></label>
        <button className="ff-btn" type="submit" disabled={!productId}>Request quote</button>
      </form>
      {status ? <p className="ff-banner" style={{ marginTop: 18 }}>{status}</p> : null}
    </main>
  );
}

export default function QuotePage() {
  return (
    <Suspense fallback={<main className="ff-main">Loading…</main>}>
      <QuoteBody />
    </Suspense>
  );
}
