'use client';
import { useState } from 'react';
import { Sparkles, Copy, Check, Instagram, Globe, Hash, FileText, Loader2 } from 'lucide-react';
import { API_URL } from '@/lib/api';

type ContentType = 'caption' | 'hashtags' | 'blog_outline' | 'ad_copy';

const CONTENT_TYPES: { value: ContentType; label: string; icon: typeof Instagram; placeholder: string }[] = [
  { value: 'caption',      label: 'Social Caption',  icon: Instagram, placeholder: 'Describe the post or photo (e.g., "Before/after of a master bedroom drape install")' },
  { value: 'hashtags',     label: 'Hashtag Set',     icon: Hash,      placeholder: 'Topic or post theme (e.g., "luxury motorized shades smart home")' },
  { value: 'blog_outline', label: 'Blog Outline',    icon: FileText,  placeholder: 'Blog topic (e.g., "5 window treatment trends for 2026")' },
  { value: 'ad_copy',      label: 'Ad Copy',         icon: Globe,     placeholder: 'Product or service to advertise (e.g., "Free in-home consultation for custom drapes")' },
];

const PLATFORMS = ['Instagram', 'Facebook', 'TikTok', 'Pinterest', 'Blog', 'Google Ads'];

export default function ContentGenerator() {
  const [contentType, setContentType] = useState<ContentType>('caption');
  const [platform, setPlatform] = useState('Instagram');
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [modelUsed, setModelUsed] = useState('');

  const generate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResult('');
    setCopied(false);

    const systemMsg = `You are a marketing content specialist for a premium custom drapery and window treatments company. Generate ${contentType.replace('_', ' ')} for ${platform}. Be creative, professional, and on-brand with luxury home décor. Keep it concise and ready to post.`;

    try {
      const res = await fetch(`${API_URL}/max/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Generate ${contentType.replace('_', ' ')} for ${platform}: ${prompt}`,
          desk: 'marketing',
          history: [{ role: 'system', content: systemMsg }],
        }),
      });
      const data = await res.json();
      setResult(data.response || 'No content generated.');
      setModelUsed(data.model_used || '');
    } catch {
      setResult('Failed to generate content. Check backend connection.');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(result);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const typeConfig = CONTENT_TYPES.find(t => t.value === contentType)!;

  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="w-4 h-4" style={{ color: '#A855F7' }} />
        <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#A855F7' }}>
          AI Content Generator
        </span>
        {modelUsed && (
          <span className="text-[10px] font-mono ml-auto px-2 py-0.5 rounded-full"
            style={{ background: 'var(--raised)', color: 'var(--text-muted)' }}>
            via {modelUsed}
          </span>
        )}
      </div>

      {/* Content type selector */}
      <div className="flex gap-1.5 mb-3">
        {CONTENT_TYPES.map(ct => (
          <button
            key={ct.value}
            onClick={() => setContentType(ct.value)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition"
            style={{
              background: contentType === ct.value ? 'rgba(168,85,247,0.15)' : 'var(--raised)',
              color: contentType === ct.value ? '#A855F7' : 'var(--text-secondary)',
              border: contentType === ct.value ? '1px solid rgba(168,85,247,0.3)' : '1px solid var(--border)',
            }}
          >
            <ct.icon className="w-3 h-3" />
            {ct.label}
          </button>
        ))}
      </div>

      {/* Platform selector */}
      <div className="flex gap-1 mb-3">
        {PLATFORMS.map(p => (
          <button
            key={p}
            onClick={() => setPlatform(p)}
            className="px-2 py-1 rounded text-[10px] transition"
            style={{
              background: platform === p ? 'var(--gold-pale)' : 'transparent',
              color: platform === p ? 'var(--gold)' : 'var(--text-muted)',
              border: platform === p ? '1px solid var(--gold-border)' : '1px solid transparent',
            }}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2 mb-3">
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder={typeConfig.placeholder}
          className="flex-1 rounded-lg px-3 py-2 text-xs resize-none outline-none"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          rows={2}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); generate(); } }}
        />
        <button
          onClick={generate}
          disabled={loading || !prompt.trim()}
          className="px-4 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shrink-0"
          style={{
            background: loading ? 'var(--raised)' : prompt.trim() ? '#A855F7' : 'var(--elevated)',
            color: prompt.trim() && !loading ? '#fff' : 'var(--text-muted)',
          }}
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
          {loading ? 'Generating...' : 'Generate'}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="rounded-lg p-3 relative" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <button
            onClick={copyToClipboard}
            className="absolute top-2 right-2 p-1.5 rounded-lg transition"
            style={{ color: copied ? '#22c55e' : 'var(--text-muted)' }}
            title="Copy to clipboard"
          >
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
