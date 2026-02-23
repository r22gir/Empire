'use client';

import { useState } from 'react';
import BundleCard from '@/components/bundles/BundleCard';
import PreOrderForm from '@/components/bundles/PreOrderForm';
import { Check, Package, Shield, QrCode, TrendingUp } from 'lucide-react';

const BUNDLES = [
  {
    type: 'budget_mobile',
    name: 'Budget Mobile Bundle',
    price: 349,
    originalValue: 498,
    features: [
      '📱 Xiaomi Redmi Note 13',
      '📸 108MP Camera (great for product photos!)',
      '📦 1 Year Lite Subscription ($348 value)',
      '🎁 Quick Start Card',
    ],
  },
  {
    type: 'seeker_pro',
    name: 'Seeker Pro Bundle',
    price: 599,
    originalValue: 708,
    popular: true,
    features: [
      '📱 Solana Seeker Phone',
      '💳 Built-in Crypto Wallet (Seed Vault)',
      '📦 1 Year Pro Subscription ($708 value)',
      '🎁 Premium Packaging + Quick Start Card',
    ],
  },
  {
    type: 'full_empire',
    name: 'Full Empire Bundle',
    price: 899,
    originalValue: 1288,
    features: [
      '📱 Solana Seeker Phone',
      '💻 Beelink Mini PC (24/7 AI Agents)',
      '📦 1 Year Empire Subscription ($1,188 value)',
      '🤖 Pre-configured AI Agents',
    ],
  },
];

export default function BundlesPage() {
  const [selectedBundle, setSelectedBundle] = useState<typeof BUNDLES[0] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);

  const handlePreOrder = (bundle: typeof BUNDLES[0]) => {
    setSelectedBundle(bundle);
    setShowForm(true);
  };

  const handleOrderSuccess = (orderId: string) => {
    setShowForm(false);
    setOrderSuccess(true);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-br from-empire-blue to-empire-lightBlue text-white py-16 px-4">
        <div className="container mx-auto max-w-6xl text-center">
          <h1 className="text-5xl font-bold mb-4">📱 EmpireBox Hardware Bundles</h1>
          <p className="text-2xl mb-8 opacity-90">
            Your Complete Reselling Business in a Box
          </p>
          <p className="text-lg max-w-2xl mx-auto">
            Get everything you need to start your reselling empire. Phone, subscription,
            and setup—all in one package. Ships March 2026.
          </p>
        </div>
      </div>

      {/* Bundles Grid */}
      <div className="container mx-auto max-w-7xl px-4 py-16">
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {BUNDLES.map((bundle) => (
            <BundleCard
              key={bundle.type}
              {...bundle}
              onPreOrder={() => handlePreOrder(bundle)}
            />
          ))}
        </div>

        {/* Features Section */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-16">
          <h2 className="text-3xl font-bold text-center mb-12">
            Why Choose EmpireBox?
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="bg-empire-blue bg-opacity-10 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Package size={32} className="text-empire-blue" />
              </div>
              <h3 className="font-semibold mb-2">Phone Ships Sealed</h3>
              <p className="text-sm text-gray-600">
                We never touch your phone. It ships factory-sealed for maximum security.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-empire-orange bg-opacity-10 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <QrCode size={32} className="text-empire-orange" />
              </div>
              <h3 className="font-semibold mb-2">Instant Setup</h3>
              <p className="text-sm text-gray-600">
                Scan the QR code on your Quick Start Card for guided setup in minutes.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-green-500 bg-opacity-10 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Shield size={32} className="text-green-500" />
              </div>
              <h3 className="font-semibold mb-2">Secure Wallet</h3>
              <p className="text-sm text-gray-600">
                Create your own secure crypto wallet. Your keys, your control.
              </p>
            </div>
            <div className="text-center">
              <div className="bg-purple-500 bg-opacity-10 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <TrendingUp size={32} className="text-purple-500" />
              </div>
              <h3 className="font-semibold mb-2">Start Selling Fast</h3>
              <p className="text-sm text-gray-600">
                Everything configured and ready. Start listing products on day one.
              </p>
            </div>
          </div>
        </div>

        {/* Guarantees */}
        <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-xl p-8 border-2 border-green-200">
          <h2 className="text-2xl font-bold text-center mb-6">Our Guarantees</h2>
          <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
            <div className="flex items-start gap-3">
              <Check size={24} className="text-green-600 flex-shrink-0" />
              <div>
                <h3 className="font-semibold mb-1">30-Day Money Back</h3>
                <p className="text-sm text-gray-700">
                  Not satisfied? Return within 30 days for a full refund, no questions asked.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Check size={24} className="text-green-600 flex-shrink-0" />
              <div>
                <h3 className="font-semibold mb-1">Free Shipping (USA)</h3>
                <p className="text-sm text-gray-700">
                  Free ground shipping to all US addresses. International shipping available.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Check size={24} className="text-green-600 flex-shrink-0" />
              <div>
                <h3 className="font-semibold mb-1">Factory Warranty</h3>
                <p className="text-sm text-gray-700">
                  Full manufacturer warranty on all hardware. Plus our own support.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Check size={24} className="text-green-600 flex-shrink-0" />
              <div>
                <h3 className="font-semibold mb-1">Cancel Anytime</h3>
                <p className="text-sm text-gray-700">
                  After your included subscription, continue monthly or cancel anytime.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-16">
          <h2 className="text-3xl font-bold text-center mb-8">Frequently Asked Questions</h2>
          <div className="max-w-3xl mx-auto space-y-4">
            <details className="bg-white rounded-lg shadow p-6">
              <summary className="font-semibold cursor-pointer">
                When will my bundle ship?
              </summary>
              <p className="mt-2 text-gray-600">
                All bundles are scheduled to ship in March 2026. You'll receive tracking
                information via email as soon as your order ships.
              </p>
            </details>
            <details className="bg-white rounded-lg shadow p-6">
              <summary className="font-semibold cursor-pointer">
                Can I upgrade my subscription later?
              </summary>
              <p className="mt-2 text-gray-600">
                Yes! You can upgrade your subscription plan at any time from within the
                MarketForge app. The difference will be prorated.
              </p>
            </details>
            <details className="bg-white rounded-lg shadow p-6">
              <summary className="font-semibold cursor-pointer">
                Is the phone unlocked?
              </summary>
              <p className="mt-2 text-gray-600">
                Yes, all phones are factory unlocked and work with all major US carriers.
              </p>
            </details>
            <details className="bg-white rounded-lg shadow p-6">
              <summary className="font-semibold cursor-pointer">
                What if I already have a phone?
              </summary>
              <p className="mt-2 text-gray-600">
                You can purchase a subscription-only license on our website. These bundles
                are for customers who want the complete hardware + software package.
              </p>
            </details>
          </div>
        </div>
      </div>

      {/* Pre-Order Form Modal */}
      {showForm && selectedBundle && (
        <PreOrderForm
          bundleType={selectedBundle.type}
          bundleName={selectedBundle.name}
          price={selectedBundle.price}
          onClose={() => setShowForm(false)}
          onSuccess={handleOrderSuccess}
        />
      )}

      {/* Success Modal */}
      {orderSuccess && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-8 text-center">
            <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
              <Check size={32} className="text-green-600" />
            </div>
            <h2 className="text-2xl font-bold mb-4">Pre-Order Confirmed!</h2>
            <p className="text-gray-600 mb-6">
              Thank you for your pre-order! You'll receive a confirmation email shortly with
              your order details and license key.
            </p>
            <button
              onClick={() => setOrderSuccess(false)}
              className="bg-empire-blue hover:bg-empire-darkBlue text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
