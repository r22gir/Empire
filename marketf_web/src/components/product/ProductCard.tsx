import Link from 'next/link';
import { formatPrice } from '@/lib/utils';

interface ProductCardProps {
  product: {
    id: string;
    title: string;
    price: number;
    images: string[];
    condition: string;
  };
}

export default function ProductCard({ product }: ProductCardProps) {
  const imageUrl = product.images?.[0] || '/placeholder-product.png';

  return (
    <Link href={`/product/${product.id}`} className="card hover:shadow-lg transition-shadow">
      <div className="aspect-square bg-gray-100 rounded-lg mb-4 overflow-hidden">
        <img
          src={imageUrl}
          alt={product.title}
          className="w-full h-full object-cover"
        />
      </div>
      <h3 className="font-semibold mb-2 line-clamp-2">{product.title}</h3>
      <p className="text-sm text-gray-500 mb-2 capitalize">
        {product.condition.replace('_', ' ')}
      </p>
      <p className="text-xl font-bold text-primary">{formatPrice(product.price)}</p>
      <div className="flex items-center gap-1 mt-2 text-sm text-gray-600">
        {/* TODO: Replace with actual seller rating from API */}
        <span>⭐ 4.9</span>
        <span className="text-gray-400">•</span>
        <span>Fast shipping</span>
      </div>
    </Link>
  );
}
