'use client'
import { useState } from 'react'
import { Lightbulb, Plus, Sparkles, Rocket, Star, X } from 'lucide-react'

interface Idea { id: string; title: string; description: string; status: 'idea' | 'research' | 'prototype' | 'launched'; priority: string }

export default function Creations() {
  const [ideas, setIdeas] = useState<Idea[]>([])
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', status: 'idea' as const, priority: 'medium' })

  const save = () => {
    if (!form.title) return
    setIdeas([...ideas, { ...form, id: Date.now().toString() }])
    setShowModal(false)
    setForm({ title: '', description: '', status: 'idea', priority: 'medium' })
  }

  const statusColors = { idea: 'bg-purple-500/20 text-purple-400', research: 'bg-blue-500/20 text-blue-400', prototype: 'bg-yellow-500/20 text-yellow-400', launched: 'bg-green-500/20 text-green-400' }

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center">
            <Lightbulb className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Creations Lab</h1>
            <p className="text-gray-500">Innovation & R&D</p>
          </div>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 bg-gradient-to-r from-pink-500 to-purple-600 px-4 py-2 rounded-xl font-semibold">
          <Plus className="w-5 h-5" />New Idea
        </button>
      </div>

      {ideas.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-pink-500/20 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-10 h-10 text-pink-400" />
          </div>
          <h2 className="text-xl font-bold mb-2">No ideas yet</h2>
          <p className="text-gray-500 mb-6">Capture your innovations and product ideas</p>
          <button onClick={() => setShowModal(true)} className="bg-gradient-to-r from-pink-500 to-purple-600 px-6 py-3 rounded-xl font-semibold">Add First Idea</button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {ideas.map(idea => (
            <div key={idea.id} className="bg-[#0a0a12] rounded-xl border border-white/10 p-5">
              <div className="flex justify-between mb-3">
                <span className={`text-xs px-2 py-1 rounded ${statusColors[idea.status]}`}>{idea.status}</span>
                <Lightbulb className="w-5 h-5 text-pink-400" />
              </div>
              <h3 className="font-semibold text-lg mb-2">{idea.title}</h3>
              <p className="text-gray-500 text-sm">{idea.description}</p>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowModal(false)} />
          <div className="relative bg-[#0a0a12] border border-white/10 rounded-2xl w-full max-w-md p-6">
            <div className="flex justify-between mb-4"><h2 className="text-xl font-bold">New Idea</h2><button onClick={() => setShowModal(false)}><X className="w-5 h-5" /></button></div>
            <div className="space-y-4">
              <input type="text" placeholder="Idea title *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <textarea placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={4} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none resize-none" />
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as any })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none">
                <option value="idea">Idea</option>
                <option value="research">Research</option>
                <option value="prototype">Prototype</option>
                <option value="launched">Launched</option>
              </select>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="flex-1 bg-white/10 py-3 rounded-xl">Cancel</button>
              <button onClick={save} className="flex-1 bg-gradient-to-r from-pink-500 to-purple-600 py-3 rounded-xl font-semibold">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
