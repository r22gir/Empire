'use client';
import { useState } from 'react';
import { Sparkles, Send, Mail, Phone, Calendar, Loader2, Copy, Check, UserPlus } from 'lucide-react';
import { API_URL } from '@/lib/api';
import { type Lead } from '@/lib/deskData';

type AgentAction = 'follow_up_email' | 'lead_score' | 'objection_handler' | 'new_lead';

const ACTIONS: { value: AgentAction; label: string; icon: typeof Mail; description: string }[] = [
  { value: 'follow_up_email', label: 'Draft Follow-Up', icon: Mail,     description: 'Generate a professional follow-up email' },
  { value: 'lead_score',      label: 'Score Lead',      icon: Sparkles, description: 'AI analysis of lead quality and next steps' },
  { value: 'objection_handler', label: 'Handle Objection', icon: Phone, description: 'Get talking points for common objections' },
  { value: 'new_lead',        label: 'New Lead Script',  icon: UserPlus, description: 'Generate initial outreach for a new lead' },
];

interface SalesAgentProps {
  selectedLead?: Lead | null;
}

export default function SalesAgent({ selectedLead }: SalesAgentProps) {
  const [action, setAction] = useState<AgentAction>('follow_up_email');
  const [context, setContext] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [modelUsed, setModelUsed] = useState('');

  const runAgent = async () => {
    setLoading(true);
    setResult('');

    const leadContext = selectedLead
      ? `Lead: ${selectedLead.client}, Project: ${selectedLead.projectType}, Value: $${selectedLead.estimatedValue.toLocaleString()}, Stage: ${selectedLead.stage}, Last Contact: ${selectedLead.lastContact}, Notes: ${selectedLead.notes}`
      : '';

    const prompts: Record<AgentAction, string> = {
      follow_up_email: `Draft a professional, warm follow-up email for this client. Keep it concise (3-4 paragraphs max). Be specific about their project. ${leadContext}\nAdditional context: ${context || 'Standard follow-up'}`,
      lead_score: `Analyze this lead and provide: 1) Lead Score (1-10) with reasoning, 2) Recommended next action, 3) Estimated close probability, 4) Suggested timeline. ${leadContext}\nAdditional context: ${context || 'None'}`,
      objection_handler: `The client has this objection or concern: "${context || 'Price is too high'}". Provide 3-4 professional talking points to address this objection for a premium drapery/window treatment company. ${leadContext}`,
      new_lead: `Create an initial outreach script (phone + email) for a new lead interested in custom window treatments. ${context ? `Details: ${context}` : 'They found us through a referral.'}`,
    };

    try {
      const res = await fetch(`${API_URL}/max/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: prompts[action],
          desk: 'sales',
        }),
      });
      const data = await res.json();
      setResult(data.response || 'No response.');
      setModelUsed(data.model_used || '');
    } catch {
      setResult('Failed to connect. Check backend.');
    } finally {
      setLoading(false);
    }
  };

  const copyResult = () => {
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const currentAction = ACTIONS.find(a => a.value === action)!;

  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4" style={{ color: '#8B5CF6' }} />
        <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#8B5CF6' }}>
          Sales AI Agent
        </span>
        {selectedLead && (
          <span className="text-[10px] px-2 py-0.5 rounded-full ml-auto"
            style={{ background: 'var(--gold-pale)', color: 'var(--gold)', border: '1px solid var(--gold-border)' }}>
            {selectedLead.client}
          </span>
        )}
        {modelUsed && (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full"
            style={{ background: 'var(--raised)', color: 'var(--text-muted)' }}>
            via {modelUsed}
          </span>
        )}
      </div>

      {/* Action selector */}
      <div className="flex gap-1.5 mb-3 flex-wrap">
        {ACTIONS.map(a => (
          <button
            key={a.value}
            onClick={() => setAction(a.value)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition"
            style={{
              background: action === a.value ? 'rgba(139,92,246,0.15)' : 'var(--raised)',
              color: action === a.value ? '#8B5CF6' : 'var(--text-secondary)',
              border: action === a.value ? '1px solid rgba(139,92,246,0.3)' : '1px solid var(--border)',
            }}
          >
            <a.icon className="w-3 h-3" />
            {a.label}
          </button>
        ))}
      </div>

      <p className="text-[10px] mb-2" style={{ color: 'var(--text-muted)' }}>{currentAction.description}</p>

      {/* Context input */}
      <div className="flex gap-2 mb-3">
        <input
          value={context}
          onChange={e => setContext(e.target.value)}
          placeholder={
            action === 'objection_handler' ? 'Enter the objection (e.g., "Price is too high")' :
            action === 'new_lead' ? 'Describe the lead source and interest' :
            'Additional context (optional)'
          }
          className="flex-1 rounded-lg px-3 py-2 text-xs outline-none"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          onKeyDown={e => { if (e.key === 'Enter') runAgent(); }}
        />
        <button
          onClick={runAgent}
          disabled={loading}
          className="px-4 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shrink-0"
          style={{
            background: loading ? 'var(--raised)' : '#8B5CF6',
            color: loading ? 'var(--text-muted)' : '#fff',
          }}
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
          {loading ? 'Thinking...' : 'Run'}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="rounded-lg p-3 relative" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <button onClick={copyResult} className="absolute top-2 right-2 p-1.5 rounded-lg transition"
            style={{ color: copied ? '#22c55e' : 'var(--text-muted)' }}>
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <pre className="text-xs leading-relaxed whitespace-pre-wrap pr-8" style={{ color: 'var(--text-primary)' }}>
            {result}
          </pre>
        </div>
      )}
    </div>
  );
}
