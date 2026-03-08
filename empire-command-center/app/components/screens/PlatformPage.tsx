'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { Server, Activity, Brain, Users, Code, Shield, Cpu, HardDrive, Wifi, Database, Globe, Zap } from 'lucide-react';

export default function PlatformPage() {
  const [systemStats, setSystemStats] = useState<any>(null);
  const [services, setServices] = useState<any>(null);

  useEffect(() => {
    fetch(API + '/max/system').then(r => r.json()).then(setSystemStats).catch(() => {});
    fetch(API + '/max/services').then(r => r.json()).then(setServices).catch(() => {});
  }, []);

  const cpu = systemStats?.cpu_percent || 0;
  const ram = systemStats?.memory?.percent || 0;
  const disk = systemStats?.disk?.percent || 0;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-[#dbeafe] flex items-center justify-center">
          <Server size={20} className="text-[#2563eb]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#1a1a1a]">Platform</h1>
          <p className="text-xs text-[#777]">Infrastructure & SaaS Management · {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
        </div>
      </div>

      {/* System Health */}
      <div className="grid grid-cols-4 gap-3 mt-5 mb-6">
        <HealthCard icon={<Cpu size={18} />} label="CPU" value={`${cpu}%`} color={cpu > 80 ? '#dc2626' : cpu > 50 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<HardDrive size={18} />} label="RAM" value={`${ram}%`} color={ram > 85 ? '#dc2626' : ram > 60 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<Database size={18} />} label="Disk" value={`${disk}%`} color={disk > 90 ? '#dc2626' : disk > 70 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<Activity size={18} />} label="Uptime" value={systemStats?.uptime || '--'} color="#2563eb" />
      </div>

      <div className="grid grid-cols-[1fr_1fr] gap-4 mb-6">
        {/* Services Status */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Wifi size={15} className="text-[#2563eb]" /> Service Health
          </h3>
          <div className="space-y-2">
            <ServiceRow name="Backend API" port="8000" status="online" />
            <ServiceRow name="Empire App" port="3000" status="--" />
            <ServiceRow name="WorkroomForge" port="3001" status="--" />
            <ServiceRow name="LuxeForge" port="3002" status="--" />
            <ServiceRow name="Command Center" port="3009" status="online" />
            <ServiceRow name="OpenClaw" port="7878" status="--" />
            <ServiceRow name="Ollama" port="11434" status="--" />
          </div>
        </div>

        {/* AI Infrastructure */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Brain size={15} className="text-[#7c3aed]" /> AI Infrastructure
          </h3>
          <div className="space-y-2">
            <AIRow name="xAI Grok" type="Primary" status="active" color="#b8960c" />
            <AIRow name="Claude (Anthropic)" type="Fallback" status="standby" color="#7c3aed" />
            <AIRow name="Ollama (Local)" type="Local" status="--" color="#16a34a" />
            <AIRow name="Stability AI" type="Image Gen" status="error" color="#dc2626" />
            <AIRow name="Groq Whisper" type="STT" status="--" color="#2563eb" />
          </div>
          <div className="mt-4 p-3 rounded-lg bg-[#dbeafe] border border-[#93c5fd]">
            <div className="text-[10px] font-bold text-[#2563eb] mb-1">AI ROUTING</div>
            <div className="text-xs text-[#555]">Priority: xAI Grok &rarr; Claude &rarr; Ollama</div>
          </div>
        </div>
      </div>

      {/* API & Security */}
      <div className="grid grid-cols-[1fr_1fr] gap-4 mb-6">
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Code size={15} className="text-[#b8960c]" /> API Endpoints
          </h3>
          <div className="space-y-1.5">
            <EndpointRow method="POST" path="/max/chat/stream" desc="AI Chat (SSE)" />
            <EndpointRow method="GET" path="/quotes" desc="Quote List" />
            <EndpointRow method="POST" path="/files/upload" desc="File Upload" />
            <EndpointRow method="GET" path="/max/ai-desks" desc="AI Desks" />
            <EndpointRow method="GET" path="/max/system" desc="System Stats" />
            <EndpointRow method="GET" path="/memory/search" desc="Memory Search" />
          </div>
        </div>

        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Shield size={15} className="text-[#16a34a]" /> Security & Access
          </h3>
          <div className="space-y-2">
            <SecurityRow label="CORS" value="Open (*)" color="#d97706" />
            <SecurityRow label="Auth" value="None (local)" color="#d97706" />
            <SecurityRow label="Telegram Bot" value="Configured" color="#16a34a" />
            <SecurityRow label="API Keys" value="3 active" color="#16a34a" />
            <SecurityRow label="Guardrails" value="Enabled" color="#16a34a" />
          </div>
        </div>
      </div>

      {/* Ecosystem */}
      <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
        <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
          <Globe size={15} className="text-[#b8960c]" /> Empire Ecosystem
        </h3>
        <div className="grid grid-cols-4 gap-2">
          {[
            { name: 'MAX', icon: '⚡', color: '#b8960c' },
            { name: 'WorkroomForge', icon: '🏗', color: '#16a34a' },
            { name: 'CraftForge', icon: '🪵', color: '#ca8a04' },
            { name: 'LuxeForge', icon: '💎', color: '#7c3aed' },
            { name: 'SocialForge', icon: '📣', color: '#ec4899' },
            { name: 'OpenClaw', icon: '🤖', color: '#2563eb' },
            { name: 'VoiceForge', icon: '🎙', color: '#06b6d4' },
            { name: 'ShipForge', icon: '🚚', color: '#16a34a' },
          ].map(p => (
            <div key={p.name} className="p-3 rounded-lg border border-[#ece8e1] bg-[#faf9f7] text-center hover:border-[#b8960c] hover:bg-[#fdf8eb] transition-all cursor-pointer">
              <div className="text-xl mb-1">{p.icon}</div>
              <div className="text-[11px] font-semibold" style={{ color: p.color }}>{p.name}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function HealthCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-4 hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] transition-all">
      <div className="flex items-center gap-2 mb-2">
        <span style={{ color }}>{icon}</span>
        <span className="text-[11px] font-semibold text-[#777]">{label}</span>
      </div>
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="w-full h-1.5 rounded-full bg-[#f0ede8] mt-2 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: value.includes('%') ? value : '0%', background: color }} />
      </div>
    </div>
  );
}

function ServiceRow({ name, port, status }: { name: string; port: string; status: string }) {
  const isOnline = status === 'online';
  return (
    <div className="flex items-center justify-between p-2.5 rounded-lg border border-[#ece8e1] bg-[#faf9f7]">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-[#16a34a]' : 'bg-[#d8d3cb]'}`} />
        <span className="text-xs text-[#1a1a1a] font-medium">{name}</span>
        <span className="text-[9px] font-mono text-[#aaa]">:{port}</span>
      </div>
      <span className={`text-[10px] font-bold ${isOnline ? 'text-[#16a34a]' : 'text-[#aaa]'}`}>{status.toUpperCase()}</span>
    </div>
  );
}

function AIRow({ name, type, status, color }: { name: string; type: string; status: string; color: string }) {
  return (
    <div className="flex items-center justify-between p-2.5 rounded-lg border border-[#ece8e1] bg-[#faf9f7]">
      <div>
        <span className="text-xs font-medium text-[#1a1a1a]">{name}</span>
        <span className="text-[9px] text-[#aaa] ml-1.5">{type}</span>
      </div>
      <span className="text-[10px] font-bold" style={{ color }}>{status.toUpperCase()}</span>
    </div>
  );
}

function EndpointRow({ method, path, desc }: { method: string; path: string; desc: string }) {
  const methodColor = method === 'POST' ? '#ca8a04' : '#16a34a';
  return (
    <div className="flex items-center gap-2 p-2 rounded border border-[#ece8e1] bg-[#faf9f7]">
      <span className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded" style={{ color: methodColor, background: methodColor + '15' }}>{method}</span>
      <span className="text-[10px] font-mono text-[#555] flex-1 truncate">{path}</span>
      <span className="text-[9px] text-[#aaa]">{desc}</span>
    </div>
  );
}

function SecurityRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between p-2.5 rounded-lg border border-[#ece8e1] bg-[#faf9f7]">
      <span className="text-xs text-[#555]">{label}</span>
      <span className="text-[10px] font-bold" style={{ color }}>{value}</span>
    </div>
  );
}
