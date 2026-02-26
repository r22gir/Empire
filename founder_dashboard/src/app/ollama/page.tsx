'use client';
import { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface OllamaModel {
  name: string;
  size_gb: number;
  modified_at: string;
  digest: string;
}

export default function OllamaManagerPage() {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [pullName, setPullName] = useState('');
  const [pulling, setPulling] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchModels = async () => {
    try {
      const res = await fetch(API_URL + '/ollama/models');
      const data = await res.json();
      setModels(data.models || []);
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to connect to Ollama' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchModels(); }, []);

  const pullModel = async () => {
    if (!pullName.trim()) return;
    setPulling(true);
    setMessage(null);
    try {
      const res = await fetch(API_URL + '/ollama/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: pullName.trim() }),
      });
      if (res.ok) {
        setMessage({ type: 'success', text: `Pulled ${pullName} successfully` });
        setPullName('');
        fetchModels();
      } else {
        const data = await res.json();
        setMessage({ type: 'error', text: data.detail || 'Pull failed' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Pull request failed' });
    } finally {
      setPulling(false);
    }
  };

  const deleteModel = async (name: string) => {
    if (!confirm(`Delete model "${name}"?`)) return;
    setDeleting(name);
    try {
      const res = await fetch(`${API_URL}/ollama/models/${encodeURIComponent(name)}`, { method: 'DELETE' });
      if (res.ok) {
        setMessage({ type: 'success', text: `Deleted ${name}` });
        fetchModels();
      } else {
        const data = await res.json();
        setMessage({ type: 'error', text: data.detail || 'Delete failed' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Delete request failed' });
    } finally {
      setDeleting(null);
    }
  };

  const totalSize = models.reduce((sum, m) => sum + m.size_gb, 0);

  return (
    <div className="min-h-screen bg-[#030308] text-white p-8">
      <div className="max-w-4xl mx-auto">
        <a href="/" className="text-gray-400 hover:text-white mb-2 block text-sm">&larr; Back to Console</a>
        <h1 className="text-3xl font-bold mb-2">Ollama Model Manager</h1>
        <p className="text-gray-500 mb-6">{models.length} models installed &mdash; {totalSize.toFixed(1)} GB total</p>

        {message && (
          <div className={`mb-4 p-3 rounded-lg text-sm ${message.type === 'success' ? 'bg-green-900/30 text-green-400 border border-green-700' : 'bg-red-900/30 text-red-400 border border-red-700'}`}>
            {message.text}
          </div>
        )}

        {/* Pull new model */}
        <div className="mb-6 flex gap-3">
          <input
            type="text"
            value={pullName}
            onChange={(e) => setPullName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && pullModel()}
            placeholder="Model name (e.g. llama3.2, mistral, codellama:7b)"
            className="flex-1 bg-[#0a0a0f] border border-gray-700 rounded-lg px-4 py-3 text-sm focus:border-amber-500 focus:outline-none"
          />
          <button
            onClick={pullModel}
            disabled={pulling || !pullName.trim()}
            className="px-6 py-3 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 disabled:text-gray-500 font-medium transition"
          >
            {pulling ? 'Pulling...' : 'Pull Model'}
          </button>
        </div>

        {/* Model list */}
        {loading ? (
          <div className="text-center py-20 text-gray-500">Loading models...</div>
        ) : (
          <div className="space-y-3">
            {models.map((m) => (
              <div key={m.name} className="flex items-center justify-between p-4 rounded-xl border border-gray-800 bg-[#0a0a0f] hover:border-gray-700 transition">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg">{m.name}</h3>
                  <div className="flex gap-4 mt-1 text-xs text-gray-500">
                    <span>{m.size_gb} GB</span>
                    <span>{m.digest}</span>
                    <span>{new Date(m.modified_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <button
                  onClick={() => deleteModel(m.name)}
                  disabled={deleting === m.name}
                  className="px-4 py-2 rounded-lg text-sm bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600/40 transition disabled:opacity-50"
                >
                  {deleting === m.name ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            ))}
            {models.length === 0 && (
              <div className="text-center py-12 text-gray-500">No models installed. Pull one above!</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
