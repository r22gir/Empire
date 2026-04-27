'use client';
import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, MessageSquare, Users, Package, Wrench,
  BarChart3, Settings, HelpCircle, ChevronLeft, ChevronRight,
  Zap, Bot, Database, Globe, ShoppingCart, Layers,
  FileText, RefreshCw, Shield, Megaphone, ArrowRight
} from 'lucide-react';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: <LayoutDashboard size={18} /> },
  { label: 'MAX AI', href: '/max', icon: <Bot size={18} />, badge: '18 desks' },
  { label: 'CRM', href: '/crm', icon: <Users size={18} /> },
  { label: 'Finance', href: '/finance', icon: <BarChart3 size={18} /> },
  { label: 'Workroom', href: '/workroom', icon: <Wrench size={18} /> },
  { label: 'ArchiveForge', href: '/archiveforge-life', icon: <Package size={18} /> },
  { label: 'RecoveryForge', href: '/recoveryforge', icon: <RefreshCw size={18} /> },
  { label: 'RelistApp', href: '/relistapp', icon: <ArrowRight size={18} /> },
  { label: 'Drawing Studio', href: '/drawing', icon: <Layers size={18} /> },
  { label: 'SocialForge', href: '/social', icon: <Megaphone size={18} /> },
  { label: 'VendorOps', href: '/vendorops', icon: <Shield size={18} /> },
  { label: 'CraftForge', href: '/craftforge', icon: <Wrench size={18} /> },
  { label: 'ApostApp', href: '/apostapp', icon: <FileText size={18} /> },
];

interface EmpireSidebarProps {
  collapsed?: boolean;
  onToggle?: (collapsed: boolean) => void;
}

export function EmpireSidebar({ collapsed = false, onToggle }: EmpireSidebarProps) {
  const pathname = usePathname();

  return (
    <div style={{
      width: collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
      minWidth: collapsed ? 'var(--sidebar-collapsed-width)' : 'var(--sidebar-width)',
      height: '100vh',
      background: 'var(--gradient-sidebar)',
      borderRight: '1px solid var(--border-default)',
      display: 'flex',
      flexDirection: 'column',
      transition: 'width var(--transition-normal)',
      overflow: 'hidden',
      position: 'fixed',
      left: 0,
      top: 0,
      zIndex: 100,
    }}>
      {/* Logo area */}
      <div style={{
        padding: 'var(--space-5) var(--space-4)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        minHeight: 'var(--topbar-height)',
      }}>
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              background: 'var(--accent-gradient)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Zap size={16} color="#fff" />
            </div>
            <span style={{
              fontSize: 'var(--text-lg)',
              fontWeight: 700,
              color: 'var(--text-primary)',
              letterSpacing: '-0.5px',
            }}>Empire</span>
          </div>
        )}
        {collapsed && (
          <div style={{
            width: '28px',
            height: '28px',
            background: 'var(--accent-gradient)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Zap size={16} color="#fff" />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden', padding: 'var(--space-3) 0' }}>
        <div style={{ padding: '0 var(--space-3)' }}>
          {!collapsed && (
            <p style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              color: 'var(--text-faint)',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              padding: 'var(--space-2) var(--space-3)',
              marginBottom: 'var(--space-1)',
            }}>Main</p>
          )}
          {navItems.map((item) => {
            const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--space-3)',
                  padding: collapsed ? '10px' : '9px var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '2px',
                  textDecoration: 'none',
                  color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                  background: active ? 'var(--panel-active)' : 'transparent',
                  border: active ? '1px solid var(--border-accent)' : '1px solid transparent',
                  transition: 'all var(--transition-fast)',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  fontSize: 'var(--text-sm)',
                  fontWeight: active ? 600 : 400,
                }}
                onMouseEnter={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = 'var(--panel-hover)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }
                }}
              >
                <span style={{ flexShrink: 0, opacity: active ? 1 : 0.7 }}>{item.icon}</span>
                {!collapsed && (
                  <>
                    <span style={{ flex: 1 }}>{item.label}</span>
                    {item.badge && (
                      <span style={{
                        fontSize: 'var(--text-xs)',
                        background: active ? 'var(--accent-primary-bg)' : 'rgba(255,255,255,0.06)',
                        color: active ? 'var(--accent-primary)' : 'var(--text-muted)',
                        padding: '1px 7px',
                        borderRadius: 'var(--radius-full)',
                        fontWeight: 500,
                      }}>{item.badge}</span>
                    )}
                  </>
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Collapse toggle */}
      <div style={{
        padding: 'var(--space-3)',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        <button
          onClick={() => onToggle?.(!collapsed)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-2)',
            padding: '8px',
            borderRadius: 'var(--radius-md)',
            background: 'transparent',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: 'var(--text-xs)',
            transition: 'all var(--transition-fast)',
          }}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </div>
  );
}