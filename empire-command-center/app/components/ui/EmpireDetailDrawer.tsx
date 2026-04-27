'use client';
import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface EmpireDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

const sizeMap = {
  sm: '320px',
  md: '420px',
  lg: '540px',
  xl: '720px',
};

export function EmpireDetailDrawer({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  size = 'md',
}: EmpireDetailDrawerProps) {
  const [visible, setVisible] = useState(false);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setRendered(true);
      requestAnimationFrame(() => setVisible(true));
    } else {
      setVisible(false);
      const timer = setTimeout(() => setRendered(false), 350);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!rendered) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`empire-drawer-backdrop ${visible ? 'visible' : ''}`}
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(4px)',
          zIndex: 399,
          opacity: visible ? 1 : 0,
          transition: 'opacity 300ms ease',
        }}
      />

      {/* Drawer panel */}
      <div
        className={`empire-drawer-panel ${visible ? 'open' : ''}`}
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: sizeMap[size],
          maxWidth: '95vw',
          background: 'var(--panel-bg)',
          borderLeft: '1px solid var(--border-subtle)',
          zIndex: 400,
          display: 'flex',
          flexDirection: 'column',
          transform: visible ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 350ms cubic-bezier(0.16, 1, 0.3, 1)',
          boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--space-5) var(--space-6)',
          borderBottom: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}>
          <div>
            <h2 style={{
              fontSize: 'var(--text-lg)',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: subtitle ? '2px' : 0,
            }}>{title}</h2>
            {subtitle && (
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>{subtitle}</p>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'var(--panel-hover)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              color: 'var(--text-secondary)',
              transition: 'all var(--transition-fast)',
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: 'var(--space-5) var(--space-6)',
        }}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div style={{
            padding: 'var(--space-4) var(--space-6)',
            borderTop: '1px solid var(--border-subtle)',
            flexShrink: 0,
          }}>
            {footer}
          </div>
        )}
      </div>
    </>
  );
}