'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { API } from '../../lib/api';
import { Send, RefreshCw, MessageCircle, AlertTriangle, CheckCircle2, XCircle, Camera, Mic } from 'lucide-react';

interface TelegramStatus {
  configured: boolean;
  bot_token_set: boolean;
  chat_id_set: boolean;
}

interface TelegramMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  type?: 'text' | 'photo' | 'voice';
  image?: string;
  image_filename?: string;
}

function MessageBubble({ role, content, timestamp, isPhoto, isVoice, imageFilename }: {
  role: string;
  content: string;
  timestamp?: string;
  isPhoto?: boolean;
  isVoice?: boolean;
  imageFilename?: string | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const isUser = role === 'user';
  const isLong = content.length > 400;

  // Clean up vision prefix from display
  let displayContent = content;
  if (isPhoto && content.includes('VISION MEASUREMENT RESULTS')) {
    const visionMatch = content.match(/VISION MEASUREMENT RESULTS[\s\S]*$/);
    if (visionMatch) {
      displayContent = visionMatch[0];
    }
  }

  const truncated = isLong && !expanded ? displayContent.slice(0, 400) + '...' : displayContent;

  return (
    <div style={{
      padding: '10px 14px',
      borderRadius: 12,
      border: '1px solid #ece8e0',
      background: isUser ? '#fdf8eb' : '#faf9f7',
    }}>
      <div className="flex items-center gap-2 mb-1.5">
        <span style={{
          fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 4,
          background: isUser ? '#b8960c20' : '#2563eb20',
          color: isUser ? '#b8960c' : '#2563eb',
        }}>
          {isUser ? 'FOUNDER' : 'MAX'}
        </span>
        {isPhoto && (
          <span className="flex items-center gap-1" style={{ fontSize: 9, color: '#7c3aed', fontWeight: 600 }}>
            <Camera size={10} /> Photo
          </span>
        )}
        {isVoice && (
          <span className="flex items-center gap-1" style={{ fontSize: 9, color: '#16a34a', fontWeight: 600 }}>
            <Mic size={10} /> Voice
          </span>
        )}
        {timestamp && (
          <span style={{ fontSize: 9, color: '#bbb', marginLeft: 'auto' }}>
            {new Date(timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {/* Image preview */}
      {imageFilename && (
        <div style={{ marginBottom: 8 }}>
          <img
            src={`${API}/max/telegram/image/${imageFilename}`}
            alt="Attachment"
            style={{ maxWidth: 280, maxHeight: 200, borderRadius: 8, border: '1px solid #ece8e0', cursor: 'pointer' }}
            onClick={() => window.open(`${API}/max/telegram/image/${imageFilename}`, '_blank')}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        </div>
      )}

      <div style={{ fontSize: 12, color: '#555', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {truncated}
      </div>

      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          style={{ fontSize: 10, color: '#b8960c', fontWeight: 600, marginTop: 4, cursor: 'pointer', background: 'none', border: 'none', padding: 0 }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  );
}

export default function TelegramScreen() {
  const [status, setStatus] = useState<TelegramStatus | null>(null);
  const [messages, setMessages] = useState<TelegramMessage[]>([]);
  const [totalMessages, setTotalMessages] = useState(0);
  const [newMessage, setNewMessage] = useState('');
  const [isUrgent, setIsUrgent] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<{ success: boolean; message: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/telegram/status');
      if (res.ok) setStatus(await res.json());
    } catch { /* silent */ }
  }, []);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/telegram/history?limit=50');
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
        setTotalMessages(data.total || 0);
      }
    } catch { /* silent */ }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchStatus(), fetchHistory()]);
    setLoading(false);
  }, [fetchStatus, fetchHistory]);

  useEffect(() => {
    refresh();
    // Auto-refresh every 30 seconds
    refreshTimer.current = setInterval(() => {
      fetchHistory();
    }, 30000);
    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, [refresh, fetchHistory]);

  const handleSend = async () => {
    if (!newMessage.trim() || sending) return;
    setSending(true);
    setSendResult(null);
    try {
      const res = await fetch(API + '/max/telegram/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: newMessage, urgent: isUrgent }),
      });
      const data = await res.json();
      if (data.success) {
        setSendResult({ success: true, message: 'Message sent to Telegram' });
        setNewMessage('');
        setIsUrgent(false);
        setTimeout(fetchHistory, 1500);
      } else {
        setSendResult({ success: false, message: data.detail || 'Failed to send' });
      }
    } catch (e: any) {
      setSendResult({ success: false, message: e.message || 'Network error' });
    } finally {
      setSending(false);
      setTimeout(() => setSendResult(null), 4000);
    }
  };

  const isConnected = status?.configured && status?.bot_token_set && status?.chat_id_set;

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-[#dbeafe] flex items-center justify-center">
          <MessageCircle size={20} className="text-[#2563eb]" />
        </div>
        <div className="flex-1">
          <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Telegram</h1>
          <p style={{ fontSize: 13, color: '#aaa', margin: 0 }}>MAX Bot &middot; Founder Communication Channel</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg hover:bg-[#ece8e0] transition-colors cursor-pointer" title="Refresh">
          <RefreshCw size={16} className={`text-[#999] ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Status Card */}
      <div className="section-label" style={{ marginTop: 20, marginBottom: 8 }}>Bot Status</div>
      <div className="empire-card" style={{ marginBottom: 16 }}>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-[#16a34a]' : 'bg-[#dc2626]'}`} />
          <div className="flex-1">
            <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            <div style={{ fontSize: 11, color: '#999' }}>
              {status ? (
                <>
                  Token: {status.bot_token_set ? 'Set' : 'Missing'} &middot; Chat ID: {status.chat_id_set ? 'Set' : 'Missing'}
                </>
              ) : 'Loading...'}
            </div>
          </div>
          <span className={`status-pill ${isConnected ? 'ok' : 'overdue'}`}>
            {isConnected ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
        {!isConnected && status && (
          <div style={{ marginTop: 12, padding: 10, borderRadius: 8, background: '#fef2f2', border: '1px solid #fecaca', fontSize: 11, color: '#dc2626' }}>
            <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4 }} />
            Set TELEGRAM_BOT_TOKEN and TELEGRAM_FOUNDER_CHAT_ID environment variables on the backend to enable the Telegram bot.
          </div>
        )}
      </div>

      <div className="grid grid-cols-[1fr_1fr] gap-4 mb-6">
        {/* Send Message */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <Send size={15} className="text-[#b8960c]" /> Send Message
          </h3>
          <textarea
            value={newMessage}
            onChange={e => setNewMessage(e.target.value)}
            placeholder={isConnected ? 'Type a message to send via Telegram...' : 'Telegram not configured'}
            disabled={!isConnected}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            style={{
              width: '100%', minHeight: 80, padding: 10, borderRadius: 8,
              border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 12,
              resize: 'vertical', fontFamily: 'inherit', color: '#1a1a1a',
              outline: 'none',
            }}
          />
          <div className="flex items-center justify-between mt-3">
            <label className="flex items-center gap-2 cursor-pointer" style={{ fontSize: 11, color: '#999' }}>
              <input
                type="checkbox"
                checked={isUrgent}
                onChange={e => setIsUrgent(e.target.checked)}
                disabled={!isConnected}
                style={{ accentColor: '#dc2626' }}
              />
              Urgent alert
            </label>
            <button
              onClick={handleSend}
              disabled={!isConnected || sending || !newMessage.trim()}
              style={{
                padding: '6px 16px', borderRadius: 8, border: 'none',
                background: isConnected && newMessage.trim() ? '#b8960c' : '#d8d3cb',
                color: '#fff', fontSize: 12, fontWeight: 600, cursor: isConnected ? 'pointer' : 'default',
                opacity: sending ? 0.6 : 1,
              }}
            >
              {sending ? 'Sending...' : 'Send'}
            </button>
          </div>
          {sendResult && (
            <div className="flex items-center gap-2 mt-2" style={{ fontSize: 11, color: sendResult.success ? '#16a34a' : '#dc2626' }}>
              {sendResult.success ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
              {sendResult.message}
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
            <MessageCircle size={15} className="text-[#2563eb]" /> Conversation Stats
          </h3>
          <div className="space-y-3">
            <StatRow label="Total Messages" value={String(totalMessages)} />
            <StatRow label="User Messages" value={String(messages.filter(m => m.role === 'user').length)} />
            <StatRow label="Assistant Replies" value={String(messages.filter(m => m.role === 'assistant').length)} />
            <StatRow label="Photos" value={String(messages.filter(m => m.type === 'photo' || m.image || m.image_filename).length)} />
            <StatRow label="Voice" value={String(messages.filter(m => m.type === 'voice').length)} />
            <StatRow label="Bot Status" value={isConnected ? 'Polling' : 'Stopped'} color={isConnected ? '#16a34a' : '#dc2626'} />
          </div>
        </div>
      </div>

      {/* Recent Messages */}
      <div className="section-label" style={{ marginBottom: 8 }}>
        Recent Messages
        <span style={{ fontWeight: 400, color: '#bbb', marginLeft: 8, fontSize: 11 }}>
          {totalMessages} total &middot; auto-refreshes every 30s
        </span>
      </div>
      <div className="empire-card">
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, fontSize: 12, color: '#999' }}>
            {loading ? 'Loading messages...' : 'No Telegram messages yet'}
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {[...messages].reverse().slice(0, 50).map((msg, i) => {
              const isPhoto = msg.type === 'photo' || !!msg.image || !!msg.image_filename || msg.content.includes('VISION MEASUREMENT RESULTS');
              const isVoice = msg.type === 'voice';
              const imageFile = msg.image || msg.image_filename;
              // For legacy messages without metadata, try to detect image filename from content
              const legacyImageMatch = !imageFile && isPhoto ? msg.content.match(/telegram_[\w.-]+\.(jpg|png|jpeg)/i) : null;
              const displayImage = imageFile || (legacyImageMatch ? legacyImageMatch[0] : null);

              return (
                <MessageBubble
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  timestamp={msg.timestamp}
                  isPhoto={isPhoto}
                  isVoice={isVoice}
                  imageFilename={displayImage}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function StatRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between" style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
      <span style={{ fontSize: 12, color: '#555' }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 700, color: color || '#1a1a1a' }}>{value}</span>
    </div>
  );
}
