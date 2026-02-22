'use client';

import { useState, useEffect, useRef } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  model?: string;
}

interface Desk {
  id: string;
  name: string;
  description: string;
  status: string;
  stats: { completed: number; failed: number };
}

interface AIModel {
  id: string;
  name: string;
  available: boolean;
  type: string;
}

export default function FounderDashboard() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: "Hello! I'm MAX, your AI Assistant Manager. All 8 desks are online. How can I help?" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [desks, setDesks] = useState<Desk[]>([]);
  const [models, setModels] = useState<AIModel[]>([]);
  const [selectedModel, setSelectedModel] = useState('ollama-llama');
  const [stats, setStats] = useState({ total_completed: 0, active_tasks: 0 });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDesks();
    fetchModels();
    fetchStats();
    const interval = setInterval(() => { fetchDesks(); fetchStats(); }, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchDesks = async () => {
    try {
      const res = await fetch(API_URL + '/max/desks');
      const data = await res.json();
      setDesks(data.desks || []);
    } catch (e) { console.error('Failed to fetch desks:', e); }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch(API_URL + '/max/models');
      const data = await res.json();
      setModels(data.models || []);
    } catch (e) { console.error('Failed to fetch models:', e); }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(API_URL + '/max/stats');
      const data = await res.json();
      setStats(data.stats || {});
    } catch (e) { console.error('Failed to fetch stats:', e); }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    const userMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    try {
      const res = await fetch(API_URL + '/max/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          model: selectedModel,
          history: messages.map(m => ({ role: m.role, content: m.content }))
        })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response || 'Error processing request.', model: data.model_used }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Connection error. Check if backend is running.' }]);
    } finally { setIsLoading(false); }
  };

  const getStatusColor = (status: string) => {
    if (status === 'idle') return 'bg-green-500';
    if (status === 'busy') return 'bg-yellow-500';
    return 'bg-gray-500';
  };

  return (
    <div className="min-h-screen bg-[#050508] flex">
      {/* Sidebar */}
      <div className="w-72 bg-[#0a0a0f] border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-xl font-bold text-purple-400">EmpireBox</h1>
          <p className="text-xs text-gray-500">Founder Edition</p>
        </div>
        <div className="p-3 grid grid-cols-2 gap-2">
          <div className="bg-[#050508] rounded-lg p-3 border border-gray-800">
            <span className="text-xs text-gray-400">Completed</span>
            <p className="text-xl font-bold text-white">{stats.total_completed}</p>
          </div>
          <div className="bg-[#050508] rounded-lg p-3 border border-gray-800">
            <span className="text-xs text-gray-400">Active</span>
            <p className="text-xl font-bold text-white">{stats.active_tasks}</p>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2 px-2">AI Desks</h3>
          {desks.map(desk => (
            <div key={desk.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-[#050508] cursor-pointer">
              <div className="relative">
                <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center text-gray-400 text-sm">
                  {desk.name.charAt(0)}
                </div>
                <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#0a0a0f] ${getStatusColor(desk.status)}`} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-200">{desk.name}</p>
                <p className="text-xs text-gray-500">{desk.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col">
        <div className="h-14 bg-[#0a0a0f] border-b border-gray-800 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold">M</div>
            <div>
              <h2 className="font-semibold text-white">MAX</h2>
              <p className="text-xs text-gray-400">AI Assistant Manager</p>
            </div>
          </div>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="bg-[#050508] border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
          >
            {models.map(m => (
              <option key={m.id} value={m.id} disabled={!m.available}>
                {m.name} {!m.available && '(No Key)'}
              </option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.role === 'user' ? 'bg-purple-600 text-white' : 'bg-[#0a0a0f] border border-gray-800 text-gray-200'}`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.model && <p className="text-xs mt-2 opacity-50">via {msg.model}</p>}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-[#0a0a0f] border border-gray-800 rounded-2xl px-4 py-3 text-gray-400">
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-[#0a0a0f] border-t border-gray-800">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Message MAX..."
              className="flex-1 bg-[#050508] border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none"
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="w-12 h-12 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 flex items-center justify-center text-white font-bold"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
