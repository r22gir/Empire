'use client';

import { useState, useEffect, useRef } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Message { role: 'user' | 'assistant'; content: string; model?: string; image?: string; }
interface Desk { id: string; name: string; description: string; status: string; }
interface AIModel { id: string; name: string; available: boolean; }
interface UploadedFile { name: string; category: string; size: number; }
interface BrowseFile { name: string; path: string; isDir: boolean; size: number; }
interface Task { id: string; title: string; description: string; desk_id: string; status: string; priority: number; created_at: string; }
interface Reminder { id: string; text: string; dueDate: string; priority: 'low' | 'medium' | 'high'; completed: boolean; createdAt: string; }
interface AINotification { id: string; source: string; type: string; title: string; message: string; priority: string; action_url: string; read: boolean; created_at: string; context?: { options?: string[]; [key: string]: any }; }

export default function FounderDashboard() {
  const [messages, setMessages] = useState<Message[]>([{ role: 'assistant', content: "Hello! I'm MAX, your AI Assistant Manager.\n\nTip: Ctrl+V to paste images, Shift+Enter for new lines!" }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [desks, setDesks] = useState<Desk[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState('claude');
  const [stats, setStats] = useState({ total_completed: 0, active_tasks: 0, pending_tasks: 0, total_failed: 0 });
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [showFiles, setShowFiles] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<{name: string, category: string} | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [showBrowser, setShowBrowser] = useState(false);
  const [browseFiles, setBrowseFiles] = useState<BrowseFile[]>([]);
  const [browsePath, setBrowsePath] = useState('~');
  const [selectedBrowseFile, setSelectedBrowseFile] = useState<string | null>(null);
  const [pastedPreview, setPastedPreview] = useState<string | null>(null);
  const [pastedFile, setPastedFile] = useState<File | null>(null);
  const [showTasks, setShowTasks] = useState(false);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [showNewTask, setShowNewTask] = useState(false);
  const [newTask, setNewTask] = useState({ title: '', description: '', desk_id: '', priority: 5 });
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [aiNotifications, setAiNotifications] = useState<AINotification[]>([]);
  const [selectedNotif, setSelectedNotif] = useState<AINotification | null>(null);
  const [notifReply, setNotifReply] = useState('');
  const [showReminders, setShowReminders] = useState(false);
  const [newReminder, setNewReminder] = useState<{text: string; dueDate: string; priority: 'low'|'medium'|'high'}>({ text: '', dueDate: '', priority: 'medium' });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { fetchDesks(); fetchModels(); fetchStats(); fetchFiles(); fetchTasks(); const interval = setInterval(() => { fetchDesks(); fetchStats(); fetchFiles(); fetchTasks(); }, 30000); return () => clearInterval(interval); }, []);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.startsWith('image/')) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) {
            const url = URL.createObjectURL(file);
            setPastedPreview(url);
            setPastedFile(file);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Image pasted! Type your question or click Upload Now.' }]);
          }
          return;
        }
      }
    };
    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, []);

  const fetchDesks = async () => { try { const res = await fetch(API_URL + '/max/desks'); const data = await res.json(); setDesks(data.desks || []); } catch (e) { console.error(e); } };
  const fetchModels = async () => { try { const res = await fetch(API_URL + '/max/models'); const data = await res.json(); setModels(data.models || []); } catch (e) { console.error(e); } };
  const fetchStats = async () => { try { const res = await fetch(API_URL + '/max/stats'); const data = await res.json(); setStats(data.stats || {}); } catch (e) { console.error(e); } };
  const fetchFiles = async () => { try { const res = await fetch(API_URL + '/files/list'); const data = await res.json(); setFiles(data.files || []); } catch (e) { console.error(e); } };
  const fetchTasks = async () => { try { const res = await fetch(API_URL + '/max/tasks'); const data = await res.json(); setTasks(data.tasks || []); } catch (e) { console.error(e); } };

  // Reminders - load from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('empire-reminders');
    if (saved) setReminders(JSON.parse(saved));
  }, []);
  useEffect(() => { localStorage.setItem('empire-reminders', JSON.stringify(reminders)); }, [reminders]);
  
  // Fetch AI notifications from backend
  const fetchNotifications = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/notifications?unread_only=false');
      const data = await res.json();
      setAiNotifications(data.notifications || []);
    } catch (e) { console.log('Notifications fetch error:', e); }
  };
  useEffect(() => { fetchNotifications(); const interval = setInterval(fetchNotifications, 10000); return () => clearInterval(interval); }, []);
  
  const markNotificationRead = async (id: string) => {
    await fetch(`http://localhost:8000/api/v1/notifications/\${id}/read`, { method: 'PATCH' });
    fetchNotifications();
  };
  const dismissNotification = async (id: string) => {
    await fetch(`http://localhost:8000/api/v1/notifications/${id}`, { method: 'DELETE' });
    fetchNotifications();
  };
  const respondToNotification = async (id: string, action: string) => {
    await fetch(`http://localhost:8000/api/v1/notifications/respond/${id}?action=${encodeURIComponent(action)}`, { method: 'POST' });
    fetchNotifications();
  };
  const addReminder = () => {
    if (!newReminder.text.trim()) return;
    setReminders(prev => [...prev, { id: Date.now().toString(), text: newReminder.text, dueDate: newReminder.dueDate, priority: newReminder.priority, completed: false, createdAt: new Date().toISOString() }]);
    setNewReminder({ text: '', dueDate: '', priority: 'medium' });
  };
  const toggleReminder = (id: string) => setReminders(prev => prev.map(r => r.id === id ? { ...r, completed: !r.completed } : r));
  const deleteReminder = (id: string) => setReminders(prev => prev.filter(r => r.id !== id));
  const getPriorityColor = (p: string) => p === 'high' ? 'text-red-400' : p === 'medium' ? 'text-yellow-400' : 'text-green-400';

  const createTask = async () => {
    if (!newTask.title.trim()) return;
    try {
      const res = await fetch(API_URL + '/max/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTask)
      });
      if (res.ok) {
        setNewTask({ title: '', description: '', desk_id: '', priority: 5 });
        setShowNewTask(false);
        fetchTasks();
        fetchStats();
      }
    } catch (e) { console.error(e); }
  };

  const completeTask = async (taskId: string) => {
    try {
      await fetch(API_URL + '/max/tasks/' + taskId + '/complete', { method: 'POST' });
      fetchTasks();
      fetchStats();
    } catch (e) { console.error(e); }
  };

  const failTask = async (taskId: string) => {
    try {
      await fetch(API_URL + '/max/tasks/' + taskId + '/fail', { method: 'POST' });
      fetchTasks();
      fetchStats();
    } catch (e) { console.error(e); }
  };

  const browseDirApi = async (path: string) => {
    try {
      const res = await fetch(API_URL + '/files/browse?path=' + encodeURIComponent(path));
      const data = await res.json();
      setBrowseFiles(data.files || []);
      setBrowsePath(data.current_path || path);
    } catch (e) { console.error(e); }
  };

  const openFileBrowser = () => { setShowBrowser(true); browseDirApi('~'); };
  const navigateTo = (path: string) => { browseDirApi(path); setSelectedBrowseFile(null); };

  const selectFileForUpload = async () => {
    if (!selectedBrowseFile) return;
    setShowBrowser(false);
    setUploading(true);
    try {
      const res = await fetch(API_URL + '/files/upload-from-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedBrowseFile })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Uploaded: ' + data.filename }]);
        fetchFiles();
        if (data.category === 'images') setSelectedImage({ name: data.filename, category: data.category });
      }
    } catch (e) { setMessages(prev => [...prev, { role: 'assistant', content: 'Upload failed' }]); }
    finally { setUploading(false); setSelectedBrowseFile(null); }
  };

  const uploadPastedImage = async () => {
    if (!pastedFile) return;
    setUploading(true);
    try {
      const formData = new FormData();
      const filename = 'pasted_' + Date.now() + '.png';
      formData.append('file', pastedFile, filename);
      const res = await fetch(API_URL + '/files/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.status === 'success') {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Uploaded: ' + data.filename }]);
        fetchFiles();
        setSelectedImage({ name: data.filename, category: 'images' });
        setPastedPreview(null);
        setPastedFile(null);
      }
    } catch (e) { setMessages(prev => [...prev, { role: 'assistant', content: 'Upload failed' }]); }
    finally { setUploading(false); }
  };

  const uploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData(); formData.append('file', file);
      const res = await fetch(API_URL + '/files/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.status === 'success') {
        setMessages(prev => [...prev, { role: 'assistant', content: 'Uploaded: ' + data.filename + ' (' + data.category + ')' }]);
        fetchFiles();
        if (data.category === 'images') setSelectedImage({ name: data.filename, category: data.category });
      }
    } catch (e) { setMessages(prev => [...prev, { role: 'assistant', content: 'Upload failed' }]); }
    finally { setUploading(false); e.target.value = ''; }
  };

  const deleteFile = async (category: string, filename: string) => {
    if (!confirm('Delete ' + filename + '?')) return;
    try {
      const res = await fetch(API_URL + '/files/delete/' + category + '/' + filename, { method: 'DELETE' });
      if ((await res.json()).status === 'deleted') { fetchFiles(); if (selectedImage?.name === filename) setSelectedImage(null); }
    } catch (e) { console.error(e); }
  };

  const openFile = (category: string, filename: string) => {
    const url = API_URL + '/files/view/' + category + '/' + encodeURIComponent(filename);
    if (category === 'images') setPreviewImage(url); else window.open(url, '_blank');
  };

  const selectImageForAnalysis = (filename: string, category: string) => {
    setSelectedImage({ name: filename, category });
    setMessages(prev => [...prev, { role: 'assistant', content: 'Selected: ' + filename + ' - Ask me to analyze or measure!' }]);
  };

  const sendMessage = async () => {
    if ((!input.trim() && !pastedFile) || isLoading) return;
    if (pastedFile && !selectedImage) {
      await uploadPastedImage();
      if (!input.trim()) return;
    }
    const userMessage: Message = { role: 'user', content: input, image: selectedImage?.name };
    setMessages(prev => [...prev, userMessage]);
    const currentImage = selectedImage;
    setInput('');
    setIsLoading(true);
    try {
      const body: Record<string, unknown> = {
        message: input,
        model: selectedModel,
        history: messages.slice(-10).map(m => ({ role: m.role, content: m.content }))
      };
      if (currentImage) { body.image_filename = currentImage.name; body.image_category = currentImage.category; }
      const res = await fetch(API_URL + '/max/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response || 'Error', model: data.model_used }]);
      setSelectedImage(null);
    } catch (e) { setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error.' }]); }
    finally { setIsLoading(false); }
  };

  const cancelPasted = () => { setPastedPreview(null); setPastedFile(null); };
  const getStatusColor = (s: string) => s === 'idle' ? 'bg-green-500' : s === 'busy' ? 'bg-yellow-500' : 'bg-gray-500';
  const getTaskStatusColor = (s: string) => s === 'completed' ? 'text-green-400' : s === 'in_progress' ? 'text-yellow-400' : s === 'failed' ? 'text-red-400' : 'text-gray-400';
  const formatSize = (b: number) => b > 1048576 ? (b / 1048576).toFixed(1) + ' MB' : b > 1024 ? (b / 1024).toFixed(1) + ' KB' : b + ' B';
  const getDeskName = (id: string) => desks.find(d => d.id === id)?.name || id;

  return (
    <div className="h-screen bg-[#0a0a0f] flex overflow-hidden text-gray-200">
      {/* ═══════ PRODUCTS BUTTON ═══════ */}
      <a href="/products" className="fixed top-4 right-4 z-40 bg-gradient-to-r from-purple-600 to-pink-600 px-4 py-2 rounded-lg hover:opacity-90 transition flex items-center gap-2 shadow-lg border border-purple-400/30">
        <span>📦</span>
        <span className="font-bold text-white text-sm">Empire Box® Business Center →</span>
        <span className="text-white/70">→</span>
      </a>

      {previewImage && (
        <div className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-4" onClick={() => setPreviewImage(null)}>
          <button className="absolute top-4 right-4 text-white text-2xl hover:text-gray-300 bg-black/50 w-10 h-10 rounded-full">X</button>
          <img src={previewImage} alt="Preview" className="max-w-full max-h-full object-contain rounded-lg" />
        </div>
      )}

      {showBrowser && (
        <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4">
          <div className="bg-[#0a0a0f] border border-gray-700 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <h3 className="font-semibold text-white">Browse Files</h3>
              <button onClick={() => setShowBrowser(false)} className="text-gray-400 hover:text-white">X</button>
            </div>
            <div className="p-2 border-b border-gray-800 flex items-center gap-2">
              <button onClick={() => navigateTo(browsePath.split('/').slice(0, -1).join('/') || '/')} className="px-3 py-1 bg-gray-800 rounded hover:bg-gray-700 text-sm">↑ Up</button>
              <span className="text-sm text-gray-400 truncate flex-1">{browsePath}</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              {browseFiles.map((f, i) => (
                <div key={i} onClick={() => f.isDir ? navigateTo(f.path) : setSelectedBrowseFile(f.path)} className={'flex items-center gap-3 p-2 rounded cursor-pointer ' + (selectedBrowseFile === f.path ? 'bg-purple-900' : 'hover:bg-gray-800')}>
                  <span className="text-xl">{f.isDir ? '📁' : f.name.match(/\.(png|jpg|jpeg|gif|webp)$/i) ? '🖼️' : '📄'}</span>
                  <span className="flex-1 truncate">{f.name}</span>
                  {!f.isDir && <span className="text-xs text-gray-500">{formatSize(f.size)}</span>}
                </div>
              ))}
              {browseFiles.length === 0 && <p className="text-gray-500 text-center py-8">Empty folder</p>}
            </div>
            <div className="p-4 border-t border-gray-700 flex justify-end gap-2">
              <button onClick={() => setShowBrowser(false)} className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600">Cancel</button>
              <button onClick={selectFileForUpload} disabled={!selectedBrowseFile} className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500">Upload Selected</button>
            </div>
          </div>
        </div>
      )}

      {showTasks && (
        <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4">
          <div className="bg-[#0a0a0f] border border-gray-700 rounded-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <h3 className="font-semibold text-white">📋 Tasks</h3>
              <div className="flex gap-2">
                <button onClick={() => setShowNewTask(true)} className="px-3 py-1 bg-purple-600 hover:bg-purple-500 rounded text-sm">+ New Task</button>
                <button onClick={() => setShowTasks(false)} className="text-gray-400 hover:text-white px-2">X</button>
              </div>
            </div>
            
            {showNewTask && (
              <div className="p-4 border-b border-gray-800 bg-[#0f0f18]">
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <input type="text" placeholder="Task title..." value={newTask.title} onChange={e => setNewTask({...newTask, title: e.target.value})} className="bg-[#1a1a2f] border border-gray-700 rounded px-3 py-2 text-sm" />
                  <select value={newTask.desk_id} onChange={e => setNewTask({...newTask, desk_id: e.target.value})} className="bg-[#1a1a2f] border border-gray-700 rounded px-3 py-2 text-sm">
                    <option value="">Auto-assign desk</option>
                    {desks.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </div>
                <textarea placeholder="Description..." value={newTask.description} onChange={e => setNewTask({...newTask, description: e.target.value})} className="w-full bg-[#1a1a2f] border border-gray-700 rounded px-3 py-2 text-sm mb-3" rows={2} />
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">Priority:</span>
                    <input type="range" min="1" max="10" value={newTask.priority} onChange={e => setNewTask({...newTask, priority: parseInt(e.target.value)})} className="w-24" />
                    <span className="text-sm">{newTask.priority}</span>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => setShowNewTask(false)} className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm">Cancel</button>
                    <button onClick={createTask} className="px-3 py-1 bg-purple-600 hover:bg-purple-500 rounded text-sm">Create</button>
                  </div>
                </div>
              </div>
            )}
            
            <div className="flex-1 overflow-y-auto p-4">
              {tasks.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No tasks yet. Create one to get started!</p>
              ) : (
                <div className="space-y-2">
                  {tasks.map(task => (
                    <div key={task.id} className="bg-[#1a1a2f] border border-gray-800 rounded-lg p-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className={'text-xs font-medium ' + getTaskStatusColor(task.status)}>{task.status.replace('_', ' ').toUpperCase()}</span>
                            <span className="text-xs text-gray-600">P{task.priority}</span>
                          </div>
                          <h4 className="font-medium text-white mt-1">{task.title}</h4>
                          <p className="text-sm text-gray-400 mt-1">{task.description}</p>
                          <p className="text-xs text-gray-600 mt-2">Assigned to: {getDeskName(task.desk_id)}</p>
                        </div>
                        {task.status === 'in_progress' && (
                          <div className="flex gap-1 ml-3">
                            <button onClick={() => completeTask(task.id)} className="px-2 py-1 bg-green-600 hover:bg-green-500 rounded text-xs">✓ Done</button>
                            <button onClick={() => failTask(task.id)} className="px-2 py-1 bg-red-600 hover:bg-red-500 rounded text-xs">✗ Fail</button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="p-3 border-t border-gray-800 text-xs text-gray-500 flex justify-between">
              <span>Total: {tasks.length}</span>
              <span>Active: {tasks.filter(t => t.status === 'in_progress').length} | Done: {tasks.filter(t => t.status === 'completed').length} | Failed: {tasks.filter(t => t.status === 'failed').length}</span>
            </div>
          </div>
        </div>
      )}

      <div className="w-64 bg-[#050508] border-r border-gray-800 flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-xl font-bold text-purple-400">Empire Console</h1>
          <p className="text-xs text-gray-500">Founder Command Center</p>
          
          {/* AI Model Selector */}
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xs text-gray-500">🤖</span>
            <select 
              value={selectedModel} 
              onChange={(e) => setSelectedModel(e.target.value)} 
              className="flex-1 bg-[#1a1a2f] border border-purple-500/30 rounded-lg px-2 py-1.5 text-xs text-purple-300 hover:border-purple-400 focus:border-purple-500 focus:outline-none transition cursor-pointer"
            >
              {models.map(m => (
                <option key={m.id} value={m.id} disabled={!m.available}>{m.name}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="p-3 border-b border-gray-800">
          <button onClick={() => { setShowTasks(true); fetchTasks(); }} className="w-full grid grid-cols-2 gap-2 hover:opacity-80 transition-opacity">
            <div className="bg-[#0a0a0f] rounded p-2 text-center border border-gray-800 hover:border-purple-600">
              <span className="text-xs text-gray-500">Done</span>
              <p className="text-lg font-bold text-green-400">{stats.total_completed}</p>
            </div>
            <div className="bg-[#0a0a0f] rounded p-2 text-center border border-gray-800 hover:border-purple-600">
              <span className="text-xs text-gray-500">Active</span>
              <p className="text-lg font-bold text-yellow-400">{stats.active_tasks}</p>
            </div>
          </button>
          <p className="text-xs text-gray-600 text-center mt-1">Click to manage tasks</p>
        </div>
        <div className="p-3 border-b border-gray-800">
          <button onClick={() => setShowFiles(!showFiles)} className="w-full text-left text-xs font-semibold text-gray-500 uppercase flex justify-between items-center hover:text-gray-300">
            <span>Files ({files.length})</span><span>{showFiles ? '▼' : '▶'}</span>
          </button>
          {showFiles && (
            <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
              {files.map((f, i) => (
                <div key={i} className={'text-xs p-1 rounded flex items-center gap-1 group ' + (selectedImage?.name === f.name ? 'bg-purple-900' : 'hover:bg-gray-800')}>
                  <span className="cursor-pointer flex-1 truncate hover:text-white" onClick={() => openFile(f.category, f.name)}>{f.name}</span>
                  {f.category === 'images' && <button onClick={() => selectImageForAnalysis(f.name, f.category)} className="text-purple-400 hover:text-purple-200 px-1" title="Analyze">📐</button>}
                  <button onClick={() => deleteFile(f.category, f.name)} className="opacity-0 group-hover:opacity-100 text-red-400 px-1">x</button>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="p-3 border-b border-gray-800">
          <button onClick={() => setShowReminders(!showReminders)} className="w-full text-left text-xs font-semibold text-gray-500 uppercase flex justify-between items-center hover:text-gray-300">
            <span>📋 Reminders ({reminders.filter(r => !r.completed).length})</span><span>{showReminders ? '▼' : '▶'}</span>
          </button>
          {showReminders && (
            <div className="mt-2 space-y-2">
              <div className="flex gap-1">
                <input type="text" value={newReminder.text} onChange={(e) => setNewReminder({...newReminder, text: e.target.value})} placeholder="New reminder..." className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs" onKeyDown={(e) => e.key === 'Enter' && addReminder()} />
                <button onClick={addReminder} className="px-2 bg-purple-600 hover:bg-purple-500 rounded text-xs">+</button>
              </div>
              <div className="flex gap-1">
                <input type="date" value={newReminder.dueDate} onChange={(e) => setNewReminder({...newReminder, dueDate: e.target.value})} className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs" />
                <select value={newReminder.priority} onChange={(e) => setNewReminder({...newReminder, priority: e.target.value as "low" | "medium" | "high"})} className="bg-gray-800 border border-gray-700 rounded px-1 text-xs">
                  <option value="low">Low</option><option value="medium">Med</option><option value="high">High</option>
                </select>
              </div>
              <div className="max-h-32 overflow-y-auto space-y-1">
                {/* Internal Empire Notifications - Click to open modal */}
              {aiNotifications.filter(n => !n.read).length > 0 && (
                <div className="mb-3 border-b border-gray-700 pb-2">
                  <p className="text-xs text-purple-400 font-semibold mb-1">🔔 Empire Alerts ({aiNotifications.filter(n => !n.read).length})</p>
                  {aiNotifications.filter(n => !n.read).map(n => (
                    <div 
                      key={n.id} 
                      onClick={() => setSelectedNotif(n)}
                      className={"text-xs p-2 rounded mb-1 cursor-pointer hover:bg-white/10 flex items-center gap-2 border " + (n.priority === "high" ? "bg-red-900/20 border-red-700/50" : "bg-purple-900/20 border-purple-700/50")}
                    >
                      <span className={n.source === "MAX" ? "text-cyan-400" : n.source === "System" ? "text-yellow-400" : "text-purple-300"}>
                        {n.source === "MAX" ? "🧠" : n.source === "System" ? "⚙️" : n.source === "Business" ? "💰" : "🖥️"}
                      </span>
                      <span className="text-white truncate flex-1">{n.title}</span>
                      {n.priority === "high" && <span className="text-red-400 animate-pulse">●</span>}
                    </div>
                  ))}
                </div>
              )}
              {/* Manual Reminders */}
              {reminders.sort((a,b) => a.completed === b.completed ? 0 : a.completed ? 1 : -1).map(r => (
                  <div key={r.id} className={'text-xs p-2 rounded flex items-center gap-2 group ' + (r.completed ? 'bg-gray-800/50 opacity-50' : 'bg-gray-800')}>
                    <input type="checkbox" checked={r.completed} onChange={() => toggleReminder(r.id)} className="rounded" />
                    <div className="flex-1 min-w-0"><p className={r.completed ? 'line-through text-gray-500' : ''}>{r.text}</p>{r.dueDate && <p className="text-gray-500 text-[10px]">Due: {r.dueDate}</p>}</div>
                    <span className={getPriorityColor(r.priority)}>●</span>
                    <button onClick={() => deleteReminder(r.id)} className="opacity-0 group-hover:opacity-100 text-red-400">×</button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">AI Desks</h3>
          {desks.map(desk => (
            <div key={desk.id} className="flex items-center gap-2 p-2 rounded hover:bg-[#0a0a0f] cursor-pointer">
              <div className="relative">
                <div className="w-8 h-8 rounded bg-gray-800 flex items-center justify-center text-sm">{desk.name.charAt(0)}</div>
                <div className={'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-[#050508] ' + getStatusColor(desk.status)} />
              </div>
              <div className="flex-1 min-w-0"><p className="text-sm truncate">{desk.name}</p><p className="text-xs text-gray-500 truncate">{desk.description}</p></div>
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-gray-800 text-xs text-gray-600 text-center">Ctrl+V paste | Shift+Enter newline</div>
      </div>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-12 bg-[#050508] border-b border-gray-800 flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold">M</div>
            <div><span className="font-semibold">MAX</span><span className="text-xs text-gray-500 ml-2">AI Assistant</span></div>
          </div>
          {/* Model selector is in sidebar */}
          <span className="text-xs text-purple-400 bg-purple-900/30 px-2 py-1 rounded border border-purple-500/20">{models.find(m => m.id === selectedModel)?.name || selectedModel}</span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
          {messages.map((msg, i) => (
            <div key={i} className={'flex ' + (msg.role === 'user' ? 'justify-end' : 'justify-start')}>
              <div className={'max-w-[75%] rounded-xl px-4 py-2 ' + (msg.role === 'user' ? 'bg-purple-600' : 'bg-[#1a1a2f] border border-gray-800')}>
                {msg.image && <p className="text-xs mb-1 opacity-60">📎 {msg.image}</p>}
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                {msg.model && <p className="text-xs mt-1 opacity-40">via {msg.model}</p>}
              </div>
            </div>
          ))}
          {isLoading && <div className="flex justify-start"><div className="bg-[#1a1a2f] border border-gray-800 rounded-xl px-4 py-2 text-gray-400 text-sm">{selectedImage ? '📐 Analyzing...' : '💭 Thinking...'}</div></div>}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-[#050508] border-t border-gray-800 shrink-0">
          {pastedPreview && (
            <div className="mb-3 p-3 bg-purple-900/30 border border-purple-700 rounded-lg flex items-center gap-3">
              <img src={pastedPreview} alt="Pasted" className="w-20 h-20 object-cover rounded" />
              <div className="flex-1">
                <p className="text-sm text-purple-300">Image from clipboard</p>
                <p className="text-xs text-gray-500">Uploads when you send</p>
              </div>
              <button onClick={uploadPastedImage} className="px-3 py-1 bg-purple-600 hover:bg-purple-500 rounded text-sm">Upload Now</button>
              <button onClick={cancelPasted} className="text-gray-400 hover:text-white px-2">X</button>
            </div>
          )}
          {selectedImage && !pastedPreview && (
            <div className="mb-3 px-3 py-2 bg-purple-900/30 border border-purple-700 rounded-lg flex items-center justify-between text-sm">
              <span className="text-purple-300">📐 {selectedImage.name}</span>
              <button onClick={() => setSelectedImage(null)} className="text-purple-400 hover:text-white">x</button>
            </div>
          )}
          <div className="flex gap-3">
            <div className="flex flex-col gap-2">
              <button onClick={openFileBrowser} className="w-12 h-12 rounded-lg bg-gray-800 hover:bg-gray-700 flex items-center justify-center text-xl" title="Browse Files">📂</button>
              <label className="w-12 h-12 rounded-lg bg-gray-800 hover:bg-gray-700 flex items-center justify-center text-xl cursor-pointer" title="Upload File">
                <input type="file" onChange={uploadFile} className="hidden" />{uploading ? '⏳' : '📎'}
              </label>
            </div>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder={pastedPreview ? "Ask about the pasted image..." : selectedImage ? "Ask about this image (measure, describe, read)..." : "Message MAX... (Ctrl+V paste, Shift+Enter newline)"}
              className="flex-1 bg-[#0a0a0f] border border-gray-700 rounded-xl px-4 py-3 text-sm focus:border-purple-500 focus:outline-none resize-none"
              style={{minHeight: '200px', maxHeight: '400px'}}
            />
            <button onClick={sendMessage} disabled={isLoading || (!input.trim() && !pastedFile)} className="w-12 h-12 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 flex items-center justify-center text-xl self-end">→</button>
          </div>
        </div>
      </div>
    
      {/* Notification Modal */}
    {selectedNotif && (
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setSelectedNotif(null)}>
        <div className="bg-[#12121a] border border-gray-700 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
          <div className={"px-6 py-4 border-b border-gray-700 " + (selectedNotif.priority === "high" ? "bg-red-900/30" : "bg-purple-900/30")}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{selectedNotif.source === "MAX" ? "🧠" : selectedNotif.source === "System" ? "⚙️" : selectedNotif.source === "Business" ? "💰" : "🖥️"}</span>
                <div>
                  <h2 className="text-lg font-semibold text-white">{selectedNotif.title}</h2>
                  <p className="text-sm text-gray-400">{selectedNotif.source} • {selectedNotif.type.replace('_', ' ')}</p>
                </div>
              </div>
              <button onClick={() => setSelectedNotif(null)} className="text-gray-400 hover:text-white text-2xl">×</button>
            </div>
          </div>
          <div className="px-6 py-5 overflow-y-auto max-h-[50vh]">
            <p className="text-gray-200 text-base leading-relaxed mb-6">{selectedNotif.message}</p>
            {selectedNotif.context?.options && (
              <div className="mb-6">
                <p className="text-sm text-gray-400 mb-3">Quick Actions:</p>
                <div className="flex gap-3 flex-wrap">
                  {selectedNotif.context.options.map((opt: string) => (
                    <button key={opt} onClick={() => { respondToNotification(selectedNotif.id, opt); setSelectedNotif(null); }} className={"px-5 py-2.5 rounded-lg font-medium " + (opt.toLowerCase().includes('approve') || opt.toLowerCase().includes('merge') ? "bg-green-600 hover:bg-green-500" : opt.toLowerCase().includes('reject') ? "bg-red-600 hover:bg-red-500" : "bg-gray-700 hover:bg-gray-600")}>{opt}</button>
                  ))}
                </div>
              </div>
            )}
            <div>
              <p className="text-sm text-gray-400 mb-2">Or send a custom reply:</p>
              <textarea value={notifReply} onChange={(e) => setNotifReply(e.target.value)} placeholder="Type your response..." className="w-full bg-gray-800 border border-gray-600 rounded-lg px-4 py-3 text-sm focus:border-purple-500 focus:outline-none resize-none" rows={3} />
              <div className="flex justify-between items-center mt-3">
                <button onClick={() => { markNotificationRead(selectedNotif.id); setSelectedNotif(null); }} className="text-gray-500 hover:text-gray-300 text-sm">Mark as read</button>
                <button onClick={() => { if(notifReply.trim()) { respondToNotification(selectedNotif.id, notifReply); setNotifReply(''); setSelectedNotif(null); }}} disabled={!notifReply.trim()} className="px-5 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium">Send Reply</button>
              </div>
            </div>
          </div>
          <div className="px-6 py-3 border-t border-gray-700 bg-gray-900/50 flex justify-between text-xs text-gray-500">
            <span>Received: {new Date(selectedNotif.created_at).toLocaleString()}</span>
            <button onClick={() => { dismissNotification(selectedNotif.id); setSelectedNotif(null); }} className="text-red-400 hover:text-red-300">Dismiss</button>
          </div>
        </div>
      </div>
    )}
    </div>
  );
}
