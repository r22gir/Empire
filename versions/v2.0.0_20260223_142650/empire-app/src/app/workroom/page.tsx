'use client'
import { useState } from 'react'
import { Factory, Plus, Trash2, Copy, ChevronDown, ChevronUp, Send, Save, User, Camera, Sparkles } from 'lucide-react'

interface Window { id: string; name: string; width: number; height: number; treatment: string; lining: string; hardware: string; motor: string }
interface Room { id: string; name: string; windows: Window[]; expanded: boolean }
interface Quote { id: string; customer: string; rooms: Room[]; status: string; total: number; date: Date }

const PRICING = {
  treatment: { ripplefold: 45, 'pinch-pleat': 38, 'roman-shade': 55, 'roller-shade': 42 },
  lining: { unlined: 0, standard: 8, blackout: 15, thermal: 12 },
  hardware: { none: 0, 'rod-standard': 45, 'track-basic': 65, 'track-ripplefold': 95 },
  motor: { none: 0, somfy: 285, lutron: 425 }
}

export default function Workroom() {
  const [quotes, setQuotes] = useState<Quote[]>([])
  const [currentQuote, setCurrentQuote] = useState<Quote | null>(null)
  const [customer, setCustomer] = useState('')

  const genId = () => Math.random().toString(36).substr(2, 9)

  const newQuote = () => {
    const q: Quote = { id: genId(), customer: '', rooms: [], status: 'draft', total: 0, date: new Date() }
    setCurrentQuote(q)
    setCustomer('')
  }

  const addRoom = () => {
    if (!currentQuote) return
    setCurrentQuote({
      ...currentQuote,
      rooms: [...currentQuote.rooms, { id: genId(), name: `Room ${currentQuote.rooms.length + 1}`, windows: [], expanded: true }]
    })
  }

  const addWindow = (roomId: string) => {
    if (!currentQuote) return
    setCurrentQuote({
      ...currentQuote,
      rooms: currentQuote.rooms.map(r => r.id === roomId ? {
        ...r,
        windows: [...r.windows, { id: genId(), name: `Window ${r.windows.length + 1}`, width: 48, height: 60, treatment: 'ripplefold', lining: 'standard', hardware: 'track-ripplefold', motor: 'none' }]
      } : r)
    })
  }

  const updateWindow = (roomId: string, windowId: string, updates: Partial<Window>) => {
    if (!currentQuote) return
    setCurrentQuote({
      ...currentQuote,
      rooms: currentQuote.rooms.map(r => r.id === roomId ? {
        ...r,
        windows: r.windows.map(w => w.id === windowId ? { ...w, ...updates } : w)
      } : r)
    })
  }

  const deleteWindow = (roomId: string, windowId: string) => {
    if (!currentQuote) return
    setCurrentQuote({
      ...currentQuote,
      rooms: currentQuote.rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.filter(w => w.id !== windowId) } : r)
    })
  }

  const deleteRoom = (roomId: string) => {
    if (!currentQuote) return
    setCurrentQuote({ ...currentQuote, rooms: currentQuote.rooms.filter(r => r.id !== roomId) })
  }

  const toggleRoom = (roomId: string) => {
    if (!currentQuote) return
    setCurrentQuote({
      ...currentQuote,
      rooms: currentQuote.rooms.map(r => r.id === roomId ? { ...r, expanded: !r.expanded } : r)
    })
  }

  const calcWindowPrice = (w: Window): number => {
    const sqft = (w.width * w.height) / 144
    const t = PRICING.treatment[w.treatment as keyof typeof PRICING.treatment] || 40
    const l = PRICING.lining[w.lining as keyof typeof PRICING.lining] || 0
    const h = PRICING.hardware[w.hardware as keyof typeof PRICING.hardware] || 0
    const m = PRICING.motor[w.motor as keyof typeof PRICING.motor] || 0
    return (t + l) * sqft + h + m
  }

  const calcTotal = (): number => {
    if (!currentQuote) return 0
    return currentQuote.rooms.reduce((sum, r) => sum + r.windows.reduce((s, w) => s + calcWindowPrice(w), 0), 0)
  }

  const saveQuote = () => {
    if (!currentQuote) return
    const updated = { ...currentQuote, customer, total: calcTotal() }
    setQuotes([...quotes.filter(q => q.id !== updated.id), updated])
    setCurrentQuote(null)
  }

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-600 flex items-center justify-center">
            <Factory className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Workroom</h1>
            <p className="text-gray-500">Quotes & Production</p>
          </div>
        </div>
        {!currentQuote && (
          <button onClick={newQuote} className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-cyan-600 px-4 py-2 rounded-xl font-semibold">
            <Plus className="w-5 h-5" />New Quote
          </button>
        )}
        {currentQuote && (
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-green-400">${calcTotal().toLocaleString()}</span>
            <button onClick={saveQuote} className="flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-2 rounded-xl font-semibold">
              <Save className="w-5 h-5" />Save
            </button>
          </div>
        )}
      </div>

      {/* No Quote State */}
      {!currentQuote && quotes.length === 0 && (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-blue-500/20 flex items-center justify-center mx-auto mb-4">
            <Factory className="w-10 h-10 text-blue-400" />
          </div>
          <h2 className="text-xl font-bold mb-2">No quotes yet</h2>
          <p className="text-gray-500 mb-6">Create your first quote</p>
          <button onClick={newQuote} className="bg-gradient-to-r from-blue-500 to-cyan-600 px-6 py-3 rounded-xl font-semibold">Create First Quote</button>
        </div>
      )}

      {/* Quote List */}
      {!currentQuote && quotes.length > 0 && (
        <div className="space-y-4">
          {quotes.map(q => (
            <div key={q.id} onClick={() => setCurrentQuote(q)} className="bg-[#0a0a12] rounded-xl border border-white/10 p-5 cursor-pointer hover:border-white/20">
              <div className="flex justify-between">
                <div>
                  <h3 className="font-semibold">{q.customer || 'Unnamed Customer'}</h3>
                  <p className="text-sm text-gray-500">{q.rooms.length} rooms • {q.rooms.reduce((s, r) => s + r.windows.length, 0)} windows</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-green-400">${q.total.toLocaleString()}</p>
                  <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">{q.status}</span>
                </div>
              </div>
            </div>
          ))}
          <button onClick={newQuote} className="w-full py-4 border-2 border-dashed border-gray-700 hover:border-blue-500 rounded-xl text-gray-500 hover:text-blue-400 flex items-center justify-center gap-2">
            <Plus className="w-5 h-5" />New Quote
          </button>
        </div>
      )}

      {/* Quote Builder */}
      {currentQuote && (
        <div className="space-y-6">
          {/* Customer */}
          <div className="bg-[#0a0a12] rounded-xl border border-white/10 p-5">
            <label className="block text-sm text-gray-400 mb-2">Customer Name</label>
            <input type="text" value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="Enter customer name..." className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-blue-500" />
          </div>

          {/* Rooms */}
          {currentQuote.rooms.map(room => (
            <div key={room.id} className="bg-[#0a0a12] rounded-xl border border-white/10 overflow-hidden">
              <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button onClick={() => toggleRoom(room.id)} className="p-1 hover:bg-white/10 rounded">
                    {room.expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                  <input type="text" value={room.name} onChange={(e) => setCurrentQuote({ ...currentQuote, rooms: currentQuote.rooms.map(r => r.id === room.id ? { ...r, name: e.target.value } : r) })} className="bg-transparent font-semibold text-lg outline-none" />
                  <span className="text-sm text-gray-500">({room.windows.length} windows)</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-green-400">${room.windows.reduce((s, w) => s + calcWindowPrice(w), 0).toLocaleString()}</span>
                  <button onClick={() => deleteRoom(room.id)} className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>
              {room.expanded && (
                <div className="p-5 space-y-4">
                  {room.windows.map(w => (
                    <div key={w.id} className="bg-[#1a1a2e] rounded-xl p-4 border border-white/5">
                      <div className="flex justify-between mb-3">
                        <input type="text" value={w.name} onChange={(e) => updateWindow(room.id, w.id, { name: e.target.value })} className="bg-transparent font-medium outline-none" />
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-green-400">${calcWindowPrice(w).toLocaleString()}</span>
                          <button onClick={() => deleteWindow(room.id, w.id)} className="p-1 text-gray-500 hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Width (in)</label>
                          <input type="number" value={w.width} onChange={(e) => updateWindow(room.id, w.id, { width: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Height (in)</label>
                          <input type="number" value={w.height} onChange={(e) => updateWindow(room.id, w.id, { height: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Treatment</label>
                          <select value={w.treatment} onChange={(e) => updateWindow(room.id, w.id, { treatment: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none">
                            <option value="ripplefold">Ripplefold</option>
                            <option value="pinch-pleat">Pinch Pleat</option>
                            <option value="roman-shade">Roman Shade</option>
                            <option value="roller-shade">Roller Shade</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Lining</label>
                          <select value={w.lining} onChange={(e) => updateWindow(room.id, w.id, { lining: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none">
                            <option value="unlined">Unlined</option>
                            <option value="standard">Standard</option>
                            <option value="blackout">Blackout</option>
                            <option value="thermal">Thermal</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Hardware</label>
                          <select value={w.hardware} onChange={(e) => updateWindow(room.id, w.id, { hardware: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none">
                            <option value="none">None</option>
                            <option value="rod-standard">Rod Standard</option>
                            <option value="track-basic">Track Basic</option>
                            <option value="track-ripplefold">Track Ripplefold</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Motor</label>
                          <select value={w.motor} onChange={(e) => updateWindow(room.id, w.id, { motor: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm outline-none">
                            <option value="none">None</option>
                            <option value="somfy">Somfy ($285)</option>
                            <option value="lutron">Lutron ($425)</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  ))}
                  <button onClick={() => addWindow(room.id)} className="w-full py-3 border-2 border-dashed border-gray-700 hover:border-blue-500 rounded-xl text-gray-500 hover:text-blue-400 flex items-center justify-center gap-2">
                    <Plus className="w-5 h-5" />Add Window
                  </button>
                </div>
              )}
            </div>
          ))}

          {/* Add Room */}
          <button onClick={addRoom} className="w-full py-4 bg-[#0a0a12] hover:bg-[#1a1a2e] border border-gray-800 hover:border-blue-500 rounded-xl text-gray-400 hover:text-blue-400 flex items-center justify-center gap-2">
            <Plus className="w-5 h-5" />Add Room
          </button>

          {/* Back */}
          <button onClick={() => setCurrentQuote(null)} className="text-gray-500 hover:text-white">← Back to Quotes</button>
        </div>
      )}
    </div>
  )
}
