'use client'
import { useState, useEffect } from 'react'
import { CheckSquare, Plus, Mic, Clock, Check, X, Trash2, Flag } from 'lucide-react'
import AudioRecorder from '@/components/audio/AudioRecorder'

interface Task {
  id: string
  title: string
  status: 'todo' | 'doing' | 'done'
  priority: 'low' | 'normal' | 'high'
  category: string
  fromAudio?: boolean
  createdAt: string
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [showAudio, setShowAudio] = useState(false)
  const [newTask, setNewTask] = useState('')

  useEffect(() => {
    const saved = localStorage.getItem('empire_tasks')
    if (saved) setTasks(JSON.parse(saved))
  }, [])

  useEffect(() => {
    localStorage.setItem('empire_tasks', JSON.stringify(tasks))
  }, [tasks])

  const addTask = (title: string, fromAudio = false) => {
    if (!title.trim()) return
    setTasks([{ id: Date.now().toString(), title, status: 'todo', priority: 'normal', category: 'General', fromAudio, createdAt: new Date().toISOString() }, ...tasks])
    setNewTask('')
    setShowAdd(false)
  }

  const updateStatus = (id: string, status: Task['status']) => {
    setTasks(tasks.map(t => t.id === id ? { ...t, status } : t))
  }

  const deleteTask = (id: string) => {
    setTasks(tasks.filter(t => t.id !== id))
  }

  const columns = [
    { id: 'todo', label: 'Por Hacer', color: 'border-gray-500' },
    { id: 'doing', label: 'En Progreso', color: 'border-blue-500' },
    { id: 'done', label: 'Completado', color: 'border-green-500' },
  ]

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Tareas</h1>
            <p className="text-gray-500">{tasks.filter(t => t.status !== 'done').length} pendientes</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setShowAudio(true)} className="flex items-center gap-2 bg-gradient-to-r from-amber-500 to-orange-600 px-4 py-2 rounded-xl font-semibold">
            <Mic className="w-5 h-5" />Audio
          </button>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 bg-gradient-to-r from-violet-500 to-purple-600 px-4 py-2 rounded-xl font-semibold">
            <Plus className="w-5 h-5" />Nueva
          </button>
        </div>
      </div>

      {/* Kanban */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {columns.map(col => (
          <div key={col.id} className={`bg-[#0a0a12] rounded-xl border-t-4 ${col.color} p-4 min-h-[300px]`}>
            <h3 className="font-semibold mb-4 flex justify-between">
              {col.label}
              <span className="bg-white/10 px-2 py-0.5 rounded text-sm">{tasks.filter(t => t.status === col.id).length}</span>
            </h3>
            <div className="space-y-3">
              {tasks.filter(t => t.status === col.id).map(task => (
                <div key={task.id} className="bg-white/5 rounded-xl p-4 border border-white/10 group">
                  <div className="flex justify-between mb-2">
                    {task.fromAudio && <Mic className="w-3 h-3 text-amber-400" />}
                    <button onClick={() => deleteTask(task.id)} className="opacity-0 group-hover:opacity-100 text-red-400"><Trash2 className="w-4 h-4" /></button>
                  </div>
                  <p className="mb-3">{task.title}</p>
                  <div className="flex gap-1">
                    {columns.map(c => (
                      <button key={c.id} onClick={() => updateStatus(task.id, c.id as Task['status'])} className={`flex-1 py-1 rounded text-xs ${task.status === c.id ? 'bg-violet-500' : 'bg-white/10'}`}>
                        {c.id === 'done' ? <Check className="w-3 h-3 mx-auto" /> : c.label.slice(0,3)}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Add Modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowAdd(false)} />
          <div className="relative bg-[#0a0a12] border border-white/10 rounded-2xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-4">Nueva Tarea</h2>
            <input type="text" value={newTask} onChange={(e) => setNewTask(e.target.value)} placeholder="Descripción de la tarea..." className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 mb-4 outline-none" autoFocus />
            <div className="flex gap-3">
              <button onClick={() => setShowAdd(false)} className="flex-1 bg-white/10 py-3 rounded-xl">Cancelar</button>
              <button onClick={() => addTask(newTask)} className="flex-1 bg-violet-500 py-3 rounded-xl font-semibold">Crear</button>
            </div>
          </div>
        </div>
      )}

      {/* Audio Modal */}
      {showAudio && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowAudio(false)} />
          <div className="relative w-full max-w-lg">
            <AudioRecorder onTranscription={(text) => { addTask(text, true); setShowAudio(false) }} onClose={() => setShowAudio(false)} />
          </div>
        </div>
      )}
    </div>
  )
}
