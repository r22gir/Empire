'use client';
import React, { useState } from 'react';
import { EmpireSidebar } from './EmpireSidebar';
import { EmpireTopBar } from './EmpireTopBar';

interface EmpireShellProps {
  children: React.ReactNode;
  commitHash?: string;
  backendUrl?: string;
  backendLabel?: string;
}

export function EmpireShell({ children, commitHash = 'f535d53', backendUrl, backendLabel }: EmpireShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg-primary)',
      color: 'var(--text-primary)',
      fontFamily: 'var(--font-sans)',
    }}>
      <EmpireSidebar
        collapsed={sidebarCollapsed}
        onToggle={setSidebarCollapsed}
      />
      <EmpireTopBar
        commitHash={commitHash}
        sidebarWidth={sidebarCollapsed ? 64 : 280}
        backendUrl={backendUrl}
        backendLabel={backendLabel}
      />
      <main style={{
        marginLeft: sidebarCollapsed ? '64px' : '280px',
        paddingTop: 'var(--topbar-height)',
        minHeight: '100vh',
        transition: 'margin-left var(--transition-normal)',
      }}>
        <div style={{
          padding: 'var(--space-6)',
        }}>
          {children}
        </div>
      </main>
    </div>
  );
}