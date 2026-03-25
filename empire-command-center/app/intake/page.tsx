'use client';
import { Crown, ArrowRight, Ruler, Camera, MessageSquare } from 'lucide-react';
import Link from 'next/link';

export default function IntakeLanding() {
  return (
    <div data-intake-page className="min-h-screen bg-[#f5f2ed]">
      <nav className="bg-[#1a1a1a] border-b border-[#2a2a2a]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-12">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#b8960c] flex items-center justify-center">
              <Crown size={13} className="text-white" />
            </div>
            <span className="font-bold text-[13px] text-white tracking-wide">Empire</span>
            <span className="text-[9px] text-[#888] font-medium tracking-wider uppercase">LuxeForge</span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/intake/login" className="px-3 py-2 min-h-[44px] flex items-center text-sm text-[#aaa] hover:text-[#b8960c] transition-colors font-medium">Sign In</Link>
            <Link href="/intake/signup" className="px-4 py-2 min-h-[44px] flex items-center text-sm font-semibold bg-[#b8960c] text-white rounded-lg hover:bg-[#a3850b] transition-colors">Get Started</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#fdf8eb] border border-[#b8960c]/20 text-[#b8960c] text-[11px] font-semibold mb-6">
            <Crown size={12} /> Free for designers & clients
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-[#1a1a1a] mb-4 leading-tight">
            Submit Your Project.<br />Get a Quote in 24 Hours.
          </h1>
          <p className="text-base text-[#777] max-w-xl mx-auto mb-8">
            Upload photos, add measurements, describe your vision. We handle the rest — custom drapery, upholstery, blinds, and more.
          </p>
          <Link href="/intake/signup" className="inline-flex items-center gap-2 px-8 py-3.5 text-sm font-bold bg-[#1a1a1a] text-white rounded-xl hover:bg-[#333] transition-all hover:shadow-lg group">
            Start Your Project <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mt-16">
          {[
            { icon: Camera, title: 'Upload Photos', desc: 'Snap photos of your rooms and windows. We analyze them with AI.', step: '1', color: '#7c3aed' },
            { icon: Ruler, title: 'Add Measurements', desc: 'Enter window sizes or let us measure. Use a credit card for scale.', step: '2', color: '#b8960c' },
            { icon: MessageSquare, title: 'Get Your Quote', desc: '3-tier proposals with mockups. Choose your favorite and approve.', step: '3', color: '#16a34a' },
          ].map((item, i) => (
            <Link key={i} href="/intake/signup">
              <div className="bg-[#faf9f7] rounded-[14px] border border-[#ece8e0] p-6 text-center hover:border-[#d5d0c8] hover:shadow-[0_2px_12px_rgba(0,0,0,0.04)] hover:-translate-y-[1px] transition-all cursor-pointer">
                <div className="text-[9px] font-bold tracking-[1.5px] text-[#c5c0b8] uppercase mb-3">Step {item.step}</div>
                <div className="w-11 h-11 rounded-xl flex items-center justify-center mx-auto mb-4"
                  style={{ background: item.color + '12', border: `1px solid ${item.color}25` }}>
                  <item.icon size={20} style={{ color: item.color }} />
                </div>
                <h3 className="font-semibold text-[14px] text-[#1a1a1a] mb-2">{item.title}</h3>
                <p className="text-[12px] text-[#888] leading-relaxed">{item.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
