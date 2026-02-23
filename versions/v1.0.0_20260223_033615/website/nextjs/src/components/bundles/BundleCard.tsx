'use client';

import { Check, Star } from 'lucide-react';

interface BundleCardProps {
  name: string;
  type: string;
  price: number;
  originalValue: number;
  features: string[];
  popular?: boolean;
  onPreOrder: () => void;
}

export default function BundleCard({
  name,
  type,
  price,
  originalValue,
  features,
  popular = false,
  onPreOrder,
}: BundleCardProps) {
  const savings = originalValue - price;

  return (
    <div
      className={`relative bg-white rounded-xl shadow-lg p-6 ${
        popular ? 'border-4 border-empire-orange' : 'border-2 border-gray-200'
      }`}
    >
      {popular && (
        <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
          <div className="bg-empire-orange text-white px-4 py-1 rounded-full flex items-center gap-1 text-sm font-bold">
            <Star size={16} fill="currentColor" />
            <span>MOST POPULAR</span>
          </div>
        </div>
      )}

      <div className="text-center mb-6">
        <h3 className="text-2xl font-bold text-gray-900 mb-2">{name}</h3>
        <div className="text-4xl font-bold text-empire-blue mb-2">
          ${price}
        </div>
        <p className="text-sm text-gray-600">
          Save ${savings} (${originalValue} value)
        </p>
      </div>

      <ul className="space-y-3 mb-8">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start gap-2">
            <Check size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
            <span className="text-sm text-gray-700">{feature}</span>
          </li>
        ))}
      </ul>

      <button
        onClick={onPreOrder}
        className={`w-full font-bold py-4 px-6 rounded-lg transition-colors ${
          popular
            ? 'bg-empire-orange hover:bg-orange-600 text-white'
            : 'bg-empire-blue hover:bg-empire-darkBlue text-white'
        }`}
      >
        Pre-Order Now - Ships March 2026
      </button>

      <p className="text-xs text-gray-500 text-center mt-4">
        30-day money back guarantee
      </p>
    </div>
  );
}
