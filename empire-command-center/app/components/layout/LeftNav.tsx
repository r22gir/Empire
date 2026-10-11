'use client';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { V3Rail, BusinessesSheet } from '../../v3/Shell';
import type { SheetGroup } from '../../v3/Shell';
import type { RailItem } from '../../v3/edition';
import { EcosystemProduct, ScreenMode } from '../../lib/types';
import { AMP_HIDDEN_NAV, AMP_NAV_LABELS, MAXINE_HIDDEN_NAV, MAXINE_NAV_LABELS, editionFromEnv } from '../../lib/edition';
import { dailySummaryLabel, navGroupLabel } from '../../lib/familyChrome';
import { T } from '../../v3/edition';
import RightPanel from './RightPanel';
import {
  Crown, Scissors, TreePine, Gem, Share2, Bot, ShieldCheck, Server, Lightbulb,
  Cpu, Activity, Coins, Store, Wrench, Headphones, Target, Truck,
  Users, Repeat, Globe, FileText, Sparkles, Wallet, Sun, Heart,
  ChevronsLeft, ChevronsRight, Camera, PawPrint, Monitor, Menu, X, PenTool, CircleHelp,
  Building2, ShoppingCart, LayoutDashboard, Archive, BadgeCheck, FileAudio, DollarSign,
  ChevronDown, ChevronRight, LayoutGrid,
  FileStack,
} from 'lucide-react';

export interface NavItem {
  id: string;
  name: string;
  icon: React.ReactNode;
  status: 'active' | 'dev' | 'planned';
  color: string;
  screen?: ScreenMode;
  // 'daily-summary' is special: it toggles the inline Dashboard (RightPanel) instead of navigating.
  kind?: 'product' | 'screen' | 'daily-summary';
}

export interface NavGroup {
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
// Exported so /preview/cockpit can mirror the real menu (same items, same order).
export const NAV_GROUPS: NavGroup[] = [
  {
    key: 'command',
    label: 'Command',
    defaultExpanded: true, // always expanded per Founder
    items: [
      { id: 'owner', name: "Owner's Desk", icon: <Crown size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'archivo', name: 'Archivo', icon: <Archive size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'ayuda', name: 'Ayuda', icon: <CircleHelp size={16} />, status: 'active', color: '#b8960c', kind: 'product' },
      { id: 'workroom', name: 'Empire Workroom', icon: <Scissors size={16} />, status: 'active', color: '#16a34a', kind: 'product' },
      { id: 'craft', name: 'WoodCraft', icon: <TreePine size={16} />, status: 'active', color: '#ca8a04', kind: 'product' },
      // Daily Summary is the inline Dashboard panel (rightPanel) — toggled, not navigated.
      { id: 'daily-summary', name: 'Daily Summary', icon: <LayoutDashboard size={16} />, status: 'active', color: '#7c3aed', kind: 'daily-summary' },
      // Final Docs hub: latest final estimate / presentation / invoice / drawings / photos per job.
      { id: 'final-docs', name: 'Final Docs', icon: <FileStack size={16} />, status: 'active', color: '#00e5ff', screen: 'final-docs' as ScreenMode, kind: 'screen' },
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
      { id: 'cibernettic', name: 'Cibernettic', icon: <Server size={16} />, status: 'active', color: '#2563eb', kind: 'product' },
      { id: 'nueva-empresa', name: 'Nueva empresa', icon: <Building2 size={16} />, status: 'active', color: '#D4A030', kind: 'product' },
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
      { id: 'improvements', name: 'Improvements', icon: <Lightbulb size={16} />, status: 'active', color: '#7c3aed', kind: 'product' },
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

// Rail key for the current screen (v3 launcher rail highlight).
function railKey(product: EcosystemProduct, screen?: ScreenMode): string | null {
  if (screen === 'invoices' || screen === 'invoice') return 'finance';
  if (screen === 'inbox') return 'comms';
  if (screen === 'final-docs' || screen === 'docs') return 'docs';
  const p = String(product);
  if (p === 'owner' && (screen === 'chat' || !screen)) return 'max';
  if (['workroom', 'craft', 'construction', 'amp', 'lead', 'social', 'market', 'system', 'crm', 'pay'].includes(p)) return p;
  return null;
}

/** Family-only entries that open their own pages instead of an in-app product. */
const FAMILY_PAGE_HREF: Record<string, string> = {
  'nueva-empresa': '/amp/empresas',
  cibernettic: '/amp/empresas/cibernettic',
  archivo: '/archivo',
  ayuda: '/ayuda',
};

/**
 * NAV_GROUPS as this edition shows them. Family editions (Max-e / Maxine) hide the
 * Workroom tools and Empire internals, add their own businesses, and use Spanish labels.
 * The main studio gets NAV_GROUPS minus the family-only entries.
 */
export function editionNavGroups(edition: string = editionFromEnv()): NavGroup[] {
  const ampEdition = edition === 'amp';
  const maxineEdition = edition === 'maxine';
  return NAV_GROUPS.map((group) => {
    let items = group.items.filter((item) => {
      if (item.id === 'cibernettic' && !ampEdition) return false;
      if (item.id === 'archivo' && !ampEdition && !maxineEdition) return false;
      if (item.id === 'ayuda' && !ampEdition && !maxineEdition) return false;
      if (maxineEdition) return !MAXINE_HIDDEN_NAV.has(item.id);
      if (ampEdition) return !AMP_HIDDEN_NAV.has(item.id);
      return item.id !== 'nueva-empresa';
    });
    if (maxineEdition && group.key === 'command') {
      const portfolio = NAV_GROUPS.flatMap((g) => g.items).find((item) => item.id === 'construction');
      items = items.filter((item) => item.id !== 'construction');
      if (portfolio) items = [{ ...portfolio, name: MAXINE_NAV_LABELS.construction }, ...items];
    }
    if (maxineEdition && group.key === 'business') {
      items = items.filter((item) => item.id !== 'construction');
    }
    return {
      ...group,
      label: navGroupLabel(edition, group.key, T(group.label)),
      items: items.map((item) => {
        if (maxineEdition && MAXINE_NAV_LABELS[item.id]) return { ...item, name: MAXINE_NAV_LABELS[item.id] };
        if (ampEdition && AMP_NAV_LABELS[item.id]) return { ...item, name: AMP_NAV_LABELS[item.id] };
        if (item.kind === 'daily-summary') return { ...item, name: dailySummaryLabel(edition) };
        return { ...item, name: T(item.name) };
      }),
    };
  }).filter((group) => group.items.length > 0);
}

/** Link for a nav entry (sheet / home). */
export function navItemHref(item: NavItem): string {
  if (FAMILY_PAGE_HREF[item.id]) return FAMILY_PAGE_HREF[item.id];
  if (item.kind === 'daily-summary') return '/?product=owner&screen=dashboard';
  if (item.kind === 'screen' && item.screen) return `/?screen=${encodeURIComponent(item.screen)}`;
  return `/?product=${encodeURIComponent(item.id)}`;
}

/**
 * Left navigation (design system v3): the launcher rail with the main forges, plus an
 * "All" sheet that lists every module in NAV_GROUPS (one click away). Daily Summary
 * (RightPanel) opens as a side panel next to the rail. On phones the rail is hidden
 * and a floating button opens the same sheet.
 */
export default function LeftNav({ activeProduct, activeScreen, onProductChange, onScreenChange, dashboardProps }: Props) {
  const [sheet, setSheet] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const handleNavClick = useCallback((item: NavItem) => {
    if (FAMILY_PAGE_HREF[item.id]) { window.location.href = FAMILY_PAGE_HREF[item.id]; return; }
    if (item.kind === 'daily-summary') { setShowDashboard(s => !s); return; }
    if (item.screen && onScreenChange) onScreenChange(item.screen);
    else onProductChange(item.id as EcosystemProduct);
  }, [onProductChange, onScreenChange]);

  const groups: SheetGroup[] = useMemo(() => editionNavGroups().map(g => ({
    key: g.key, label: g.label,
    items: g.items.map(it => ({
      id: it.id, name: it.name, icon: it.icon, status: it.status,
      href: navItemHref(it),
      on: it.kind === 'daily-summary' ? showDashboard : (it.screen ? activeScreen === it.screen : activeProduct === it.id),
      onPick: () => handleNavClick(it),
    })),
  })), [activeProduct, activeScreen, showDashboard, handleNavClick]);

  const onGo = useCallback((it: RailItem) => {
    if (it.screen && onScreenChange) onScreenChange(it.screen as ScreenMode);
    else if (it.product) onProductChange(it.product as EcosystemProduct);
  }, [onProductChange, onScreenChange]);
  const closeSheet = useCallback(() => setSheet(false), []);

  return (
    <>
      {!isMobile && <V3Rail className="static" active={railKey(activeProduct, activeScreen)} onGo={onGo} onAll={() => setSheet(true)} />}
      {!isMobile && showDashboard && dashboardProps && (
        <aside className="v3-dash" aria-label="Daily summary">
          <div className="v3-ph"><h2 className="v3-disp">{dailySummaryLabel(editionFromEnv())}</h2>
            <span className="r"><button type="button" className="v3-ib" onClick={() => setShowDashboard(false)} aria-label={T('Close')}><X size={13} /></button></span></div>
          <RightPanel {...dashboardProps} />
        </aside>
      )}
      {isMobile && !sheet && (
        <button type="button" onClick={() => setSheet(true)} className="v3-fab" aria-label={T('All modules')}><LayoutGrid size={20} strokeWidth={1.6} /></button>
      )}
      {isMobile && showDashboard && dashboardProps && (
        <div className="v3-sheet v3-dash-m" role="dialog" aria-label="Daily summary">
          <div className="hd"><h2 className="v3-disp">{dailySummaryLabel(editionFromEnv())}</h2>
            <button type="button" className="v3-ib" style={{ marginLeft: 'auto' }} onClick={() => setShowDashboard(false)} aria-label="Close"><X size={14} /></button></div>
          <RightPanel {...dashboardProps} />
        </div>
      )}
      <BusinessesSheet open={sheet} onClose={closeSheet} groups={groups} />
    </>
  );
}
