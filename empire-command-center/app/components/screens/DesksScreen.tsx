'use client';
import { useState } from 'react';
import { API } from '../../lib/api';
import { Desk } from '../../lib/types';
import { Bot, Send, Loader2, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react';

const DESK_COLORS: Record<string, { bg: string; border: string; text: string; icon: string }> = {
  forge:       { bg: '#f0fdf4', border: '#bbf7d0', text: '#16a34a', icon: '🏗' },
  market:      { bg: '#eff6ff', border: '#93c5fd', text: '#2563eb', icon: '🛍' },
  marketing:   { bg: '#fdf2f8', border: '#f9a8d4', text: '#ec4899', icon: '📣' },
  support:     { bg: '#faf5ff', border: '#e9d5ff', text: '#7c3aed', icon: '🎧' },
  sales:       { bg: '#fdf8eb', border: '#f5ecd0', text: '#b8960c', icon: '💰' },
  finance:     { bg: '#fffbeb', border: '#fde68a', text: '#d97706', icon: '📊' },
  clients:     { bg: '#ecfeff', border: '#a5f3fc', text: '#0891b2', icon: '👥' },
  contractors: { bg: '#fef3c7', border: '#fcd34d', text: '#b45309', icon: '🔧' },
  it:          { bg: '#f0f9ff', border: '#7dd3fc', text: '#0284c7', icon: '🖥' },
  website:     { bg: '#fdf2f8', border: '#fbcfe8', text: '#db2777', icon: '🌐' },
  legal:       { bg: '#f5f3ef', border: '#d8d3cb', text: '#555', icon: '⚖️' },
  lab:         { bg: '#fef9c3', border: '#fde047', text: '#a16207', icon: '🧪' },
};

interface Props {
  desks: Desk[];
  onSendTask: (msg: string) => void;
}

export default function DesksScreen({ desks, onSendTask }: Props) {
  const [expandedDesk, setExpandedDesk] = useState<string | null>(null);
  const [taskInput, setTaskInput] = useState('');
  const [taskDesk, setTaskDesk] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [taskResult, setTaskResult] = useState<{ desk: string; result: string; success: boolean } | null>(null);

  const submitTask = async (deskId: string) => {
    if (!taskInput.trim()) return;
    setSubmitting(true);
    setTaskResult(null);
    try {
      const res = await fetch(API + '/max/ai-desks/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ desk_id: deskId, task: taskInput }),
      });
      const data = await res.json();
      setTaskResult({
        desk: deskId,
        result: data.result || data.output || data.message || JSON.stringify(data),
        success: res.ok,
      });
      setTaskInput('');
    } catch (e: any) {
      setTaskResult({ desk: deskId, result: e.message, success: false });
    }
    setSubmitting(false);
  };

  const quickTask = (deskId: string, task: string) => {
    setTaskDesk(deskId);
    setExpandedDesk(deskId);
    setTaskInput(task);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-[#ede9fe] flex items-center justify-center">
          <Bot size={20} className="text-[#7c3aed]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#1a1a1a]">AI Desks</h1>
          <p className="text-xs text-[#777]">{desks.length} agents ready · Click to assign tasks</p>
        </div>
      </div>

      {/* Task result banner */}
      {taskResult && (
        <div className={`mb-4 p-4 rounded-xl border-2 ${taskResult.success ? 'bg-[#f0fdf4] border-[#bbf7d0]' : 'bg-[#fef2f2] border-[#fecaca]'}`}>
          <div className="flex items-center gap-2 mb-1">
            {taskResult.success ? <CheckCircle size={16} className="text-[#16a34a]" /> : <XCircle size={16} className="text-[#dc2626]" />}
            <span className="text-sm font-bold">{taskResult.success ? 'Task Completed' : 'Task Failed'}</span>
            <button onClick={() => setTaskResult(null)} className="ml-auto text-xs text-[#aaa] hover:text-[#555] cursor-pointer">dismiss</button>
          </div>
          <div className="text-xs text-[#555] whitespace-pre-wrap max-h-[200px] overflow-y-auto">{taskResult.result}</div>
        </div>
      )}

      {/* Desk Grid */}
      <div className="grid grid-cols-2 gap-3">
        {desks.map(d => {
          const colors = DESK_COLORS[d.id] || DESK_COLORS.lab;
          const isExpanded = expandedDesk === d.id;
          const deskData = d as any;
          return (
            <div key={d.id}
              className="rounded-xl border-2 transition-all overflow-hidden"
              style={{ borderColor: isExpanded ? colors.text : colors.border, background: 'white' }}>

              {/* Header */}
              <div className="p-4 cursor-pointer flex items-start gap-3"
                style={{ background: colors.bg }}
                onClick={() => setExpandedDesk(isExpanded ? null : d.id)}>
                <span className="text-2xl">{colors.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold" style={{ color: colors.text }}>{deskData.agent_name || d.name}</span>
                    <span className="text-[10px] font-mono text-[#999]">{d.id}</span>
                  </div>
                  <div className="text-[11px] text-[#555] mt-0.5 line-clamp-2">{d.persona || (deskData.description || '').slice(0, 80)}</div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="flex items-center gap-1 text-[9px] font-bold">
                      <span className={`w-2 h-2 rounded-full ${d.status === 'busy' ? 'bg-[#d97706]' : 'bg-[#16a34a]'}`} />
                      <span style={{ color: d.status === 'busy' ? '#d97706' : '#16a34a' }}>{(d.status || 'idle').toUpperCase()}</span>
                    </span>
                    {deskData.stats && (
                      <span className="text-[9px] text-[#aaa]">{deskData.stats.completed} done · {deskData.stats.failed} failed</span>
                    )}
                  </div>
                </div>
                {isExpanded ? <ChevronUp size={16} className="text-[#aaa] mt-1" /> : <ChevronDown size={16} className="text-[#aaa] mt-1" />}
              </div>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="p-4 border-t" style={{ borderColor: colors.border }}>
                  {/* Domains */}
                  {deskData.domains && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {(deskData.domains as string[]).slice(0, 8).map(dom => (
                        <span key={dom} className="text-[9px] px-2 py-0.5 rounded-full font-mono"
                          style={{ background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}>
                          {dom.replace(/_/g, ' ')}
                        </span>
                      ))}
                      {(deskData.domains as string[]).length > 8 && (
                        <span className="text-[9px] text-[#aaa]">+{(deskData.domains as string[]).length - 8} more</span>
                      )}
                    </div>
                  )}

                  {/* Quick tasks */}
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {getQuickTasks(d.id).map((qt, i) => (
                      <button key={i} onClick={() => quickTask(d.id, qt.task)}
                        className="text-[10px] px-2.5 py-1.5 rounded-lg border font-medium cursor-pointer transition-all hover:shadow-sm"
                        style={{ borderColor: colors.border, color: colors.text, background: 'white' }}>
                        {qt.label}
                      </button>
                    ))}
                  </div>

                  {/* Task input */}
                  <div className="flex gap-2">
                    <input
                      value={taskDesk === d.id ? taskInput : ''}
                      onChange={e => { setTaskDesk(d.id); setTaskInput(e.target.value); }}
                      onFocus={() => setTaskDesk(d.id)}
                      onKeyDown={e => e.key === 'Enter' && submitTask(d.id)}
                      placeholder={`Assign task to ${deskData.agent_name || d.name}...`}
                      className="flex-1 px-3 py-2.5 border-1.5 rounded-lg text-xs outline-none min-h-[40px] focus:shadow-[0_0_0_3px] transition-all"
                      style={{ borderColor: colors.border, background: 'white' }}
                    />
                    <button
                      onClick={() => submitTask(d.id)}
                      disabled={submitting || !(taskDesk === d.id && taskInput.trim())}
                      className="px-4 py-2.5 rounded-lg text-white text-xs font-bold min-h-[40px] flex items-center gap-1.5 disabled:opacity-40 transition-all"
                      style={{ background: colors.text }}>
                      {submitting && taskDesk === d.id ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                      Go
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {desks.length === 0 && (
        <div className="text-center py-16">
          <Bot size={48} className="text-[#d8d3cb] mx-auto mb-3" />
          <div className="text-base font-semibold text-[#aaa]">Loading AI Desks...</div>
          <div className="text-xs text-[#ccc] mt-1">Connecting to /api/v1/max/desks</div>
        </div>
      )}
    </div>
  );
}

function getQuickTasks(deskId: string): { label: string; task: string }[] {
  const tasks: Record<string, { label: string; task: string }[]> = {
    forge: [
      { label: '📋 List open quotes', task: 'List all open quotes with customer names and totals' },
      { label: '📊 Production status', task: 'Give me the current production status for all active jobs' },
      { label: '🪟 Fabric lookup', task: 'Look up available fabrics for drapery' },
    ],
    market: [
      { label: '📦 Active listings', task: 'Show all active marketplace listings' },
      { label: '💰 Pricing check', task: 'Run a competitor pricing analysis' },
      { label: '📬 Pending orders', task: 'List all pending orders needing fulfillment' },
    ],
    marketing: [
      { label: '📸 Draft IG post', task: 'Draft an Instagram post for our latest project' },
      { label: '📅 Schedule content', task: 'Show content calendar for this week' },
      { label: '#️⃣ Hashtag strategy', task: 'Suggest hashtags for home decor content' },
    ],
    support: [
      { label: '🎫 Open tickets', task: 'List all open support tickets' },
      { label: '📝 Draft response', task: 'Draft a response for the most recent support ticket' },
      { label: '⭐ Satisfaction', task: 'Show customer satisfaction summary' },
    ],
    sales: [
      { label: '🔥 Hot leads', task: 'Show all hot leads that need follow-up' },
      { label: '💬 Follow-up', task: 'Draft follow-up emails for pending proposals' },
      { label: '📈 Pipeline', task: 'Give me the current sales pipeline summary' },
    ],
    finance: [
      { label: '💰 P&L summary', task: 'Generate a profit and loss summary for this month' },
      { label: '📄 Overdue invoices', task: 'List all overdue invoices' },
      { label: '📊 Revenue report', task: 'Generate a revenue report for this quarter' },
    ],
    clients: [
      { label: '👤 Recent clients', task: 'Show recent client interactions' },
      { label: '📧 Thank you note', task: 'Draft a thank you note for our latest completed project' },
      { label: '🔍 Client lookup', task: 'Search for client information' },
    ],
    contractors: [
      { label: '📅 Availability', task: 'Check installer availability for next week' },
      { label: '⭐ Top rated', task: 'Show top rated contractors by reliability score' },
      { label: '💵 Pay rates', task: 'List contractor pay rates by specialty' },
    ],
    it: [
      { label: '🖥 Service health', task: 'Run a health check on all Empire services' },
      { label: '📊 Resource usage', task: 'Show current CPU, RAM, and disk usage' },
      { label: '📋 Recent logs', task: 'Show recent error logs' },
    ],
    website: [
      { label: '🔍 SEO check', task: 'Run an SEO check on the website' },
      { label: '📝 Update portfolio', task: 'Suggest new portfolio entries from recent projects' },
      { label: '⭐ Review response', task: 'Draft responses to recent Google reviews' },
    ],
    legal: [
      { label: '📄 Draft contract', task: 'Draft a standard client contract' },
      { label: '📋 Expiring docs', task: 'List documents expiring in the next 30 days' },
      { label: '⚖️ Compliance', task: 'Run a compliance check' },
    ],
    lab: [
      { label: '🧪 Test vision', task: 'Run a test of the AI vision pipeline' },
      { label: '🔊 Test TTS', task: 'Test text-to-speech with a sample' },
      { label: '💡 Suggest automation', task: 'Brainstorm new automation opportunities for the business' },
    ],
  };
  return tasks[deskId] || [{ label: '📋 Status', task: 'Give me your current status and what you can help with' }];
}
