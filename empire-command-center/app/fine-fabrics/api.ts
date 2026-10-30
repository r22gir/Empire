import type { FabricProduct } from './types';

function apiBase(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
  }
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
  }
  return `${window.location.origin}/api/v1`;
}

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    cache: 'no-store',
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `API ${res.status}`);
  }
  return res.json();
}

export function swatchSrc(product: Pick<FabricProduct, 'image_url' | 'has_owner_photo'>): string {
  if (product.has_owner_photo && product.image_url) {
    if (product.image_url.startsWith('http')) return product.image_url;
    if (typeof window === 'undefined') return product.image_url;
    return product.image_url;
  }
  return '/ff-placeholder-swatch.svg';
}

export const fabricsApi = {
  catalog: (category?: string) =>
    readJson<{ products: FabricProduct[] }>(
      `/fine-fabrics/catalog${category ? `?category=${encodeURIComponent(category)}` : ''}`,
    ),
  product: (id: string | number) => readJson<FabricProduct>(`/fine-fabrics/products/${id}`),
  checkout: (body: Record<string, unknown>) =>
    readJson<Record<string, unknown>>('/fine-fabrics/checkout', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  samples: (body: Record<string, unknown>) =>
    readJson<Record<string, unknown>>('/fine-fabrics/samples', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  preview: (productId: number) =>
    readJson<Record<string, unknown>>('/fine-fabrics/preview', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId }),
    }),
};
