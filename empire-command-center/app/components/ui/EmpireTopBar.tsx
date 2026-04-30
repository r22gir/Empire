'use client';
import React, { useState, useEffect } from 'react';
import { Bell, User, GitCommit, Wifi, WifiOff, Activity, Cpu, HardDrive } from 'lucide-react';
import { EmpireStatusPill } from './EmpireStatusPill';

interface ProviderStatus {
  id: string;
  name: string;
  status: 'online' | 'degraded' | 'offline';
  latency?: string;
}

interface EmpireTopBarProps {
  commitHash?: string;
  onMenuToggle?: () => void;
  sidebarWidth?: number;
}

export function EmpireTopBar({ commitHash, onMenuToggle, sidebarWidth = 280 }: EmpireTopBarProps) {
  const [backendOk, setBackendOk] = useState(false);
  const [frontendOk, setFrontendOk] = useState(false);

  useEffect(() => {
    // Health polling
    const checkHealth = async () => {
      try {
        const r = await fetch('http://localhost:8000/health');
        setBackendOk(r.ok);
      } catch {
        setBackendOk(false);
      }
      try {
        // Check v10 frontend on port 3010, not stable on 3005
        const r2 = await fetch('http://localhost:3010');
        setFrontendOk(r2.ok);
      } catch {
        setFrontendOk(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const shortHash = commitHash ? commitHash.slice(0, 7) : 'f535d53';

  return (
    <div style={{
      height: 'var(--topbar-height)',
      background: 'rgba(30,41,59,0.85)',
      backdropFilter: 'blur(20px)',
      borderBottom: '1px solid var(--border-default)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 var(--space-5)',
      position: 'fixed',
      top: 0,
      left: sidebarWidth,
      right: 0,
      zIndex: 90,
      transition: 'left var(--transition-normal)',
    }}>
      {/* Left: system indicators */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <GitCommit size={14} style={{ color: 'var(--text-muted)' }} />
          <code style={{
            fontSize: 'var(--text-xs)',
            fontFamily: 'var(--font-mono)',
            color: 'var(--accent-primary)',
            background: 'var(--accent-primary-bg)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-accent)',
          }}>
            {shortHash}
          </code>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginLeft: 'var(--space-2)' }}>
          <EmpireStatusPill
            status={backendOk ? 'success' : 'error'}
            label={backendOk ? 'Backend 8000' : 'Backend DOWN'}
            size="sm"
            pulse={backendOk}
          />
          <EmpireStatusPill
            status={frontendOk ? 'success' : 'error'}
            label={frontendOk ? 'v10 Frontend 3010' : 'v10 Frontend DOWN'}
            size="sm"
            pulse={frontendOk}
          />
          <EmpireStatusPill
            status="success"
            label="MAX"
            size="sm"
            pulse
          />
          <EmpireStatusPill
            status="success"
            label="OpenClaw"
            size="sm"
          />
        </div>
      </div>

      {/* Right: user controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <button
          style={{
            position: 'relative',
            background: 'transparent',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '6px',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            transition: 'all var(--transition-fast)',
          }}
        >
          <Bell size={16} />
          <span style={{
            position: 'absolute',
            top: '4px',
            right: '4px',
            width: '6px',
            height: '6px',
            background: 'var(--error)',
            borderRadius: '50%',
          }} />
        </button>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: '6px 12px',
          background: 'var(--panel-bg)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          cursor: 'pointer',
        }}>
          <div style={{
            width: '26px',
            height: '26px',
            background: 'var(--accent-gradient)',
            borderRadius: 'var(--radius-full)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <User size={14} color="#fff" />
          </div>
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontWeight: 500 }}>
            Founder
          </span>
        </div>
      </div>
    </div>
  );
}