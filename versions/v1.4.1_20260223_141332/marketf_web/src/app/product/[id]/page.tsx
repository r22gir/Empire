'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { productAPI } from '@/lib/api';
import { formatPrice } from '@/lib/utils';

export default function ProductPage() {
  const params = useParams();
  const [product, setProduct] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState(0);

  useEffect(() => {
    async function loadProduct() {
      try {
        const data = await productAPI.get(params.id as string);
        setProduct(data);
      } catch (error) {
        console.error('Failed to load product:', error);
      } finally {
        setLoading(false);
      }
    }
    loadProduct();
  }, [params.id]);

  if (loading) {
    return (
      <div className="container py-8">
        <div className="animate-pulse">
          <div className="bg-gray-200 h-96 rounded-lg mb-8"></div>
          <div className="bg-gray-200 h-8 w-2/3 mb-4 rounded"></div>
          <div className="bg-gray-200 h-4 w-1/3 rounded"></div>
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="container py-8">
        <h1>Product not found</h1>
      </div>
    );
  }

  return (
    <div className="container py-8">
      <div className="grid md:grid-cols-2 gap-8">
        {/* Image Gallery */}
        <div>
          <div className="aspect-square bg-gray-100 rounded-lg mb-4 overflow-hidden">
            <img
              src={product.images?.[selectedImage] || '/placeholder-product.png'}
              alt={product.title}
              className="w-full h-full object-cover"
            />
          </div>
          <div className="flex gap-2">
            {product.images?.map((img: string, idx: number) => (
              <button
                key={idx}
                onClick={() => setSelectedImage(idx)}
                className={`w-20 h-20 rounded-lg overflow-hidden border-2 ${
                  idx === selectedImage ? 'border-primary' : 'border-gray-200'
                }`}
              >
                <img src={img} alt="" className="w-full h-full object-cover" />
              </button>
            ))}
          </div>
        </div>

        {/* Product Info */}
        <div>
          <h1 className="text-3xl font-bold mb-4">{product.title}</h1>
          <p className="text-sm text-gray-500 mb-4 capitalize">
            Condition: {product.condition.replace('_', ' ')}
          </p>

          <div className="mb-6">
            <p className="text-4xl font-bold text-primary mb-2">
              {formatPrice(product.price)}
            </p>
            <p className="text-gray-600">
              + {formatPrice(product.shipping_price || 8.45)} shipping
            </p>
          </div>

          <div className="flex gap-4 mb-8">
            <button className="btn btn-secondary flex-1">
              🛒 Add to Cart
            </button>
            <button className="btn btn-primary flex-1">
              ⚡ Buy Now
            </button>
          </div>

          {/* Seller Info */}
          <div className="card bg-gray-50">
            <h3 className="font-bold mb-4">Seller</h3>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-gray-300 rounded-full"></div>
              <div>
                <p className="font-semibold">Seller Name</p>
                <p className="text-sm text-gray-600">⭐ 4.9 (127 reviews)</p>
              </div>
            </div>
            <p className="text-sm text-gray-600">📍 Ships from: {product.ships_from_zip}</p>
            <p className="text-sm text-gray-600">📦 Ships in 1-2 days</p>
          </div>

          {/* Description */}
          <div className="mt-8">
            <h3 className="font-bold mb-4">Description</h3>
            <p className="text-gray-700 whitespace-pre-line">{product.description}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
