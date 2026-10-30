import type { Metadata } from 'next';
import { apiBase } from '../api';
import ProductClient from '../ProductClient';
import type { FabricProduct } from '../types';

async function loadProduct(id: string): Promise<FabricProduct | null> {
  try {
    const res = await fetch(`${apiBase()}/fine-fabrics/products/${id}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata(
  { params }: { params: Promise<{ id: string }> },
): Promise<Metadata> {
  const { id } = await params;
  const product = await loadProduct(id);
  if (!product) {
    return { title: 'Cloth not offered | Empire Fine Fabrics', robots: { index: false } };
  }
  const seo = product.seo;
  return {
    title: seo?.title || `${product.pattern} ${product.color} | Empire Fine Fabrics`,
    description: seo?.description,
    alternates: seo?.canonical ? { canonical: seo.canonical } : undefined,
    openGraph: {
      title: seo?.title,
      description: seo?.description,
      url: seo?.canonical,
    },
  };
}

export default async function FabricProductPage(
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const product = await loadProduct(id);
  if (!product) {
    return <main className="ff-main"><p className="ff-empty">This cloth is not offered online.</p></main>;
  }
  const jsonLd = product.seo?.json_ld;
  return (
    <>
      {jsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      ) : null}
      <ProductClient product={product} />
    </>
  );
}
