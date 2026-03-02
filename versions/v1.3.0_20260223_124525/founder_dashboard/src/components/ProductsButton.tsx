"use client";
import Link from "next/link";

export default function ProductsButton() {
  return (
    <Link href="/products" className="block bg-gradient-to-r from-purple-600 via-pink-600 to-purple-600 rounded-xl p-6 hover:opacity-90 transition group mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-5xl">📦</span>
          <div>
            <h2 className="text-2xl font-bold text-white">Products</h2>
            <p className="text-white/70">Access all Empire Box® products</p>
          </div>
        </div>
        <div className="text-white text-4xl group-hover:translate-x-2 transition-transform">→</div>
      </div>
      <div className="flex gap-2 mt-4 flex-wrap">
        <span className="px-2 py-1 bg-white/20 rounded text-white text-sm">🏭 Workroom</span>
        <span className="px-2 py-1 bg-white/20 rounded text-white text-sm">💎 Luxe</span>
        <span className="px-2 py-1 bg-white/20 rounded text-white text-sm">🎧 Support</span>
        <span className="px-2 py-1 bg-white/20 rounded text-white text-sm">✨ Content</span>
        <span className="px-2 py-1 bg-white/20 rounded text-white text-sm">+4 more</span>
      </div>
    </Link>
  );
}
