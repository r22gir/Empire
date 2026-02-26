'use client';
import { useState } from 'react';
import { Brain, Package, Cpu, Menu, X } from 'lucide-react';

const NAV_LINKS = [
  { label: 'MAX AI',   icon: Brain,   href: '/' },
  { label: 'Products', icon: Package, href: '/products' },
  { label: 'Ollama',   icon: Cpu,     href: '/ollama' },
];

export default function TopNav({ currentApp, currentPort }: { currentApp: string; currentPort: number }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div
        className="h-11 flex items-center justify-between px-4 shrink-0 sticky top-0 z-50"
        style={{
          background: 'rgba(5,5,13,0.92)',
          borderBottom: '1px solid rgba(212,175,55,0.10)',
          backdropFilter: 'blur(20px)',
        }}
      >
        {/* Left — logo + breadcrumb */}
        <div className="flex items-center gap-3">
          <a href="/" className="flex items-center gap-2 group">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-black"
              style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #8B5CF6 100%)' }}
            >
              E
            </div>
            <span className="text-sm font-bold hidden sm:block text-gold-shimmer tracking-wider">EMPIRE</span>
          </a>
          <span style={{ color: 'rgba(212,175,55,0.25)' }}>/</span>
          <span className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{currentApp}</span>
        </div>

        {/* Center — nav links */}
        <nav className="hidden md:flex items-center gap-0.5">
          {NAV_LINKS.map(link => {
            const active = link.label === currentApp;
            return (
              <a
                key={link.href}
                href={link.href}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                style={{
                  background: active ? 'var(--gold-pale)' : 'transparent',
                  color:      active ? 'var(--gold)'      : 'var(--text-secondary)',
                  border:     active ? '1px solid var(--gold-border)' : '1px solid transparent',
                }}
              >
                <link.icon className="w-3.5 h-3.5" />
                <span className="hidden lg:inline">{link.label}</span>
              </a>
            );
          })}
        </nav>

        {/* Right — MAX button + hamburger */}
        <div className="flex items-center gap-2">
          <a
            href="/"
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: 'var(--gold-pale)',
              color: 'var(--gold)',
              border: '1px solid var(--gold-border)',
            }}
          >
            <Brain className="w-3.5 h-3.5" />
            <span>MAX</span>
          </a>
          <button
            onClick={() => setOpen(!open)}
            className="md:hidden p-2 rounded-lg transition"
            style={{ color: 'var(--text-secondary)' }}
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <div
            className="absolute right-0 top-0 h-full w-64 flex flex-col p-4"
            style={{ background: 'var(--surface)', borderLeft: '1px solid var(--border)' }}
          >
            <div className="flex justify-between items-center mb-5">
              <span className="font-bold text-sm" style={{ color: 'var(--gold)' }}>Navigation</span>
              <button onClick={() => setOpen(false)} style={{ color: 'var(--text-secondary)' }}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-1">
              {NAV_LINKS.map(link => {
                const active = link.label === currentApp;
                return (
                  <a
                    key={link.href}
                    href={link.href}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all"
                    style={{
                      background: active ? 'var(--gold-pale)' : 'transparent',
                      color:      active ? 'var(--gold)'      : 'var(--text-secondary)',
                    }}
                  >
                    <link.icon className="w-4 h-4" />
                    {link.label}
                  </a>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
