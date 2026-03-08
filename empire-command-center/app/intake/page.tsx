'use client';
import { Zap, ArrowRight, Ruler, Camera, MessageSquare } from 'lucide-react';
import Link from 'next/link';

export default function IntakeLanding() {
  return (
    <div className="min-h-screen bg-[#faf9f7]">
      <nav className="bg-white border-b border-[#e5e0d8]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-14">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#c9a84c] flex items-center justify-center">
              <Zap size={16} className="text-white" />
            </div>
            <span className="font-bold text-[14px]">Empire</span>
            <span className="text-[10px] text-[#aaa] ml-1">Design Portal</span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/intake/login" className="text-xs text-[#777] hover:text-[#c9a84c] transition-colors font-medium">Sign In</Link>
            <Link href="/intake/signup" className="px-4 py-2 text-xs font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors">Get Started</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#fdf8eb] border border-[#c9a84c]/20 text-[#c9a84c] text-xs font-medium mb-6">
            <Zap size={12} /> Free for designers & clients
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold text-[#1a1a1a] mb-4 leading-tight">
            Submit Your Project.<br />Get a Quote in 24 Hours.
          </h1>
          <p className="text-lg text-[#777] max-w-xl mx-auto mb-8">
            Upload photos, add measurements, describe your vision. We handle the rest — custom drapery, upholstery, blinds, and more.
          </p>
          <Link href="/intake/signup" className="inline-flex items-center gap-2 px-8 py-4 text-base font-semibold bg-[#c9a84c] text-white rounded-xl hover:bg-[#b8960c] transition-all hover:shadow-lg group">
            Start Your Project <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-16">
          {[
            { icon: Camera, title: 'Upload Photos', desc: 'Snap photos of your rooms and windows. We analyze them with AI.', step: '1' },
            { icon: Ruler, title: 'Add Measurements', desc: 'Enter window sizes or let us measure. Use a credit card for scale.', step: '2' },
            { icon: MessageSquare, title: 'Get Your Quote', desc: '3-tier proposals with mockups. Choose your favorite and approve.', step: '3' },
          ].map((item, i) => (
            <Link key={i} href="/intake/signup">
              <div className="bg-white rounded-xl border border-[#e5e0d8] p-6 text-center hover:border-[#c9a84c] hover:shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all cursor-pointer">
                <div className="text-[10px] font-bold text-[#c9a84c] mb-3">STEP {item.step}</div>
                <div className="w-12 h-12 rounded-xl bg-[#fdf8eb] flex items-center justify-center mx-auto mb-4">
                  <item.icon size={22} className="text-[#c9a84c]" />
                </div>
                <h3 className="font-semibold text-[#1a1a1a] mb-2">{item.title}</h3>
                <p className="text-sm text-[#777]">{item.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
