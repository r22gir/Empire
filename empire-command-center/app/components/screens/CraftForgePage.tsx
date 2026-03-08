'use client';
import { Hammer, Palette, ShoppingBag, BarChart3, Eye, Sparkles, Package, Globe } from 'lucide-react';

export default function CraftForgePage() {
  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-[#fef9c3] flex items-center justify-center">
          <Hammer size={20} className="text-[#ca8a04]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#1a1a1a]">CraftForge</h1>
          <p className="text-xs text-[#777]">AI-Designed Home Decor & Furniture · {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3 mt-5 mb-6">
        <KPI icon={<Sparkles size={18} />} iconBg="#fef9c3" iconColor="#ca8a04" label="Designs Created" value="--" sub="AI-generated products" />
        <KPI icon={<ShoppingBag size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Store Products" value="--" sub="Listed on Etsy / Shopify" />
        <KPI icon={<Eye size={18} />} iconBg="#dbeafe" iconColor="#2563eb" label="Page Views" value="--" sub="Last 30 days" />
        <KPI icon={<BarChart3 size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Revenue MTD" value="--" sub="Month to date" />
      </div>

      {/* Two-column */}
      <div className="grid grid-cols-[1fr_1fr] gap-4 mb-6">
        {/* Product Pipeline */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Palette size={15} className="text-[#ca8a04]" /> Design Pipeline
          </h3>
          <div className="space-y-2">
            <PipelineItem stage="Concept" count="--" color="#ca8a04" bg="#fef9c3" />
            <PipelineItem stage="3D Rendering" count="--" color="#2563eb" bg="#dbeafe" />
            <PipelineItem stage="Ready to List" count="--" color="#16a34a" bg="#dcfce7" />
            <PipelineItem stage="Live on Store" count="--" color="#7c3aed" bg="#ede9fe" />
          </div>
          <div className="mt-4 p-3 rounded-lg bg-[#fffbeb] border border-[#fde68a]">
            <div className="text-[10px] font-bold text-[#ca8a04] mb-1">AI FORGE STATUS</div>
            <div className="text-xs text-[#555]">Design engine ready. Generate new products via MAX chat.</div>
          </div>
        </div>

        {/* Store & Social */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Globe size={15} className="text-[#2563eb]" /> Channels & Marketing
          </h3>
          <div className="space-y-2">
            <ChannelRow name="Etsy Store" status="--" statusColor="#16a34a" icon="🛍" />
            <ChannelRow name="Shopify" status="--" statusColor="#7c3aed" icon="🏪" />
            <ChannelRow name="Instagram" status="--" statusColor="#ec4899" icon="📸" />
            <ChannelRow name="Pinterest" status="--" statusColor="#dc2626" icon="📌" />
          </div>
          <div className="mt-4 p-3 rounded-lg bg-[#ede9fe] border border-[#c4b5fd]">
            <div className="text-[10px] font-bold text-[#7c3aed] mb-1">SOCIALFORGE</div>
            <div className="text-xs text-[#555]">Auto-post engine. Connect channels to enable auto-listing.</div>
          </div>
        </div>
      </div>

      {/* Inventory */}
      <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 mb-6">
        <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
          <Package size={15} className="text-[#b8960c]" /> Inventory & Fulfillment
        </h3>
        <div className="grid grid-cols-3 gap-3">
          <InventoryCard label="Raw Materials" value="--" detail="Wood · Resin · Hardware" color="#ca8a04" />
          <InventoryCard label="Finished Goods" value="--" detail="Ready to ship" color="#16a34a" />
          <InventoryCard label="Pending Orders" value="--" detail="Awaiting fulfillment" color="#2563eb" />
        </div>
      </div>

      {/* Sales chart placeholder */}
      <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 min-h-[180px] flex items-center justify-center">
        <div className="text-center">
          <BarChart3 size={32} className="text-[#d8d3cb] mx-auto mb-2" />
          <div className="text-sm font-semibold text-[#aaa]">Sales Analytics</div>
          <div className="text-[11px] text-[#ccc] mt-1">Product performance · Revenue by channel</div>
        </div>
      </div>
    </div>
  );
}

function KPI({ icon, iconBg, iconColor, label, value, sub }: { icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string }) {
  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-4 hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] hover:border-[#ca8a04] transition-all cursor-pointer">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: iconBg, color: iconColor }}>{icon}</div>
      <div className="text-2xl font-bold text-[#1a1a1a]">{value}</div>
      <div className="text-[10px] text-[#777] font-medium mt-0.5">{label}</div>
      <div className="text-[9px] text-[#aaa] mt-0.5">{sub}</div>
    </div>
  );
}

function PipelineItem({ stage, count, color, bg }: { stage: string; count: string; color: string; bg: string }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] bg-[#faf9f7]">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full" style={{ background: color }} />
        <span className="text-xs text-[#555]">{stage}</span>
      </div>
      <span className="text-sm font-bold px-2 py-0.5 rounded" style={{ color, background: bg }}>{count}</span>
    </div>
  );
}

function ChannelRow({ name, status, statusColor, icon }: { name: string; status: string; statusColor: string; icon: string }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] bg-[#faf9f7] hover:border-[#ca8a04] transition-all cursor-pointer">
      <div className="flex items-center gap-2">
        <span className="text-sm">{icon}</span>
        <span className="text-xs font-medium text-[#1a1a1a]">{name}</span>
      </div>
      <span className="text-[10px] font-bold" style={{ color: statusColor }}>{status}</span>
    </div>
  );
}

function InventoryCard({ label, value, detail, color }: { label: string; value: string; detail: string; color: string }) {
  return (
    <div className="p-4 rounded-lg border border-[#ece8e1] bg-[#faf9f7] text-center">
      <div className="text-xl font-bold" style={{ color }}>{value}</div>
      <div className="text-xs font-semibold text-[#1a1a1a] mt-1">{label}</div>
      <div className="text-[10px] text-[#aaa] mt-0.5">{detail}</div>
    </div>
  );
}
