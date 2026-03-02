'use client'
import { Lightbulb, Plus, Sparkles } from 'lucide-react'

export default function Creations() {
  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-4 mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-yellow-500 to-pink-600 flex items-center justify-center">
            <Lightbulb className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Creations Lab</h1>
            <p className="text-gray-500">Innovation & Research</p>
          </div>
        </div>
        <div className="bg-[#1A1A1A] rounded-xl p-6 border border-gray-800 text-center">
          <Sparkles className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Innovation Hub</h2>
          <p className="text-gray-400 mb-4">Research new opportunities and track R&D projects</p>
          <button className="bg-gradient-to-r from-yellow-500 to-pink-600 px-6 py-3 rounded-xl font-semibold flex items-center gap-2 mx-auto">
            <Plus className="w-5 h-5" /> New Idea
          </button>
        </div>
      </div>
    </div>
  )
}
