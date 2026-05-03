'use client';
import React, { useState } from 'react';
import {
  Bot, Code2, BarChart3, Users, Wrench, ShoppingCart,
  Headphones, Globe, Shield, FileText, Lightbulb,
  UserPlus, ClipboardCheck, Bug, TestTube, Database,
  Layers, MessageSquare, Settings
} from 'lucide-react';
import { API } from '@/lib/api';

interface Desk {
  id: string;
  name: string;
  agent: string;
  icon: React.ReactNode;
  description: string;
}

const ALL_DESKS: Desk[] = [
  { id: 'codedesk', name: 'Code Desk', agent: 'Atlas', icon: <Code2 size={16} />, description: 'Code & craft tasks' },
  { id: 'marketdesk', name: 'Marketplace Desk', agent: 'Atlas', icon: <ShoppingCart size={16} />, description: 'Marketplace listings' },
  { id: 'marketingdesk', name: 'Marketing Desk', agent: 'Atlas', icon: <MessageSquare size={16} />, description: 'Marketing & campaigns' },
  { id: 'supportdesk', name: 'Support Desk', agent: 'Atlas', icon: <Headphones size={16} />, description: 'Customer support' },
  { id: 'salesdesk', name: 'Sales Desk', agent: 'Atlas', icon: <BarChart3 size={16} />, description: 'Sales pipeline' },
  { id: 'financedesk', name: 'Finance Desk', agent: 'Atlas', icon: <Database size={16} />, description: 'Finance & invoices' },
  { id: 'clientsdesk', name: 'Clients Desk', agent: 'Atlas', icon: <Users size={16} />, description: 'Client management' },
  { id: 'contractorsdesk', name: 'Contractors Desk', agent: 'Atlas', icon: <Wrench size={16} />, description: 'Contractor management' },
  { id: 'itdesk', name: 'IT Desk', agent: 'Atlas', icon: <Bot size={16} />, description: 'IT support' },
  { id: 'websitedesk', name: 'Website Desk', agent: 'Atlas', icon: <Globe size={16} />, description: 'Web & content' },
  { id: 'legaldesk', name: 'Legal Desk', agent: 'Raven', icon: <Shield size={16} />, description: 'Legal documents' },
  { id: 'labdesk', name: 'Lab / QA Desk', agent: 'Phoenix', icon: <TestTube size={16} />, description: 'Testing & QA' },
  { id: 'innovationdesk', name: 'Innovation Desk', agent: 'Atlas', icon: <Lightbulb size={16} />, description: 'Research & development' },
  { id: 'intakedesk', name: 'Intake Desk', agent: 'Atlas', icon: <UserPlus size={16} />, description: 'Client intake flow' },
  { id: 'analyticsdesk', name: 'Analytics Desk', agent: 'Raven', icon: <BarChart3 size={16} />, description: 'Analytics & reporting' },
  { id: 'qualitydesk', name: 'Quality Desk', agent: 'Phoenix', icon: <ClipboardCheck size={16} />, description: 'Quality assurance' },
  { id: 'qadesk', name: 'QA Desk', agent: 'Phoenix', icon: <Bug size={16} />, description: 'QA & bug tracking' },
];

interface DeskSelectorProps {
  activeDesk: string;
  onDeskChange: (deskId: string) => void;
  compact?: boolean;
}

export function DeskSelector({ activeDesk, onDeskChange, compact = false }: DeskSelectorProps) {
  const [switching, setSwitching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDeskClick = async (deskId: string) => {
    if (deskId === activeDesk) return;
    setSwitching(true);
    setError(null);
    try {
      const r = await fetch(`${API}/max/desk/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ desk: deskId }),
      });
      if (r.ok) {
        onDeskChange(deskId);
      } else {
        setError('Failed to switch desk');
      }
    } catch {
      setError('Connection error');
    } finally {
      setSwitching(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--space-2)',
      height: '100%',
      overflow: 'hidden',
    }}>
      {!compact && (
        <div style={{ padding: '0 var(--space-2) var(--space-2)' }}>
          <p style={{
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            color: 'var(--text-faint)',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}>AI Desks</p>
        </div>
      )}

      <div style={{
        display: 'grid',
        gridTemplateColumns: compact ? '1fr 1fr' : '1fr 1fr 1fr',
        gap: 'var(--space-2)',
        overflowY: 'auto',
        padding: compact ? 'var(--space-2)' : 0,
        flex: 1,
      }}>
        {ALL_DESKS.map((desk) => {
          const isActive = desk.id === activeDesk;
          return (
            <button
              key={desk.id}
              onClick={() => handleDeskClick(desk.id)}
              disabled={switching}
              title={`Chat with ${desk.name} — ${desk.agent}`}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                gap: '4px',
                padding: compact ? 'var(--space-2)' : 'var(--space-3)',
                background: isActive
                  ? 'linear-gradient(145deg, rgba(99,102,241,0.2), rgba(139,92,246,0.1))'
                  : 'rgba(255,255,255,0.04)',
                border: isActive
                  ? '1px solid rgba(99,102,241,0.5)'
                  : '1px solid rgba(255,255,255,0.08)',
                borderRadius: 'var(--radius-md)',
                cursor: switching ? 'not-allowed' : 'pointer',
                transition: 'all var(--transition-base)',
                opacity: switching && !isActive ? 0.5 : 1,
                boxShadow: isActive
                  ? '0 0 20px rgba(99,102,241,0.25), inset 0 1px 0 rgba(255,255,255,0.15)'
                  : 'none',
                position: 'relative',
                overflow: 'hidden',
                textAlign: 'left',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
                  e.currentTarget.style.boxShadow = 'var(--shadow-card-hover)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                  e.currentTarget.style.boxShadow = 'none';
                }
              }}
            >
              {isActive && (
                <div style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: '2px',
                  background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))',
                }} />
              )}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
              }}>
                {desk.icon}
                <span style={{
                  fontSize: compact ? 'var(--text-xs)' : 'var(--text-sm)',
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                }}>
                  {desk.name}
                </span>
              </div>
              <span style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--text-muted)',
                opacity: 0.8,
              }}>
                {desk.agent}
              </span>
            </button>
          );
        })}
      </div>

      {error && (
        <div style={{
          padding: 'var(--space-2)',
          background: 'var(--error-bg)',
          border: '1px solid var(--error-border)',
          borderRadius: 'var(--radius-sm)',
          fontSize: 'var(--text-xs)',
          color: 'var(--error)',
        }}>
          {error}
        </div>
      )}
    </div>
  );
}