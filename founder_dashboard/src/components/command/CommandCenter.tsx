'use client';
import { useState, useEffect, useCallback } from 'react';
import { useChat } from '@/hooks/useChat';
import { useChatHistory } from '@/hooks/useChatHistory';
import { useSystemData } from '@/hooks/useSystemData';
import { useDesk } from '@/hooks/useDesk';
import { API_URL } from '@/lib/api';
import { AINotification, BrowseFile } from '@/lib/types';
import { DeskId } from '@/lib/deskData';

import LeftColumn from './LeftColumn';
import RightColumn from './RightColumn';
import BottomBar from './BottomBar';
import DeskGrid from './DeskGrid';
import ActiveDeskView from './ActiveDeskView';

export default function CommandCenter() {
  const history = useChatHistory();
  const sys     = useSystemData();
  const desk    = useDesk();

  const chat = useChat({
    onSave: async (messages, chatId) => history.saveConversation(messages, chatId),
  });

  /* ── File state ─────────────────────────────────────────── */
  const [selectedImage,  setSelectedImage]  = useState<{ name: string; category: string } | null>(null);
  const [pastedPreview,  setPastedPreview]  = useState<string | null>(null);
  const [pastedFile,     setPastedFile]     = useState<File | null>(null);
  const [uploading,      setUploading]      = useState(false);
  const [previewImage,   setPreviewImage]   = useState<string | null>(null);

  /* ── Desk grid modal ──────────────────────────────────────── */
  const [showDeskGrid, setShowDeskGrid] = useState(false);

  /* ── Suggestion input ─────────────────────────────────────── */
  const [suggestedInput, setSuggestedInput] = useState('');

  /* ── Browser modal ──────────────────────────────────────── */
  const [showBrowser,        setShowBrowser]        = useState(false);
  const [browseFiles,        setBrowseFiles]        = useState<BrowseFile[]>([]);
  const [browsePath,         setBrowsePath]         = useState('~');
  const [selectedBrowseFile, setSelectedBrowseFile] = useState<string | null>(null);

  /* ── Tasks modal ────────────────────────────────────────── */
  const [showTasks,   setShowTasks]   = useState(false);
  const [showNewTask, setShowNewTask] = useState(false);
  const [newTask,     setNewTask]     = useState({ title: '', description: '', desk_id: '', priority: 5 });

  /* ── Notification modal ─────────────────────────────────── */
  const [selectedNotif, setSelectedNotif] = useState<AINotification | null>(null);
  const [notifReply,    setNotifReply]    = useState('');

  /* ── Paste handler ──────────────────────────────────────── */
  useEffect(() => {
    const handle = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          e.preventDefault();
          const file = items[i].getAsFile();
          if (file) { setPastedPreview(URL.createObjectURL(file)); setPastedFile(file); }
          return;
        }
      }
    };
    document.addEventListener('paste', handle);
    return () => document.removeEventListener('paste', handle);
  }, []);

  /* ── Keyboard shortcuts (Alt+1-9, Alt+0, Ctrl+Alt+1-3) ── */
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return;

      const altMap: Record<string, DeskId> = {
        '1': 'operations', '2': 'finance', '3': 'sales', '4': 'design',
        '5': 'estimating', '6': 'clients', '7': 'contractors', '8': 'support',
        '9': 'marketing', '0': 'website',
      };
      const ctrlAltMap: Record<string, DeskId> = {
        '1': 'it', '2': 'legal', '3': 'lab',
      };

      if (e.altKey && !e.ctrlKey && altMap[e.key]) {
        e.preventDefault();
        desk.openDesk(altMap[e.key]);
        setShowDeskGrid(false);
      } else if (e.altKey && e.ctrlKey && ctrlAltMap[e.key]) {
        e.preventDefault();
        desk.openDesk(ctrlAltMap[e.key]);
        setShowDeskGrid(false);
      } else if (e.key === 'Escape') {
        if (showDeskGrid) setShowDeskGrid(false);
        else if (desk.activeDesk) desk.closeDesk();
      }
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [desk, showDeskGrid]);

  /* ── File operations ────────────────────────────────────── */
  const uploadPastedImage = async () => {
    if (!pastedFile) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', pastedFile, 'pasted_' + Date.now() + '.png');
      const res  = await fetch(API_URL + '/files/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.status === 'success') {
        sys.fetchFiles();
        setSelectedImage({ name: data.filename, category: 'images' });
        setPastedPreview(null); setPastedFile(null);
      }
    } catch { /* */ } finally { setUploading(false); }
  };

  const uploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData(); fd.append('file', file);
      const res  = await fetch(API_URL + '/files/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.status === 'success') {
        sys.fetchFiles();
        setSelectedImage({ name: data.filename, category: data.category });
      }
    } catch { /* */ } finally { setUploading(false); e.target.value = ''; }
  };

  const deleteFile = async (category: string, filename: string) => {
    if (!confirm('Delete ' + filename + '?')) return;
    try {
      const res = await fetch(API_URL + '/files/delete/' + category + '/' + filename, { method: 'DELETE' });
      if ((await res.json()).status === 'deleted') {
        sys.fetchFiles();
        if (selectedImage?.name === filename) setSelectedImage(null);
      }
    } catch { /* */ }
  };

  const openFile = (category: string, filename: string) => {
    const url = API_URL + '/files/view/' + category + '/' + encodeURIComponent(filename);
    if (category === 'images') setPreviewImage(url); else window.open(url, '_blank');
  };

  /* ── File browser ───────────────────────────────────────── */
  const browseDirApi = async (path: string) => {
    try {
      const res  = await fetch(API_URL + '/files/browse?path=' + encodeURIComponent(path));
      const data = await res.json();
      setBrowseFiles(data.files || []);
      setBrowsePath(data.current_path || path);
    } catch { /* */ }
  };

  const openFileBrowser = () => { setShowBrowser(true); browseDirApi('~'); };

  const selectFileForUpload = async () => {
    if (!selectedBrowseFile) return;
    setShowBrowser(false); setUploading(true);
    try {
      const res  = await fetch(API_URL + '/files/upload-from-path', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedBrowseFile }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        sys.fetchFiles();
        setSelectedImage({ name: data.filename, category: data.category });
      }
    } catch { /* */ } finally { setUploading(false); setSelectedBrowseFile(null); }
  };

  /* ── Chat ───────────────────────────────────────────────── */
  const handleSelectConversation = useCallback(async (id: string) => {
    const msgs = await history.loadConversation(id);
    chat.loadMessages(msgs, id);
  }, [history, chat]);

  const handleNewChat = useCallback(() => {
    history.startNewChat();
    chat.loadMessages([], null);
  }, [history, chat]);

  const handleSend = (input: string) => {
    chat.sendMessage(input, sys.selectedModel, selectedImage, undefined, desk.activeDesk || undefined);
    setSelectedImage(null);
  };

  /* ── Helpers ────────────────────────────────────────────── */
  const formatSize      = (b: number) => b > 1_048_576 ? (b / 1_048_576).toFixed(1) + ' MB' : b > 1_024 ? (b / 1_024).toFixed(1) + ' KB' : b + ' B';
  const taskStatusColor = (s: string) => s === 'completed' ? 'text-green-400' : s === 'in_progress' ? 'text-yellow-400' : s === 'failed' ? 'text-red-400' : 'text-gray-400';
  const getDeskName     = (id: string) => sys.desks.find(d => d.id === id)?.name || id;

  const modalOverlay = "fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-4";
  const modalBox     = "rounded-xl w-full flex flex-col overflow-hidden shadow-2xl";

  return (
    <div
      className="h-screen flex flex-col overflow-hidden empire-ambient"
      style={{ background: 'var(--void)', color: 'var(--text-primary)' }}
    >
      {/* ════ IMAGE PREVIEW MODAL ════════════════════════════ */}
      {previewImage && (
        <div className={modalOverlay + ' bg-black/95'} onClick={() => setPreviewImage(null)}>
          <button className="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center text-lg" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>×</button>
          <img src={previewImage} alt="Preview" className="max-w-full max-h-full object-contain rounded-xl" />
        </div>
      )}

      {/* ════ FILE BROWSER MODAL ═════════════════════════════ */}
      {showBrowser && (
        <div className={modalOverlay}>
          <div className={modalBox + ' max-w-2xl max-h-[80vh]'} style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
              <h3 className="font-semibold text-sm" style={{ color: 'var(--gold)' }}>Browse Files</h3>
              <button onClick={() => setShowBrowser(false)} className="text-lg" style={{ color: 'var(--text-secondary)' }}>×</button>
            </div>
            <div className="px-3 py-2 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border)', background: 'var(--raised)' }}>
              <button
                onClick={() => browseDirApi(browsePath.split('/').slice(0, -1).join('/') || '/')}
                className="px-2.5 py-1 rounded-lg text-xs transition"
                style={{ background: 'var(--elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}
              >↑ Up</button>
              <span className="text-xs truncate flex-1 font-mono" style={{ color: 'var(--text-muted)' }}>{browsePath}</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {browseFiles.map((f, i) => (
                <div
                  key={i}
                  onClick={() => f.isDir ? browseDirApi(f.path) : setSelectedBrowseFile(f.path)}
                  className="flex items-center gap-3 p-2 rounded-lg cursor-pointer transition"
                  style={{ background: selectedBrowseFile === f.path ? 'var(--gold-pale)' : 'transparent', border: selectedBrowseFile === f.path ? '1px solid var(--gold-border)' : '1px solid transparent' }}
                  onMouseEnter={e => { if (selectedBrowseFile !== f.path) e.currentTarget.style.background = 'var(--hover)'; }}
                  onMouseLeave={e => { if (selectedBrowseFile !== f.path) e.currentTarget.style.background = 'transparent'; }}
                >
                  <span className="text-xl">{f.isDir ? '📁' : f.name.match(/\.(png|jpg|jpeg|gif|webp)$/i) ? '🖼️' : f.name.match(/\.(m4a|mp3|wav|ogg|flac|aac)$/i) ? '🎵' : '📄'}</span>
                  <span className="flex-1 truncate text-sm">{f.name}</span>
                  {!f.isDir && <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{formatSize(f.size)}</span>}
                </div>
              ))}
              {browseFiles.length === 0 && <p className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>Empty folder</p>}
            </div>
            <div className="px-4 py-3 flex justify-end gap-2" style={{ borderTop: '1px solid var(--border)' }}>
              <button onClick={() => setShowBrowser(false)} className="px-4 py-2 rounded-lg text-sm transition" style={{ background: 'var(--raised)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}>Cancel</button>
              <button onClick={selectFileForUpload} disabled={!selectedBrowseFile} className="px-4 py-2 rounded-lg text-sm font-semibold transition" style={{ background: selectedBrowseFile ? 'var(--gold)' : 'var(--elevated)', color: selectedBrowseFile ? '#0a0a0a' : 'var(--text-muted)' }}>Upload Selected</button>
            </div>
          </div>
        </div>
      )}

      {/* ════ TASKS MODAL ════════════════════════════════════ */}
      {showTasks && (
        <div className={modalOverlay}>
          <div className={modalBox + ' max-w-3xl max-h-[80vh]'} style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
              <h3 className="font-semibold text-sm" style={{ color: 'var(--gold)' }}>Tasks</h3>
              <div className="flex gap-2">
                <button onClick={() => setShowNewTask(true)} className="px-3 py-1.5 rounded-lg text-xs font-semibold transition" style={{ background: 'var(--gold)', color: '#0a0a0a' }}>+ New Task</button>
                <button onClick={() => setShowTasks(false)} className="text-lg px-2" style={{ color: 'var(--text-secondary)' }}>×</button>
              </div>
            </div>
            {showNewTask && (
              <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)', background: 'var(--raised)' }}>
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <input type="text" placeholder="Task title…" value={newTask.title} onChange={e => setNewTask({ ...newTask, title: e.target.value })} className="rounded-lg px-3 py-2 text-sm outline-none" style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} />
                  <select value={newTask.desk_id} onChange={e => setNewTask({ ...newTask, desk_id: e.target.value })} className="rounded-lg px-3 py-2 text-sm outline-none cursor-pointer" style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}>
                    <option value="">Auto-assign</option>
                    {sys.desks.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
                <textarea placeholder="Description…" value={newTask.description} onChange={e => setNewTask({ ...newTask, description: e.target.value })} className="w-full rounded-lg px-3 py-2 text-sm mb-3 resize-none outline-none" style={{ background: 'var(--elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} rows={2} />
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2 text-sm">
                    <span style={{ color: 'var(--text-muted)' }}>Priority:</span>
                    <input type="range" min="1" max="10" value={newTask.priority} onChange={e => setNewTask({ ...newTask, priority: parseInt(e.target.value) })} className="w-24" style={{ accentColor: 'var(--gold)' }} />
                    <span style={{ color: 'var(--gold)' }}>{newTask.priority}</span>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => setShowNewTask(false)} className="px-3 py-1.5 rounded-lg text-sm transition" style={{ background: 'var(--elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}>Cancel</button>
                    <button onClick={() => { if (newTask.title.trim()) { sys.createTask(newTask.title, newTask.description, newTask.desk_id, newTask.priority); setNewTask({ title: '', description: '', desk_id: '', priority: 5 }); setShowNewTask(false); } }} className="px-3 py-1.5 rounded-lg text-sm font-semibold transition" style={{ background: 'var(--gold)', color: '#0a0a0a' }}>Create</button>
                  </div>
                </div>
              </div>
            )}
            <div className="flex-1 overflow-y-auto p-4">
              {sys.tasks.length === 0 ? (
                <p className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>No tasks yet</p>
              ) : (
                <div className="space-y-2">
                  {sys.tasks.map(task => (
                    <div key={task.id} className="rounded-xl p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={'text-xs font-semibold ' + taskStatusColor(task.status)}>{task.status.replace('_', ' ').toUpperCase()}</span>
                            <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>P{task.priority}</span>
                          </div>
                          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{task.title}</p>
                          <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{task.description}</p>
                          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Assigned: {getDeskName(task.desk_id)}</p>
                        </div>
                        {task.status === 'in_progress' && (
                          <div className="flex gap-1.5 ml-3">
                            <button onClick={() => sys.completeTask(task.id)} className="px-2 py-1 rounded-lg text-xs font-semibold" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.2)' }}>✓</button>
                            <button onClick={() => sys.failTask(task.id)} className="px-2 py-1 rounded-lg text-xs font-semibold" style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>✗</button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ════ NOTIFICATION MODAL ═════════════════════════════ */}
      {selectedNotif && (
        <div className={modalOverlay} onClick={() => setSelectedNotif(null)}>
          <div className={modalBox + ' max-w-2xl max-h-[80vh]'} style={{ background: 'var(--surface)', border: '1px solid var(--border)' }} onClick={e => e.stopPropagation()}>
            <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)', background: selectedNotif.priority === 'high' ? 'rgba(239,68,68,0.08)' : 'var(--gold-pale)' }}>
              <div className="flex items-center gap-3">
                <span className="text-2xl">{selectedNotif.source === 'MAX' ? '🧠' : selectedNotif.source === 'System' ? '⚙️' : '💰'}</span>
                <div>
                  <h2 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{selectedNotif.title}</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{selectedNotif.source} · {selectedNotif.type.replace('_', ' ')}</p>
                </div>
              </div>
              <button onClick={() => setSelectedNotif(null)} className="text-xl" style={{ color: 'var(--text-secondary)' }}>×</button>
            </div>
            <div className="px-5 py-4 overflow-y-auto" style={{ maxHeight: '50vh' }}>
              <p className="text-sm leading-relaxed mb-5" style={{ color: 'var(--text-primary)' }}>{selectedNotif.message}</p>
              {selectedNotif.context?.options && (
                <div className="mb-5">
                  <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>Quick Actions:</p>
                  <div className="flex gap-2 flex-wrap">
                    {selectedNotif.context.options.map((opt: string) => (
                      <button key={opt} onClick={() => { sys.respondToNotification(selectedNotif.id, opt); setSelectedNotif(null); }} className="px-4 py-2 rounded-lg text-sm font-medium transition" style={{ background: opt.toLowerCase().includes('approve') ? 'rgba(34,197,94,0.15)' : opt.toLowerCase().includes('reject') ? 'rgba(239,68,68,0.15)' : 'var(--raised)', color: opt.toLowerCase().includes('approve') ? '#22c55e' : opt.toLowerCase().includes('reject') ? '#ef4444' : 'var(--text-primary)', border: '1px solid var(--border)' }}>{opt}</button>
                    ))}
                  </div>
                </div>
              )}
              <textarea value={notifReply} onChange={e => setNotifReply(e.target.value)} placeholder="Custom reply…" className="w-full rounded-xl px-4 py-3 text-sm resize-none outline-none" style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} rows={3} />
              <div className="flex justify-between items-center mt-3">
                <button onClick={() => { sys.markNotificationRead(selectedNotif.id); setSelectedNotif(null); }} className="text-xs transition" style={{ color: 'var(--text-muted)' }}>Mark read</button>
                <button onClick={() => { if (notifReply.trim()) { sys.respondToNotification(selectedNotif.id, notifReply); setNotifReply(''); setSelectedNotif(null); } }} disabled={!notifReply.trim()} className="px-4 py-2 rounded-lg text-sm font-semibold transition" style={{ background: notifReply.trim() ? 'var(--gold)' : 'var(--raised)', color: notifReply.trim() ? '#0a0a0a' : 'var(--text-muted)' }}>Send</button>
              </div>
            </div>
            <div className="px-5 py-2.5 flex justify-between items-center" style={{ borderTop: '1px solid var(--border)', background: 'var(--raised)' }}>
              <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{new Date(selectedNotif.created_at).toLocaleString()}</span>
              <button onClick={() => { sys.dismissNotification(selectedNotif.id); setSelectedNotif(null); }} className="text-xs transition" style={{ color: '#ef4444' }}>Dismiss</button>
            </div>
          </div>
        </div>
      )}

      {/* ════ DESK GRID MODAL ════════════════════════════════ */}
      <DeskGrid
        isOpen={showDeskGrid}
        onClose={() => setShowDeskGrid(false)}
        onSelectDesk={desk.openDesk}
        activeDesk={desk.activeDesk}
      />

      {/* ════ MAIN CONTENT AREA ══════════════════════════════ */}
      <div className="flex-1 flex min-h-0">
        {desk.activeDesk ? (
          <ActiveDeskView activeDesk={desk.activeDesk} onClose={desk.closeDesk} />
        ) : (
          <>
            <LeftColumn
              isStreaming={chat.isStreaming}
              streamingContent={chat.streamingContent}
              messages={chat.messages}
              backendOnline={sys.backendOnline}
              selectedModel={sys.selectedModel}
              models={sys.models}
              onOpenDeskGrid={() => setShowDeskGrid(true)}
              conversations={history.conversations}
              activeConversationId={history.activeId}
              onSelectConversation={handleSelectConversation}
              onNewChat={handleNewChat}
              onDeleteConversation={(id) => { history.deleteConversation(id); if (history.activeId === id) chat.loadMessages([], null); }}
              onRenameConversation={history.renameConversation}
              onSuggest={setSuggestedInput}
            />
            <RightColumn
              systemStats={sys.systemStats}
              serviceHealth={sys.serviceHealth}
              backendOnline={sys.backendOnline}
              models={sys.models}
            />
          </>
        )}
      </div>

      {/* ════ BOTTOM BAR (always visible) ════════════════════ */}
      <BottomBar
        onSend={handleSend}
        isStreaming={chat.isStreaming}
        onStop={chat.stopStreaming}
        onOpenBrowser={openFileBrowser}
        onFileUpload={uploadFile}
        uploading={uploading}
        pastedPreview={pastedPreview}
        onUploadPasted={uploadPastedImage}
        onCancelPasted={() => { setPastedPreview(null); setPastedFile(null); }}
        selectedImage={selectedImage}
        onClearImage={() => setSelectedImage(null)}
        backendOnline={sys.backendOnline}
        selectedModel={sys.selectedModel}
        models={sys.models}
        onModelChange={sys.setSelectedModel}
        suggestedInput={suggestedInput}
        onClearSuggestion={() => setSuggestedInput('')}
      />
    </div>
  );
}
