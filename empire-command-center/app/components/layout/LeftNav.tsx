'use client';
import { useState, useEffect } from 'react';
import { EcosystemProduct, ScreenMode } from '../../lib/types';
import RightPanel from './RightPanel';
import {
  Crown, Scissors, TreePine, Gem, Share2, Bot, ShieldCheck, Server,
  Cpu, Activity, Coins, Store, Wrench, Headphones, Target, Truck,
  Users, Repeat, Globe, FileText, Sparkles, Wallet, Sun, Heart,
  ChevronsLeft, ChevronsRight, Camera, PawPrint, Monitor, Menu, X, PenTool,
  Building2, ShoppingCart, LayoutDashboard, Archive, BadgeCheck, FileAudio, DollarSign,
  ChevronDown, ChevronRight,
} from 'lucide-react';

interface NavItem {
  id: string;
  name: string;
  icon: React.ReactNode;
  status: 'active' | 'dev' | 'planned';
  color: string;
  screen?: ScreenMode;
  // 'daily-summary' is special: it toggles the inline Dashboard (RightPanel) instead of navigating.
  kind?: 'product' | 'screen' | 'daily-summary';
}

interface NavGroup {
  key: string;
  label: string;
  defaultExpanded: boolean;
  // Items in this group.
  items: NavItem[];
}

// ------------------------------------------------------------------
// N1: Sidebar grouping (Lane N1).
// Per Founder's spec: Command is always expanded; all other groups
// are collapsed by default. One group expanded at a time (accordion).
// "Daily Summary" replaces the loose Dashboard toggle below the
// divider — it is now a 4th item inside Command.
// ------------------------------------------------------------------
const NAV_GROUPS: NavGroup[] = [
  {
    key: 'command',
    label: 'Command',
    defaultExpanded: true, // always expanded per Founder
    items: [
      { id: 'owner', name: "Owner's Desk", icon: <Crown size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'workroom', name: 'Empire Workroom', icon: <Scissors size={16} />, status: 'active', color: '#16a34a', kind: 'product' },
      { id: 'craft', name: 'WoodCraft', icon: <TreePine size={16} />, status: 'active', color: '#ca8a04', kind: 'product' },
      // Daily Summary is the inline Dashboard panel (rightPanel) — toggled, not navigated.
      { id: 'daily-summary', name: 'Daily Summary', icon: <LayoutDashboard size={16} />, status: 'active', color: '#7c3aed', kind: 'daily-summary' },
    ],
  },
  {
    key: 'business',
    label: 'Business',
    defaultExpanded: false,
    items: [
      { id: 'storefront', name: 'StoreFront Forge', icon: <ShoppingCart size={16} />, status: 'active', color: '#16a34a', kind: 'product' },
      { id: 'construction', name: 'ConstructionForge', icon: <Building2 size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'luxe', name: 'LuxeForge', icon: <Gem size={16} />, status: 'active', color: '#7c3aed', kind: 'product' },
      // Business Profile = BusinessOps (Phase 1) entry point. Routes to the
      // `business-profile` screen; product remains unchanged.
      { id: 'business-profile', name: 'Business Profile', icon: <BadgeCheck size={16} />, status: 'active', color: '#16a34a', screen: 'business-profile' as ScreenMode, kind: 'screen' },
      { id: 'vendorops', name: 'VendorOps', icon: <BadgeCheck size={16} />, status: 'active', color: '#0d9488', kind: 'product' },
      { id: 'contractor', name: 'ContractorForge', icon: <Wrench size={16} />, status: 'active', color: '#d97706', kind: 'product' },
      { id: 'lead', name: 'LeadForge', icon: <Target size={16} />, status: 'active', color: '#16a34a', kind: 'product' },
      { id: 'crm', name: 'ForgeCRM', icon: <Users size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'pay', name: 'EmpirePay', icon: <Wallet size={16} />, status: 'active', color: '#16a34a', kind: 'product' },
      // Patch B: Pricing Studio is the operator's revenue/quoting engine.
      // It was previously hidden in the collapsed Tools group. Moved here
      // (Business group, near EmpirePay) so the founder sees it from the
      // default sidebar view. Public /pricing (SaaS pricing page) is a
      // separate route and is not affected. QuickSwitch Z still works.
      { id: 'pricing-studio', name: 'Pricing Studio', icon: <DollarSign size={16} />, status: 'active', color: '#16a34a', screen: 'pricing-studio', kind: 'screen' },
    ],
  },
  {
    key: 'tools',
    label: 'Tools',
    defaultExpanded: false,
    items: [
      { id: 'drawings', name: 'Drawing Studio', icon: <PenTool size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'vision', name: 'AI Vision', icon: <Camera size={16} />, status: 'active', color: '#7c3aed', kind: 'product' },
      { id: 'recovery', name: 'RecoveryForge', icon: <ShieldCheck size={16} />, status: 'active', color: '#06b6d4', kind: 'product' },
    ],
  },
  {
    key: 'growth',
    label: 'Growth / Channels',
    defaultExpanded: false,
    items: [
      { id: 'social', name: 'SocialForge', icon: <Share2 size={16} />, status: 'active', color: '#ec4899', kind: 'product' },
      { id: 'market', name: 'MarketForge', icon: <Store size={16} />, status: 'active', color: '#2563eb', kind: 'product' },
      { id: 'support', name: 'SupportForge', icon: <Headphones size={16} />, status: 'active', color: '#7c3aed', kind: 'product' },
      { id: 'ship', name: 'ShipForge', icon: <Truck size={16} />, status: 'active', color: '#2563eb', kind: 'product' },
      { id: 'amp', name: 'AMP', icon: <Sun size={16} />, status: 'active', color: '#f59e0b', kind: 'product' },
      { id: 'archive', name: 'ArchiveForge', icon: <Archive size={16} />, status: 'active', color: '#06b6d4', kind: 'product' },
      { id: 'transcript', name: 'TranscriptForge', icon: <FileAudio size={16} />, status: 'active', color: '#7c3aed', kind: 'product' },
    ],
  },
  {
    key: 'system',
    label: 'System',
    defaultExpanded: false,
    items: [
      { id: 'platform', name: 'PlatformForge', icon: <Server size={16} />, status: 'active', color: '#2563eb', kind: 'product' },
      { id: 'openclaw', name: 'OpenClaw', icon: <Bot size={16} />, status: 'active', color: '#f59e0b', kind: 'product' },
      { id: 'max-continuity', name: 'MAX Continuity', icon: <ShieldCheck size={16} />, status: 'active', color: '#0d9488', kind: 'product' },
      { id: 'system', name: 'System', icon: <Activity size={16} />, status: 'active', color: '#16a34a', kind: 'product' },
      { id: 'tokens', name: 'Tokens & Costs', icon: <Coins size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'hardware', name: 'Hardware', icon: <Cpu size={16} />, status: 'dev', color: '#d97706', kind: 'product' },
    ],
  },
  {
    key: 'more',
    label: 'More',
    defaultExpanded: false,
    items: [
      { id: 'relist', name: 'RelistApp', icon: <Repeat size={16} />, status: 'active', color: '#06b6d4', kind: 'product' },
      { id: 'llc', name: 'LLCFactory', icon: <Globe size={16} />, status: 'active', color: '#16a34a', kind: 'product' },
      { id: 'apost', name: 'ApostApp', icon: <FileText size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'assist', name: 'EmpireAssist', icon: <Sparkles size={16} />, status: 'dev', color: '#b8960c', kind: 'product' },
      { id: 'vetforge', name: 'VetForge', icon: <Heart size={16} />, status: 'planned', color: '#ef4444', kind: 'product' },
      { id: 'petforge', name: 'PetForge', icon: <PawPrint size={16} />, status: 'planned', color: '#ef4444', kind: 'product' },
      { id: 'dev', name: 'Developer Panel', icon: <Monitor size={16} />, status: 'dev', color: '#b8960c', kind: 'product' },
    ],
  },
];

interface Props {
  activeProduct: EcosystemProduct;
  activeScreen?: ScreenMode;
  onProductChange: (product: EcosystemProduct) => void;
  onScreenChange?: (screen: ScreenMode) => void;
  dashboardProps?: any;
}

export default function LeftNav({ activeProduct, activeScreen, onProductChange, onScreenChange, dashboardProps }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  // Per-group expanded state. Default: Command expanded, all others collapsed.
  // Accordion: only one group can be expanded at a time. Clicking a collapsed
  // group expands it AND collapses any currently-expanded group.
  const [expandedGroup, setExpandedGroup] = useState<string>('command');
  // Daily Summary toggle is a separate piece of state (it's a panel, not a nav).
  const [showDashboard, setShowDashboard] = useState(false);

  // Detect mobile and auto-collapse the sidebar
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

  // On mobile: show hamburger button (rendered in TopBar area via CSS), overlay nav
  const handleNavClick = (item: NavItem) => {
    if (item.kind === 'daily-summary') {
      setShowDashboard(s => !s);
      if (isMobile) setMobileOpen(false);
      return;
    }
    if (item.screen && onScreenChange) {
      onScreenChange(item.screen);
    } else if (item.kind === 'product') {
      onProductChange(item.id as EcosystemProduct);
    } else if (item.screen) {
      // safety: also fall through to onProductChange if kind was 'screen' but product also wanted
      onProductChange(item.id as EcosystemProduct);
    } else {
      onProductChange(item.id as EcosystemProduct);
    }
    if (isMobile) setMobileOpen(false);
  };

  const toggleGroup = (key: string) => {
    setExpandedGroup(prev => (prev === key ? '' : key));
  };

  const showNav = isMobile ? mobileOpen : true;
  const isCollapsed = isMobile ? false : collapsed; // On mobile overlay, always show expanded

  // Helper: count visible items per group (active + dev + planned).
  const groupCount = (g: NavGroup) => g.items.length;

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

          {/* Groups */}
          {NAV_GROUPS.map((group, gi) => {
            const isOpen = expandedGroup === group.key;
            return (
              <div key={group.key} style={{ marginTop: gi === 0 ? 0 : 4 }}>
                {gi > 0 && !isCollapsed && <div className="h-px bg-[var(--border)] my-1.5" />}
                {/* Group header — clickable to expand/collapse. Hidden entirely in icon-only mode. */}
                {!isCollapsed && (
                  <button
                    onClick={() => toggleGroup(group.key)}
                    className="w-full flex items-center justify-between gap-1.5 cursor-pointer hover:bg-[#f5f3ef] transition-colors"
                    style={{
                      padding: '7px 8px',
                      borderRadius: 8,
                      background: 'transparent',
                      border: 'none',
                      marginBottom: isOpen ? 4 : 0,
                    }}
                    title={isOpen ? `Collapse ${group.label}` : `Expand ${group.label}`}
                    aria-expanded={isOpen}
                  >
                    <div className="flex items-center gap-1.5 min-w-0">
                      {isOpen
                        ? <ChevronDown size={11} className="text-[#999] shrink-0" />
                        : <ChevronRight size={11} className="text-[#999] shrink-0" />
                      }
                      <span style={{ fontSize: 10, fontWeight: 700, color: '#666', letterSpacing: 1, textTransform: 'uppercase' }}>
                        {group.label}
                      </span>
                      <span style={{ fontSize: 9, color: '#aaa', background: '#f0ede8', padding: '1px 5px', borderRadius: 4, fontWeight: 600 }}>
                        {groupCount(group)}
                      </span>
                    </div>
                  </button>
                )}

                {/* Items — only when group is expanded AND not in icon-only mode. */}
                {isOpen && !isCollapsed && (
                  <div className="flex flex-col" style={{ gap: 3 }}>
                    {group.items.map(item => {
                      const isActive =
                        item.kind === 'daily-summary'
                          ? showDashboard
                          : (item.screen ? activeScreen === item.screen : activeProduct === item.id);
                      const statusDot = item.status === 'active' ? '#22c55e'
                        : item.status === 'dev' ? '#f59e0b'
                        : '#d1d5db';

                      return (
                        <button
                          key={item.id}
                          onClick={() => handleNavClick(item)}
                          className="w-full text-left flex items-center gap-2.5 cursor-pointer transition-all"
                          style={{
                            padding: '8px 10px',
                            borderRadius: 10,
                            fontSize: 12.5,
                            minHeight: 36,
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
                          {item.kind === 'daily-summary' ? (
                            <span style={{ fontSize: 7, color: showDashboard ? '#b8960c' : '#9ca3af', fontWeight: 700, background: showDashboard ? '#fdf8eb' : '#f3f4f6', padding: '1px 5px', borderRadius: 4, lineHeight: '13px' }}>
                              {showDashboard ? 'ON' : 'OFF'}
                            </span>
                          ) : (
                            <span style={{ width: 5, height: 5, borderRadius: '50%', flexShrink: 0, background: isActive ? '#b8960c' : statusDot }} />
                          )}
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
                )}
              </div>
            );
          })}

          {/* Inline dashboard panel (Daily Summary). Always available regardless of which group is expanded. */}
          {showDashboard && !isCollapsed && dashboardProps && (
            <div style={{ padding: '8px 4px', marginTop: 8, borderTop: '1px solid var(--border)' }}>
              <RightPanel {...dashboardProps} />
            </div>
          )}
        </nav>
      )}
    </>
  );
}
