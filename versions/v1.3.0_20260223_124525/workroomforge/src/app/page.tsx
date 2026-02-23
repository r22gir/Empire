'use client'
import { useState, useEffect } from 'react'
import { 
  Inbox, Clock, CheckCircle, DollarSign, Send, Eye, Phone, MessageSquare,
  Settings, Plus, Minus, Copy, Trash2, ChevronDown, ChevronUp,
  Filter, Search, Bell, Image as ImageIcon, Wand2, Loader2, Ruler, Home
} from 'lucide-react'

// Types
interface WindowItem {
  id: string
  width: string
  height: string
  quantity: number
  treatment: string
  lining: string
  hardware: string
  motorization: string
  notes: string
  laborCost: number
  materialsCost: number
  hardwareCost: number
}

interface Room {
  id: string
  name: string
  windows: WindowItem[]
  photos: string[]
  expanded: boolean
}

interface QuoteRequest {
  id: string
  name: string
  phone: string
  message: string
  photos: string[]
  status: string
  created_at: string
  quote: any
  reference_object?: string
}

// Pricing data (based on Rowley Company)
const PRICING = {
  labor: {
    drapes: 85,          // per width
    roman_shades: 120,   // per shade
    blinds: 45,
    sheers: 65,
    valance: 55,
  },
  lining: {
    unlined: 0,
    standard: 8,         // per yard
    blackout: 15,
    thermal: 18,
    interlining: 22,
  },
  hardware: {
    standard_rod: 45,    // per foot
    decorative_rod: 85,
    ripplefold_track: 35,
    motorized_basic: 450,    // per window
    motorized_somfy: 650,
    motorized_lutron: 850,
    customer_supplies: 0,
  }
}

const createEmptyWindow = (): WindowItem => ({
  id: Math.random().toString(36).substr(2, 9),
  width: '',
  height: '',
  quantity: 1,
  treatment: 'drapes',
  lining: 'standard',
  hardware: 'standard_rod',
  motorization: 'none',
  notes: '',
  laborCost: 0,
  materialsCost: 0,
  hardwareCost: 0,
})

const createEmptyRoom = (name: string = 'New Room'): Room => ({
  id: Math.random().toString(36).substr(2, 9),
  name,
  windows: [createEmptyWindow()],
  photos: [],
  expanded: true,
})

export default function WorkroomDashboard() {
  const [requests, setRequests] = useState<QuoteRequest[]>([])
  const [selected, setSelected] = useState<QuoteRequest | null>(null)
  const [rooms, setRooms] = useState<Room[]>([])
  const [sending, setSending] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [quoteNotes, setQuoteNotes] = useState('')

  useEffect(() => {
    fetchRequests()
    const interval = setInterval(fetchRequests, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selected) {
      // Initialize with one room from the request
      setRooms([{
        ...createEmptyRoom('Main Area'),
        photos: selected.photos || []
      }])
      setQuoteNotes('')
      setAnalysisResult(null)
    }
  }, [selected?.id])

  const fetchRequests = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/quote-requests')
      const data = await res.json()
      setRequests(data.requests || [])
    } catch (e) { console.error(e) }
  }

  // Room management
  const addRoom = () => {
    setRooms([...rooms, createEmptyRoom(`Room ${rooms.length + 1}`)])
  }

  const removeRoom = (roomId: string) => {
    if (rooms.length > 1) {
      setRooms(rooms.filter(r => r.id !== roomId))
    }
  }

  const updateRoom = (roomId: string, updates: Partial<Room>) => {
    setRooms(rooms.map(r => r.id === roomId ? { ...r, ...updates } : r))
  }

  const toggleRoom = (roomId: string) => {
    setRooms(rooms.map(r => r.id === roomId ? { ...r, expanded: !r.expanded } : r))
  }

  // Window management
  const addWindow = (roomId: string) => {
    setRooms(rooms.map(r => {
      if (r.id === roomId) {
        return { ...r, windows: [...r.windows, createEmptyWindow()] }
      }
      return r
    }))
  }

  const removeWindow = (roomId: string, windowId: string) => {
    setRooms(rooms.map(r => {
      if (r.id === roomId && r.windows.length > 1) {
        return { ...r, windows: r.windows.filter(w => w.id !== windowId) }
      }
      return r
    }))
  }

  const copyWindow = (roomId: string, windowId: string) => {
    setRooms(rooms.map(r => {
      if (r.id === roomId) {
        const windowToCopy = r.windows.find(w => w.id === windowId)
        if (windowToCopy) {
          const newWindow = { ...windowToCopy, id: Math.random().toString(36).substr(2, 9) }
          return { ...r, windows: [...r.windows, newWindow] }
        }
      }
      return r
    }))
  }

  const updateWindow = (roomId: string, windowId: string, updates: Partial<WindowItem>) => {
    setRooms(rooms.map(r => {
      if (r.id === roomId) {
        return {
          ...r,
          windows: r.windows.map(w => {
            if (w.id === windowId) {
              const updated = { ...w, ...updates }
              // Recalculate costs
              const width = parseFloat(updated.width) || 0
              const height = parseFloat(updated.height) || 0
              const sqFt = (width * height) / 144
              const widthFt = width / 12
              
              // Labor based on treatment
              const laborRate = PRICING.labor[updated.treatment as keyof typeof PRICING.labor] || 85
              updated.laborCost = Math.round(laborRate * updated.quantity * (sqFt > 0 ? Math.max(1, sqFt / 10) : 1))
              
              // Materials (fabric + lining)
              const liningRate = PRICING.lining[updated.lining as keyof typeof PRICING.lining] || 0
              const fabricYards = sqFt > 0 ? Math.ceil(sqFt / 4) : 2
              updated.materialsCost = Math.round((25 + liningRate) * fabricYards * updated.quantity)
              
              // Hardware
              const hwKey = updated.motorization !== 'none' ? updated.motorization : updated.hardware
              const hwRate = PRICING.hardware[hwKey as keyof typeof PRICING.hardware] || 0
              updated.hardwareCost = Math.round(hwRate * (updated.motorization !== 'none' ? 1 : widthFt || 1) * updated.quantity)
              
              return updated
            }
            return w
          })
        }
      }
      return r
    }))
  }

  // Calculate totals
  const calculateRoomTotal = (room: Room) => {
    return room.windows.reduce((sum, w) => sum + w.laborCost + w.materialsCost + w.hardwareCost, 0)
  }

  const calculateGrandTotal = () => {
    return rooms.reduce((sum, r) => sum + calculateRoomTotal(r), 0)
  }

  const calculateTotalLabor = () => rooms.reduce((sum, r) => sum + r.windows.reduce((s, w) => s + w.laborCost, 0), 0)
  const calculateTotalMaterials = () => rooms.reduce((sum, r) => sum + r.windows.reduce((s, w) => s + w.materialsCost, 0), 0)
  const calculateTotalHardware = () => rooms.reduce((sum, r) => sum + r.windows.reduce((s, w) => s + w.hardwareCost, 0), 0)

  // AI Analysis
  const analyzePhoto = async (roomId: string, photoIndex: number) => {
    const room = rooms.find(r => r.id === roomId)
    if (!room?.photos?.[photoIndex]) return
    
    setAnalyzing(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/smart-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: room.photos[photoIndex],
          message: selected?.message || ''
        })
      })
      const data = await response.json()
      setAnalysisResult(data)
      
      // Auto-fill first empty window in this room
      if (data?.measurements) {
        const m = data.measurements
        const emptyWindow = room.windows.find(w => !w.width || !w.height)
        if (emptyWindow) {
          updateWindow(roomId, emptyWindow.id, {
            width: String(m.estimated_width || ''),
            height: String(m.estimated_height || ''),
            treatment: m.treatment_suggestion || 'drapes',
          })
        }
      }
    } catch (e) {
      console.error(e)
      setAnalysisResult({ status: 'error', analysis: 'Failed to analyze' })
    }
    setAnalyzing(false)
  }

  // Generate quote summary
  const generateQuoteNotes = () => {
    const lines: string[] = []
    rooms.forEach(room => {
      lines.push(`\n📍 ${room.name}`)
      lines.push('─'.repeat(30))
      room.windows.forEach((w, i) => {
        if (w.width && w.height) {
          lines.push(`  Window ${i + 1}: ${w.width}" W × ${w.height}" H (Qty: ${w.quantity})`)
          lines.push(`    Treatment: ${w.treatment.replace('_', ' ')}`)
          lines.push(`    Lining: ${w.lining.replace('_', ' ')}`)
          lines.push(`    Hardware: ${w.hardware.replace('_', ' ')}`)
          if (w.motorization !== 'none') {
            lines.push(`    Motorization: ${w.motorization.replace('_', ' ')}`)
          }
          lines.push(`    Subtotal: $${(w.laborCost + w.materialsCost + w.hardwareCost).toLocaleString()}`)
        }
      })
      lines.push(`  Room Total: $${calculateRoomTotal(room).toLocaleString()}`)
    })
    lines.push(`\n${'═'.repeat(30)}`)
    lines.push(`GRAND TOTAL: $${calculateGrandTotal().toLocaleString()}`)
    setQuoteNotes(lines.join('\n'))
  }

  // Send quote
  const sendQuote = async () => {
    if (!selected) return
    setSending(true)
    try {
      await fetch(`http://localhost:8000/api/v1/quote-requests/${selected.id}/quote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          price: `$${calculateGrandTotal().toLocaleString()}`,
          notes: quoteNotes,
          rooms: rooms,
          totals: {
            labor: calculateTotalLabor(),
            materials: calculateTotalMaterials(),
            hardware: calculateTotalHardware(),
            grand_total: calculateGrandTotal()
          },
          sent_at: new Date().toISOString()
        })
      })
      fetchRequests()
      setSelected(null)
    } catch (e) { console.error(e) }
    setSending(false)
  }

  const pending = requests.filter(r => r.status === 'pending')

  const getStatusColor = (status: string) => ({
    pending: 'bg-yellow-500/20 text-yellow-400',
    quoted: 'bg-blue-500/20 text-blue-400',
    approved: 'bg-green-500/20 text-green-400',
  }[status] || 'bg-gray-500/20 text-gray-400')

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white flex">
      {/* Sidebar */}
      <aside className="w-64 bg-[#1A1A1A] border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span className="text-2xl">🏭</span>
            <span className="text-[#C9A84C]">WorkroomForge</span>
          </h1>
        </div>
        
        <nav className="flex-1 p-2">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-1 bg-[#C9A84C]/20 text-[#C9A84C] border-l-2 border-[#C9A84C]">
            <Inbox className="w-5 h-5" />
            <span className="flex-1 text-left">Quote Requests</span>
            {pending.length > 0 && (
              <span className="bg-[#C9A84C] text-black text-xs px-2 py-0.5 rounded-full">{pending.length}</span>
            )}
          </button>
        </nav>

        <div className="p-4 border-t border-gray-800">
          <button className="w-full flex items-center gap-3 px-4 py-2 text-gray-400 hover:text-white rounded-lg hover:bg-[#2C2C2C]">
            <Settings className="w-5 h-5" />
            <span>Settings</span>
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-[#1A1A1A] border-b border-gray-800 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">📥 Quote Requests</h2>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
              <input type="text" placeholder="Search..." className="bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm w-64 focus:border-[#C9A84C] outline-none" />
            </div>
            <button className="relative p-2 text-gray-400 hover:text-white">
              <Bell className="w-5 h-5" />
              {pending.length > 0 && <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-xs flex items-center justify-center">{pending.length}</span>}
            </button>
          </div>
        </header>

        <div className="flex-1 flex overflow-hidden">
          {/* Request List */}
          <div className="w-72 bg-[#1A1A1A] border-r border-gray-800 overflow-y-auto">
            <div className="p-3 border-b border-gray-800 text-sm text-gray-400">
              {requests.length} requests
            </div>
            {requests.map(req => (
              <div
                key={req.id}
                onClick={() => setSelected(req)}
                className={`p-4 cursor-pointer hover:bg-[#2C2C2C] border-b border-gray-800 ${selected?.id === req.id ? 'bg-[#2C2C2C] border-l-2 border-[#C9A84C]' : ''}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold truncate">{req.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(req.status)}`}>{req.status}</span>
                </div>
                <p className="text-gray-400 text-sm truncate">{req.message}</p>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                  <Clock className="w-3 h-3" />
                  {new Date(req.created_at).toLocaleDateString()}
                  {req.photos?.length > 0 && (
                    <span className="flex items-center gap-1 ml-auto">
                      <ImageIcon className="w-3 h-3" /> {req.photos.length}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Quote Builder */}
          <div className="flex-1 overflow-y-auto p-6">
            {selected ? (
              <div className="max-w-5xl mx-auto">
                {/* Customer Info */}
                <div className="bg-[#1A1A1A] rounded-xl p-4 mb-4 border border-gray-800 flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-bold">{selected.name}</h3>
                    <p className="text-gray-400 flex items-center gap-2">
                      <Phone className="w-4 h-4" /> {selected.phone}
                    </p>
                    <p className="text-gray-500 text-sm mt-1">{selected.message}</p>
                  </div>
                  <span className={`px-4 py-2 rounded-full ${getStatusColor(selected.status)}`}>{selected.status}</span>
                </div>

                {/* Rooms */}
                {rooms.map((room, roomIndex) => (
                  <div key={room.id} className="bg-[#1A1A1A] rounded-xl mb-4 border border-gray-800 overflow-hidden">
                    {/* Room Header */}
                    <div 
                      className="flex items-center justify-between px-4 py-3 bg-[#2C2C2C] cursor-pointer"
                      onClick={() => toggleRoom(room.id)}
                    >
                      <div className="flex items-center gap-3">
                        {room.expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        <Home className="w-4 h-4 text-[#C9A84C]" />
                        <input
                          type="text"
                          value={room.name}
                          onChange={(e) => updateRoom(room.id, { name: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                          className="bg-transparent font-semibold focus:outline-none focus:border-b border-[#C9A84C]"
                        />
                        <span className="text-sm text-gray-500">({room.windows.length} windows)</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[#C9A84C] font-bold">${calculateRoomTotal(room).toLocaleString()}</span>
                        {rooms.length > 1 && (
                          <button onClick={(e) => { e.stopPropagation(); removeRoom(room.id); }} className="text-red-400 hover:text-red-300 p-1">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {room.expanded && (
                      <div className="p-4">
                        {/* Photos for this room */}
                        {room.photos.length > 0 && (
                          <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
                            {room.photos.map((photo, i) => (
                              <div key={i} className="relative flex-shrink-0">
                                <img src={photo} alt="" className="w-24 h-24 object-cover rounded-lg border border-gray-700" />
                                <button
                                  onClick={() => analyzePhoto(room.id, i)}
                                  disabled={analyzing}
                                  className="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-purple-600 hover:bg-purple-700 text-xs px-2 py-1 rounded flex items-center gap-1"
                                >
                                  {analyzing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                                  AI
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Windows */}
                        {room.windows.map((window, windowIndex) => (
                          <div key={window.id} className="bg-[#0D0D0D] rounded-lg p-4 mb-3 border border-gray-800">
                            <div className="flex items-center justify-between mb-3">
                              <span className="font-semibold text-sm">Window {windowIndex + 1}</span>
                              <div className="flex items-center gap-2">
                                {/* Quantity */}
                                <div className="flex items-center gap-1 bg-[#2C2C2C] rounded-lg px-2 py-1">
                                  <span className="text-xs text-gray-400">Qty:</span>
                                  <button onClick={() => updateWindow(room.id, window.id, { quantity: Math.max(1, window.quantity - 1) })} className="text-gray-400 hover:text-white">
                                    <Minus className="w-3 h-3" />
                                  </button>
                                  <span className="w-6 text-center font-bold">{window.quantity}</span>
                                  <button onClick={() => updateWindow(room.id, window.id, { quantity: window.quantity + 1 })} className="text-gray-400 hover:text-white">
                                    <Plus className="w-3 h-3" />
                                  </button>
                                </div>
                                <button onClick={() => copyWindow(room.id, window.id)} className="text-blue-400 hover:text-blue-300 p-1" title="Copy window">
                                  <Copy className="w-4 h-4" />
                                </button>
                                {room.windows.length > 1 && (
                                  <button onClick={() => removeWindow(room.id, window.id)} className="text-red-400 hover:text-red-300 p-1">
                                    <Trash2 className="w-4 h-4" />
                                  </button>
                                )}
                              </div>
                            </div>

                            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                              {/* Dimensions */}
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">Width"</label>
                                <input
                                  type="number"
                                  value={window.width}
                                  onChange={(e) => updateWindow(room.id, window.id, { width: e.target.value })}
                                  placeholder="48"
                                  className="w-full bg-[#1A1A1A] rounded px-2 py-1.5 border border-gray-700 focus:border-[#C9A84C] outline-none text-sm"
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">Height"</label>
                                <input
                                  type="number"
                                  value={window.height}
                                  onChange={(e) => updateWindow(room.id, window.id, { height: e.target.value })}
                                  placeholder="60"
                                  className="w-full bg-[#1A1A1A] rounded px-2 py-1.5 border border-gray-700 focus:border-[#C9A84C] outline-none text-sm"
                                />
                              </div>
                              
                              {/* Treatment */}
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">Treatment</label>
                                <select
                                  value={window.treatment}
                                  onChange={(e) => updateWindow(room.id, window.id, { treatment: e.target.value })}
                                  className="w-full bg-[#1A1A1A] rounded px-2 py-1.5 border border-gray-700 focus:border-[#C9A84C] outline-none text-sm"
                                >
                                  <option value="drapes">Drapes</option>
                                  <option value="roman_shades">Roman Shades</option>
                                  <option value="blinds">Blinds</option>
                                  <option value="sheers">Sheers</option>
                                  <option value="valance">Valance</option>
                                </select>
                              </div>

                              {/* Lining */}
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">Lining</label>
                                <select
                                  value={window.lining}
                                  onChange={(e) => updateWindow(room.id, window.id, { lining: e.target.value })}
                                  className="w-full bg-[#1A1A1A] rounded px-2 py-1.5 border border-gray-700 focus:border-[#C9A84C] outline-none text-sm"
                                >
                                  <option value="unlined">Unlined</option>
                                  <option value="standard">Standard</option>
                                  <option value="blackout">Blackout</option>
                                  <option value="thermal">Thermal/Bump</option>
                                  <option value="interlining">Interlining</option>
                                </select>
                              </div>

                              {/* Hardware */}
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">Hardware</label>
                                <select
                                  value={window.hardware}
                                  onChange={(e) => updateWindow(room.id, window.id, { hardware: e.target.value })}
                                  className="w-full bg-[#1A1A1A] rounded px-2 py-1.5 border border-gray-700 focus:border-[#C9A84C] outline-none text-sm"
                                >
                                  <option value="standard_rod">Standard Rod</option>
                                  <option value="decorative_rod">Decorative Rod</option>
                                  <option value="ripplefold_track">Ripplefold Track</option>
                                  <option value="customer_supplies">Customer Supplies</option>
                                </select>
                              </div>

                              {/* Motorization */}
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">Motor</label>
                                <select
                                  value={window.motorization}
                                  onChange={(e) => updateWindow(room.id, window.id, { motorization: e.target.value })}
                                  className="w-full bg-[#1A1A1A] rounded px-2 py-1.5 border border-gray-700 focus:border-[#C9A84C] outline-none text-sm"
                                >
                                  <option value="none">None</option>
                                  <option value="motorized_basic">Basic Motor</option>
                                  <option value="motorized_somfy">Somfy</option>
                                  <option value="motorized_lutron">Lutron</option>
                                </select>
                              </div>
                            </div>

                            {/* Window pricing */}
                            <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-800 text-sm">
                              <div className="flex gap-4 text-gray-400">
                                <span>Labor: ${window.laborCost}</span>
                                <span>Materials: ${window.materialsCost}</span>
                                <span>Hardware: ${window.hardwareCost}</span>
                              </div>
                              <span className="font-bold text-[#C9A84C]">
                                ${((window.laborCost + window.materialsCost + window.hardwareCost) * window.quantity).toLocaleString()}
                                {window.quantity > 1 && <span className="text-xs text-gray-500 ml-1">× {window.quantity}</span>}
                              </span>
                            </div>
                          </div>
                        ))}

                        <button
                          onClick={() => addWindow(room.id)}
                          className="w-full py-2 border border-dashed border-gray-700 rounded-lg text-gray-400 hover:text-white hover:border-[#C9A84C] transition flex items-center justify-center gap-2"
                        >
                          <Plus className="w-4 h-4" /> Add Window
                        </button>
                      </div>
                    )}
                  </div>
                ))}

                {/* Add Room Button */}
                <button
                  onClick={addRoom}
                  className="w-full py-3 mb-4 bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl text-gray-300 flex items-center justify-center gap-2 transition"
                >
                  <Plus className="w-5 h-5" /> Add Room
                </button>

                {/* Totals & Send */}
                <div className="bg-[#1A1A1A] rounded-xl p-5 border border-[#C9A84C]">
                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="text-center">
                      <p className="text-gray-400 text-sm">Labor</p>
                      <p className="text-xl font-bold">${calculateTotalLabor().toLocaleString()}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-gray-400 text-sm">Materials</p>
                      <p className="text-xl font-bold">${calculateTotalMaterials().toLocaleString()}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-gray-400 text-sm">Hardware</p>
                      <p className="text-xl font-bold">${calculateTotalHardware().toLocaleString()}</p>
                    </div>
                    <div className="text-center bg-[#C9A84C]/20 rounded-lg py-2">
                      <p className="text-[#C9A84C] text-sm">Grand Total</p>
                      <p className="text-2xl font-bold text-[#C9A84C]">${calculateGrandTotal().toLocaleString()}</p>
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm text-gray-400">Quote Notes</label>
                      <button onClick={generateQuoteNotes} className="text-xs text-[#C9A84C] hover:underline">
                        📝 Generate Summary
                      </button>
                    </div>
                    <textarea
                      value={quoteNotes}
                      onChange={(e) => setQuoteNotes(e.target.value)}
                      rows={6}
                      className="w-full bg-[#0D0D0D] rounded-lg px-3 py-2 border border-gray-700 focus:border-[#C9A84C] outline-none text-sm font-mono"
                      placeholder="Click 'Generate Summary' or type custom notes..."
                    />
                  </div>

                  <button
                    onClick={sendQuote}
                    disabled={sending || calculateGrandTotal() === 0}
                    className="w-full bg-[#C9A84C] hover:bg-[#A07A2E] text-[#1A1A1A] font-bold py-4 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50 transition text-lg"
                  >
                    <Send className="w-5 h-5" />
                    {sending ? 'Sending...' : `Send Quote - $${calculateGrandTotal().toLocaleString()}`}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <Eye className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-lg">Select a request to start quoting</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
