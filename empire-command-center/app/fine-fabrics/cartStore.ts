'use client';

import type { CartLine, FabricProduct } from './types';

const KEY = 'empire-fine-fabrics-cart';

function read(): CartLine[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function write(lines: CartLine[]) {
  window.localStorage.setItem(KEY, JSON.stringify(lines));
  window.dispatchEvent(new Event('ff-cart'));
}

export function cartLines(): CartLine[] {
  return read();
}

export function cartCount(): number {
  return read().reduce((sum, line) => sum + line.yards, 0);
}

export function addToCart(product: FabricProduct, yards: number) {
  const lines = read();
  const existing = lines.find((line) => line.product_id === product.id);
  if (existing) existing.yards = Number((existing.yards + yards).toFixed(2));
  else {
    lines.push({
      product_id: product.id,
      yards,
      pattern: product.pattern,
      color: product.color,
      empire_code: product.empire_code,
      price_per_yard: product.price_per_yard,
      image_url: product.image_url,
    });
  }
  write(lines);
}

export function setYards(productId: number, yards: number) {
  const lines = read().map((line) =>
    line.product_id === productId ? { ...line, yards } : line,
  ).filter((line) => line.yards > 0);
  write(lines);
}

export function clearCart() {
  write([]);
}

export function money(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}
