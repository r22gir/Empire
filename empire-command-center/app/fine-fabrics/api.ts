import type { FabricProduct, ShippingEstimate } from './types';

export function apiBase(): string {
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
  const headers: Record<string, string> = { ...(init?.headers as Record<string, string> || {}) };
  if (init?.body && !(init.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers,
    cache: 'no-store',
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `API ${res.status}`);
  }
  return res.json();
}

export function swatchSrc(product: Pick<FabricProduct, 'image_url' | 'has_owner_photo' | 'has_vendor_image' | 'placeholder'>): string {
  if (product.image_url) {
    return product.image_url;
  }
  return '/ff-placeholder-swatch.svg';
}

export function productTitle(product: Pick<FabricProduct, 'display_title' | 'brand' | 'sku' | 'pattern' | 'color' | 'empire_code'>): string {
  if (product.display_title) return product.display_title;
  const bits = [product.brand, product.sku, product.pattern, product.color].filter(Boolean);
  return bits.join(' ') || product.empire_code || 'Fabric';
}

export const fabricsApi = {
  catalog: (category?: string, search?: string) => {
    const q = new URLSearchParams();
    if (category) q.set('category', category);
    if (search) q.set('search', search);
    const suffix = q.toString() ? `?${q.toString()}` : '';
    return readJson<{ products: FabricProduct[] }>(`/fine-fabrics/catalog${suffix}`);
  },
  product: (id: string | number) => readJson<FabricProduct>(`/fine-fabrics/products/${id}`),
  estimateShipping: (body: { items?: Array<{ product_id: number; yards: number }>; sample_ids?: number[] }) =>
    readJson<ShippingEstimate>('/fine-fabrics/shipping/estimate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
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
  preview: (productId: number, itemType?: string) =>
    readJson<Record<string, unknown>>('/fine-fabrics/preview', {
      method: 'POST',
      body: JSON.stringify({ product_id: productId, item_type: itemType || 'roman_shade' }),
    }),
  itemQuote: (body: Record<string, unknown>) =>
    readJson<Record<string, unknown>>('/fine-fabrics/quote', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  admin: {
    products: () => readJson<{ products: FabricProduct[] }>('/fine-fabrics/admin/products'),
    unsorted: () => readJson<{ products: Array<FabricProduct & { vendor_name?: string; is_unsorted?: boolean }> }>('/fine-fabrics/admin/unsorted'),
    importFiles: () => readJson<{ files: Array<{ name: string; bytes: number }> }>('/fine-fabrics/admin/import-files'),
    importDir: (filename?: string) =>
      readJson<Record<string, unknown>>('/fine-fabrics/admin/import-dir', {
        method: 'POST',
        body: JSON.stringify({ filename: filename || null }),
      }),
    importCsv: async (file: File) => {
      const data = new FormData();
      data.append('file', file);
      const res = await fetch(`${apiBase()}/fine-fabrics/import`, { method: 'POST', body: data });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    assignCategory: (id: number, category: string) =>
      readJson<Record<string, unknown>>(`/fine-fabrics/admin/products/${id}/category`, {
        method: 'PUT',
        body: JSON.stringify({ category }),
      }),
    shippingRules: () => readJson<{ rules: Array<Record<string, unknown>> }>('/fine-fabrics/admin/shipping-rules'),
    updateShippingRules: (vendorId: number, body: Record<string, number>) =>
      readJson<{ rules: Array<Record<string, unknown>> }>(`/fine-fabrics/admin/shipping-rules/${vendorId}`, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    orders: () =>
      readJson<{ orders: Array<Record<string, unknown>>; samples: Array<Record<string, unknown>> }>(
        '/fine-fabrics/admin/orders',
      ),
    shortfalls: () => readJson<{ shortfalls: Array<Record<string, unknown>> }>('/fine-fabrics/admin/shortfalls'),
    recordOrderShipping: (id: number, actual: number) =>
      readJson<Record<string, unknown>>(`/fine-fabrics/admin/orders/${id}/shipping`, {
        method: 'PUT',
        body: JSON.stringify({ actual_vendor_shipping: actual }),
      }),
    recordSampleShipping: (id: number, actual: number) =>
      readJson<Record<string, unknown>>(`/fine-fabrics/admin/samples/${id}/shipping`, {
        method: 'PUT',
        body: JSON.stringify({ actual_vendor_shipping: actual }),
      }),
  },
};
