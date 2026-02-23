'use client';
import Link from 'next/link';

const products = [
  { id: 'workroom-forge', name: 'Workroom Forge', emoji: '🔨', description: 'Order management', status: 'active', color: 'from-orange-500 to-red-600' },
  { id: 'luxeforge', name: 'LuxeForge', emoji: '✨', description: 'Product configurator', status: 'active', color: 'from-purple-500 to-pink-600' },
  { id: 'install-forge', name: 'Install Forge', emoji: '🔧', description: 'Installation scheduling', status: 'coming', color: 'from-blue-500 to-cyan-600' },
  { id: 'quote-forge', name: 'Quote Forge', emoji: '📝', description: 'Quotes & proposals', status: 'coming', color: 'from-green-500 to-emerald-600' },
  { id: 'max-ai', name: 'MAX AI', emoji: '🤖', description: 'AI assistant', status: 'active', color: 'from-violet-500 to-purple-600' },
];

export default function ProductsPage() {
  return (
    <div className="min-h-screen bg-[#030308] text-white p-8">
      <a href="/" className="text-gray-400 hover:text-white mb-4 block">← Back</a>
      <h1 className="text-3xl font-bold mb-8">🏰 Empire Box® Business Center</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((p) => (
          <a key={p.id} href={p.status === 'active' ? "/products/" + p.id : "#"}
            className="p-6 rounded-xl border border-gray-800 bg-[#0a0a0f] hover:border-purple-500">
            <div className="text-4xl mb-4">{p.emoji}</div>
            <h3 className="font-bold text-lg mb-2">{p.name}</h3>
            <p className="text-gray-400 text-sm">{p.description}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
