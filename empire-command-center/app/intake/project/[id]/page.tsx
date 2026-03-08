'use client';
import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import {
  ArrowLeft, MapPin, Camera, Ruler, FileText, MessageSquare,
  Send, Download, CheckCircle, Clock,
} from 'lucide-react';
import IntakeNav from '../../../components/intake/IntakeNav';
import PhotoUploader from '../../../components/intake/PhotoUploader';
import { intakeFetch, getToken } from '../../../lib/intake-auth';

const statusConfig: Record<string, { label: string; color: string; bg: string; icon: any }> = {
  draft: { label: 'Draft', color: '#777', bg: '#f5f3ef', icon: Clock },
  submitted: { label: 'Submitted — Under Review', color: '#2563eb', bg: '#dbeafe', icon: Clock },
  'quote-ready': { label: 'Quote Ready', color: '#c9a84c', bg: '#fdf8eb', icon: FileText },
  approved: { label: 'Approved', color: '#16a34a', bg: '#dcfce7', icon: CheckCircle },
  'in-production': { label: 'In Production', color: '#7c3aed', bg: '#ede9fe', icon: Clock },
  installed: { label: 'Installed', color: '#16a34a', bg: '#dcfce7', icon: CheckCircle },
};

export default function ProjectDetail() {
  const router = useRouter();
  const params = useParams();
  const projectId = params.id as string;

  const [user, setUser] = useState<any>(null);
  const [project, setProject] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  const loadProject = async () => {
    try {
      const proj = await intakeFetch(`/projects/${projectId}`);
      setProject(proj);
    } catch (_err) {
      router.push('/intake/dashboard');
    }
  };

  useEffect(() => {
    if (!getToken()) { router.push('/intake/login'); return; }
    const init = async () => {
      try {
        const me = await intakeFetch('/me');
        setUser(me);
        await loadProject();
      } catch (_err) {
        router.push('/intake/login');
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [projectId, router]);

  const sendMessage = async () => {
    if (!message.trim()) return;
    setSending(true);
    try {
      await intakeFetch(`/projects/${projectId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: message }),
      });
      setMessage('');
      await loadProject();
    } catch (_err) {
      // ignore
    } finally {
      setSending(false);
    }
  };

  if (loading || !project) {
    return (
      <div className="min-h-screen bg-[#faf9f7] flex items-center justify-center">
        <div className="text-sm text-[#aaa]">Loading...</div>
      </div>
    );
  }

  const status = statusConfig[project.status] || statusConfig.draft;
  const StatusIcon = status.icon;
  const photos = project.photos || [];
  const measurements = project.measurements || [];
  const messages = project.messages || [];

  return (
    <div className="min-h-screen bg-[#faf9f7]">
      <IntakeNav user={user} />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <button
          onClick={() => router.push('/intake/dashboard')}
          className="flex items-center gap-1.5 text-xs text-[#777] hover:text-[#c9a84c] transition-colors mb-4"
        >
          <ArrowLeft size={14} /> Back to Projects
        </button>

        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded"
                style={{ color: status.color, background: status.bg }}
              >
                <StatusIcon size={10} /> {status.label}
              </span>
              <span className="text-[10px] text-[#aaa]">{project.intake_code}</span>
            </div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">{project.name}</h1>
            {project.address && (
              <div className="flex items-center gap-1 text-xs text-[#777] mt-1">
                <MapPin size={12} /> {project.address}
              </div>
            )}
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {project.treatment && (
            <div className="bg-white border border-[#e5e0d8] rounded-lg p-3">
              <div className="text-[10px] text-[#aaa] mb-0.5">Treatment</div>
              <div className="text-xs font-semibold text-[#1a1a1a] capitalize">{project.treatment}</div>
            </div>
          )}
          {project.style && (
            <div className="bg-white border border-[#e5e0d8] rounded-lg p-3">
              <div className="text-[10px] text-[#aaa] mb-0.5">Style</div>
              <div className="text-xs font-semibold text-[#1a1a1a] capitalize">{project.style}</div>
            </div>
          )}
          {project.scope && (
            <div className="bg-white border border-[#e5e0d8] rounded-lg p-3">
              <div className="text-[10px] text-[#aaa] mb-0.5">Scope</div>
              <div className="text-xs font-semibold text-[#1a1a1a] capitalize">{project.scope.replace(/-/g, ' ')}</div>
            </div>
          )}
          <div className="bg-white border border-[#e5e0d8] rounded-lg p-3">
            <div className="text-[10px] text-[#aaa] mb-0.5">Photos</div>
            <div className="text-xs font-semibold text-[#1a1a1a]">{photos.length}</div>
          </div>
        </div>

        {/* Quote PDF */}
        {project.quote_pdf && (
          <div className="bg-[#fdf8eb] border border-[#c9a84c]/20 rounded-xl p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText size={18} className="text-[#c9a84c]" />
                <div>
                  <div className="text-sm font-semibold text-[#1a1a1a]">Your Quote is Ready</div>
                  <div className="text-[10px] text-[#777]">Review your 3-tier proposal and choose an option</div>
                </div>
              </div>
              <a
                href={`http://localhost:8000${project.quote_pdf}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 text-xs font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors flex items-center gap-1.5"
              >
                <Download size={14} /> View Quote
              </a>
            </div>
          </div>
        )}

        {/* Photos section */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <Camera size={16} className="text-[#c9a84c]" />
            <h2 className="text-sm font-bold text-[#1a1a1a]">Photos</h2>
          </div>
          {project.status === 'draft' ? (
            <PhotoUploader projectId={projectId} photos={photos} onUpload={loadProject} />
          ) : photos.length > 0 ? (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {photos.map((p: any, i: number) => (
                <div key={i} className="relative aspect-square rounded-lg overflow-hidden bg-[#f5f3ef] border border-[#e5e0d8]">
                  <img
                    src={`http://localhost:8000${p.path}`}
                    alt={p.original_name}
                    className="w-full h-full object-cover"
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[#aaa]">No photos uploaded.</p>
          )}
        </div>

        {/* Measurements section */}
        {measurements.length > 0 && (
          <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 mb-4">
            <div className="flex items-center gap-2 mb-4">
              <Ruler size={16} className="text-[#c9a84c]" />
              <h2 className="text-sm font-bold text-[#1a1a1a]">Measurements</h2>
            </div>
            <div className="space-y-2">
              {measurements.map((m: any, i: number) => (
                <div key={i} className="flex items-center gap-3 text-xs p-2.5 rounded-lg bg-[#faf9f7] border border-[#e5e0d8]">
                  <span className="font-semibold text-[#1a1a1a] min-w-[100px]">{m.room || `Window ${i + 1}`}</span>
                  <span className="text-[#777]">{m.width}&quot; W &times; {m.height}&quot; H</span>
                  {m.reference && m.reference !== 'none' && (
                    <span className="text-[10px] text-[#aaa] px-1.5 py-0.5 bg-[#f5f3ef] rounded">
                      ref: {m.reference}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {project.notes && (
          <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 mb-4">
            <h2 className="text-sm font-bold text-[#1a1a1a] mb-2">Notes</h2>
            <p className="text-xs text-[#777] whitespace-pre-wrap">{project.notes}</p>
          </div>
        )}

        {/* Messages */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare size={16} className="text-[#c9a84c]" />
            <h2 className="text-sm font-bold text-[#1a1a1a]">Messages</h2>
          </div>

          {messages.length > 0 ? (
            <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
              {messages.map((msg: any, i: number) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg text-xs ${
                    msg.from === 'client'
                      ? 'bg-[#fdf8eb] border border-[#c9a84c]/20 ml-8'
                      : 'bg-[#f5f3ef] border border-[#e5e0d8] mr-8'
                  }`}
                >
                  <div className="font-semibold text-[#1a1a1a] mb-1">
                    {msg.from === 'client' ? 'You' : 'Empire Team'}
                  </div>
                  <div className="text-[#555]">{msg.text}</div>
                  {msg.timestamp && (
                    <div className="text-[9px] text-[#aaa] mt-1">
                      {new Date(msg.timestamp).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-[#aaa] mb-4">No messages yet. Send one to start the conversation.</p>
          )}

          <div className="flex items-center gap-2">
            <input
              type="text"
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
              placeholder="Type a message..."
              className="flex-1 px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
            />
            <button
              onClick={sendMessage}
              disabled={sending || !message.trim()}
              className="px-4 py-2.5 bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors disabled:opacity-50"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
