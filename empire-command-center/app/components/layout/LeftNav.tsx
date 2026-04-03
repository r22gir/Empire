'use client';
import { useState, useEffect } from 'react';
import { EcosystemProduct } from '../../lib/types';
import {
  Crown, Scissors, TreePine, Gem, Share2, Bot, ShieldCheck, Server,
  Cpu, Activity, Coins, Store, Wrench, Headphones, Target, Truck,
  Users, Repeat, Globe, FileText, Sparkles, Wallet, Sun, Heart,
  ChevronsLeft, ChevronsRight, Camera, PawPrint, Monitor, Menu, X, PenTool,
  Building2, ShoppingCart,
} from 'lucide-react';

interface NavItem {
  id: EcosystemProduct;
  name: string;
  icon: React.ReactNode;
  status: 'active' | 'dev' | 'planned';
  color: string;
}

const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Command',
    items: [
      { id: 'owner', name: "Owner's Desk", icon: <Crown size={16} />, status: 'active', color: '#b8960c' },
      { id: 'max-avatar' as any, name: 'MAX Avatar', icon: <Monitor size={16} />, status: 'active', color: '#b8960c' },
    ],
  },
  {
    label: 'Your Business',
    items: [
      { id: 'workroom', name: 'Empire Workroom', icon: <Scissors size={16} />, status: 'active', color: '#16a34a' },
      { id: 'craft', name: 'WoodCraft', icon: <TreePine size={16} />, status: 'active', color: '#ca8a04' },
      { id: 'storefront', name: 'StoreFront Forge', icon: <ShoppingCart size={16} />, status: 'active', color: '#16a34a' },
      { id: 'construction', name: 'ConstructionForge', icon: <Building2 size={16} />, status: 'active', color: '#b8960c' },
      { id: 'luxe', name: 'LuxeForge', icon: <Gem size={16} />, status: 'active', color: '#7c3aed' },
    ],
  },
  {
    label: 'Tools',
    items: [
      { id: 'vision', name: 'AI Vision', icon: <Camera size={16} />, status: 'active', color: '#7c3aed' },
      { id: 'drawings' as any, name: 'Drawing Studio', icon: <PenTool size={16} />, status: 'active', color: '#b8960c' },
    ],
  },
  {
    label: 'Ecosystem',
    items: [
      { id: 'social', name: 'SocialForge', icon: <Share2 size={16} />, status: 'dev', color: '#ec4899' },
      { id: 'openclaw', name: 'OpenClaw', icon: <Bot size={16} />, status: 'active', color: '#f59e0b' },
      { id: 'recovery', name: 'RecoveryForge', icon: <ShieldCheck size={16} />, status: 'active', color: '#06b6d4' },
      { id: 'market', name: 'MarketForge', icon: <Store size={16} />, status: 'dev', color: '#2563eb' },
      { id: 'contractor', name: 'ContractorForge', icon: <Wrench size={16} />, status: 'dev', color: '#d97706' },
      { id: 'support', name: 'SupportForge', icon: <Headphones size={16} />, status: 'dev', color: '#7c3aed' },
      { id: 'lead', name: 'LeadForge', icon: <Target size={16} />, status: 'dev', color: '#16a34a' },
      { id: 'ship', name: 'ShipForge', icon: <Truck size={16} />, status: 'dev', color: '#2563eb' },
      { id: 'crm', name: 'ForgeCRM', icon: <Users size={16} />, status: 'dev', color: '#b8960c' },
      { id: 'relist', name: 'RelistApp', icon: <Repeat size={16} />, status: 'active', color: '#06b6d4' },
      { id: 'llc', name: 'LLCFactory', icon: <Globe size={16} />, status: 'dev', color: '#16a34a' },
      { id: 'apost', name: 'ApostApp', icon: <FileText size={16} />, status: 'dev', color: '#b8960c' },
      { id: 'assist', name: 'EmpireAssist', icon: <Sparkles size={16} />, status: 'dev', color: '#b8960c' },
      { id: 'pay', name: 'EmpirePay', icon: <Wallet size={16} />, status: 'dev', color: '#16a34a' },
      { id: 'amp', name: 'AMP', icon: <Sun size={16} />, status: 'active', color: '#f59e0b' },
      { id: 'vetforge', name: 'VetForge', icon: <Heart size={16} />, status: 'dev', color: '#ef4444' },
      { id: 'petforge', name: 'PetForge', icon: <PawPrint size={16} />, status: 'dev', color: '#ef4444' },
    ],
  },
  {
    label: 'Infrastructure',
    items: [
      { id: 'platform', name: 'PlatformForge', icon: <Server size={16} />, status: 'active', color: '#2563eb' },
      { id: 'hardware', name: 'Hardware', icon: <Cpu size={16} />, status: 'dev', color: '#d97706' },
      { id: 'system', name: 'System', icon: <Activity size={16} />, status: 'active', color: '#16a34a' },
      { id: 'tokens', name: 'Tokens & Costs', icon: <Coins size={16} />, status: 'active', color: '#b8960c' },
    ],
  },
];

interface Props {
  activeProduct: EcosystemProduct;
  onProductChange: (product: EcosystemProduct) => void;
}

export default function LeftNav({ activeProduct, onProductChange }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile and auto-collapse
  useEffect(() => {
    const check = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setCollapsed(true);
        setMobileOpen(false);
      }
    };
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  // Close mobile nav on product change
  const handleProductClick = (product: EcosystemProduct) => {
    onProductChange(product);
    if (isMobile) setMobileOpen(false);
  };

  // On mobile: show hamburger button (rendered in TopBar area via CSS), overlay nav
  const showNav = isMobile ? mobileOpen : true;
  const isCollapsed = isMobile ? false : collapsed; // On mobile overlay, always show expanded

  return (
    <>
      {/* Mobile hamburger button - fixed position */}
      {isMobile && !mobileOpen && (
        <button
          onClick={() => setMobileOpen(true)}
          className="fixed bottom-20 left-3 z-[110] flex items-center justify-center"
          style={{
            width: 48, height: 48, borderRadius: 14,
            background: '#b8960c', color: '#fff',
            boxShadow: '0 4px 16px rgba(184,150,12,0.4)',
            border: 'none', cursor: 'pointer',
          }}
          aria-label="Open menu"
        >
          <Menu size={22} />
        </button>
      )}

      {/* Mobile overlay backdrop */}
      {isMobile && mobileOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-[100]"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Nav panel */}
      {showNav && (
        <nav
          className={`bg-[var(--panel)] border-r border-[var(--border)] flex flex-col shrink-0 overflow-y-auto ${
            isMobile ? 'fixed inset-y-0 left-0 z-[101] shadow-2xl' : ''
          }`}
          style={{
            width: isCollapsed ? 56 : 220,
            transition: 'width 0.2s ease',
            padding: isCollapsed ? '8px 6px' : '12px 10px',
          }}
        >
          {/* Close / Collapse toggle */}
          <button
            onClick={() => {
              if (isMobile) setMobileOpen(false);
              else setCollapsed(!collapsed);
            }}
            className="flex items-center justify-center cursor-pointer hover:bg-[#f0ede8] transition-colors"
            style={{
              width: isCollapsed ? 36 : '100%',
              height: 36,
              borderRadius: 8,
              border: 'none',
              background: 'transparent',
              color: '#999',
              marginBottom: 8,
              alignSelf: isCollapsed ? 'center' : 'flex-end',
            }}
            title={isMobile ? 'Close menu' : (collapsed ? 'Expand sidebar' : 'Collapse sidebar')}
          >
            {isMobile ? <X size={18} /> : (collapsed ? <ChevronsRight size={14} /> : <ChevronsLeft size={14} />)}
          </button>

          {NAV_SECTIONS.map((section, si) => (
            <div key={section.label}>
              {si > 0 && <div className="h-px bg-[var(--border)] my-2" style={{ margin: isCollapsed ? '6px 4px' : '8px 6px' }} />}
              {!isCollapsed && (
                <div className="section-label mb-1.5" style={{ fontSize: 9, padding: '0 8px' }}>{section.label}</div>
              )}
              <div className="flex flex-col" style={{ gap: isCollapsed ? 2 : 3 }}>
                {section.items.map(item => {
                  const isActive = activeProduct === item.id;
                  const statusDot = item.status === 'active' ? '#22c55e'
                    : item.status === 'dev' ? '#f59e0b'
                    : '#d1d5db';

                  if (isCollapsed) {
                    return (
                      <button
                        key={item.id}
                        onClick={() => handleProductClick(item.id)}
                        className="flex items-center justify-center cursor-pointer transition-all"
                        title={item.name}
                        style={{
                          width: 40,
                          height: 40,
                          borderRadius: 12,
                          border: isActive ? '1.5px solid #f0e6c0' : '1.5px solid transparent',
                          background: isActive ? '#fdf8eb' : 'transparent',
                          color: isActive ? '#b8960c' : item.color,
                          opacity: isActive ? 1 : 0.7,
                          alignSelf: 'center',
                          position: 'relative',
                        }}
                        onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#f5f3ef'; e.currentTarget.style.opacity = '1'; } }}
                        onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.opacity = '0.7'; } }}
                      >
                        {item.icon}
                        <span style={{
                          position: 'absolute', top: 4, right: 4,
                          width: 5, height: 5, borderRadius: '50%',
                          background: isActive ? '#b8960c' : statusDot,
                        }} />
                      </button>
                    );
                  }

                  return (
                    <button
                      key={item.id}
                      onClick={() => handleProductClick(item.id)}
                      className="w-full text-left flex items-center gap-2.5 cursor-pointer transition-all"
                      style={{
                        padding: '10px 12px',
                        borderRadius: 12,
                        fontSize: 13,
                        minHeight: 44,
                        border: isActive ? '1.5px solid #f0e6c0' : '1.5px solid transparent',
                        background: isActive ? '#fdf8eb' : 'transparent',
                        fontWeight: isActive ? 600 : 400,
                        boxShadow: isActive ? '0 1px 4px rgba(184,150,12,0.08)' : 'none',
                      }}
                      onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#f5f3ef'; e.currentTarget.style.borderColor = '#ece8e0'; } }}
                      onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; } }}
                    >
                      <span className="shrink-0" style={{ color: isActive ? '#b8960c' : item.color, opacity: isActive ? 1 : 0.7 }}>
                        {item.icon}
                      </span>
                      <span className="flex-1 truncate" style={{ color: isActive ? '#96750a' : '#666' }}>{item.name}</span>
                      <span style={{ width: 5, height: 5, borderRadius: '50%', flexShrink: 0, background: isActive ? '#b8960c' : statusDot }} />
                      {item.status === 'dev' && !isActive && (
                        <span style={{ fontSize: 7, color: '#d97706', fontWeight: 700, background: '#fffbeb', padding: '1px 5px', borderRadius: 4, lineHeight: '13px' }}>DEV</span>
                      )}
                      {item.status === 'planned' && !isActive && (
                        <span style={{ fontSize: 7, color: '#9ca3af', fontWeight: 700, background: '#f3f4f6', padding: '1px 5px', borderRadius: 4, lineHeight: '13px' }}>SOON</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      )}
    </>
  );
}
