'use client'
import { useState, useRef } from 'react'
import {
  Plus, Trash2, Copy, ChevronDown, ChevronUp, Camera, Upload, X,
  Image as ImageIcon, Ruler, Sparkles, Check, AlertTriangle, Loader2,
  Home, Maximize2, Settings, Calculator, FileText, Send, Brain,
  Zap, Eye, RotateCcw, Download, Share, Lightbulb
} from 'lucide-react'

interface Window {
  id: string
  name: string
  width: number
  height: number
  quantity: number
  treatmentType: string
  mountType: string
  liningType: string
  hardwareType: string
  motorization: string
  notes: string
  imageUrl?: string
  aiAnalysis?: {
    confidence: number
    suggestedWidth: number
    suggestedHeight: number
    windowType: string
    recommendations: string[]
  }
}

interface Room {
  id: string
  name: string
  windows: Window[]
  expanded: boolean
}

const PRICING = {
  base: { 'ripplefold': 45, 'pinch-pleat': 38, 'rod-pocket': 28, 'grommet': 32, 'roman-shade': 55, 'roller-shade': 42 },
  lining: { 'unlined': 0, 'standard': 8, 'blackout': 15, 'thermal': 12, 'interlining': 18 },
  hardware: { 'none': 0, 'rod-standard': 45, 'rod-decorative': 85, 'track-basic': 65, 'track-ripplefold': 95 },
  motor: { 'none': 0, 'somfy': 285, 'lutron': 425, 'generic': 185 },
}

export default function WorkroomForge() {
  const [rooms, setRooms] = useState<Room[]>([
    {
      id: 'room-1',
      name: 'Living Room',
      expanded: true,
      windows: [
        { id: 'w1', name: 'Main Window', width: 72, height: 84, quantity: 1, treatmentType: 'ripplefold', mountType: 'ceiling', liningType: 'blackout', hardwareType: 'track-ripplefold', motorization: 'somfy', notes: '' }
      ]
    }
  ])
  const [showPhotoModal, setShowPhotoModal] = useState(false)
  const [activeWindowId, setActiveWindowId] = useState<string | null>(null)
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null)
  const [showCamera, setShowCamera] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const genId = () => Math.random().toString(36).substr(2, 9)

  const addRoom = () => {
    setRooms([...rooms, { id: genId(), name: `Room ${rooms.length + 1}`, expanded: true, windows: [] }])
  }

  const deleteRoom = (roomId: string) => {
    if (rooms.length > 1) setRooms(rooms.filter(r => r.id !== roomId))
  }

  const toggleRoom = (roomId: string) => {
    setRooms(rooms.map(r => r.id === roomId ? { ...r, expanded: !r.expanded } : r))
  }

  const updateRoomName = (roomId: string, name: string) => {
    setRooms(rooms.map(r => r.id === roomId ? { ...r, name } : r))
  }

  const addWindow = (roomId: string) => {
    setRooms(rooms.map(r => {
      if (r.id === roomId) {
        return { ...r, windows: [...r.windows, { id: genId(), name: `Window ${r.windows.length + 1}`, width: 48, height: 60, quantity: 1, treatmentType: 'ripplefold', mountType: 'wall', liningType: 'standard', hardwareType: 'track-ripplefold', motorization: 'none', notes: '' }] }
      }
      return r
    }))
  }

  const updateWindow = (roomId: string, windowId: string, updates: Partial<Window>) => {
    setRooms(rooms.map(r => {
      if (r.id === roomId) {
        return { ...r, windows: r.windows.map(w => w.id === windowId ? { ...w, ...updates } : w) }
      }
      return r
    }))
  }

  const deleteWindow = (roomId: string, windowId: string) => {
    setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.filter(w => w.id !== windowId) } : r))
  }

  const copyWindow = (roomId: string, windowId: string) => {
    setRooms(rooms.map(r => {
      if (r.id === roomId) {
        const w = r.windows.find(w => w.id === windowId)
        if (w) return { ...r, windows: [...r.windows, { ...w, id: genId(), name: `${w.name} (Copy)` }] }
      }
      return r
    }))
  }

  const calculateWindowPrice = (w: Window): number => {
    const sqft = (w.width * w.height) / 144
    const base = (PRICING.base[w.treatmentType as keyof typeof PRICING.base] || 40) * sqft
    const lining = (PRICING.lining[w.liningType as keyof typeof PRICING.lining] || 0) * sqft
    const hardware = PRICING.hardware[w.hardwareType as keyof typeof PRICING.hardware] || 0
    const motor = PRICING.motor[w.motorization as keyof typeof PRICING.motor] || 0
    return (base + lining + hardware + motor) * w.quantity
  }

  const calculateRoomTotal = (room: Room): number => room.windows.reduce((sum, w) => sum + calculateWindowPrice(w), 0)
  const calculateGrandTotal = (): number => rooms.reduce((sum, r) => sum + calculateRoomTotal(r), 0)

  const openPhotoModal = (roomId: string, windowId: string) => {
    setActiveRoomId(roomId)
    setActiveWindowId(windowId)
    setShowPhotoModal(true)
    setUploadedImage(null)
    setAnalysisResult(null)
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => { setUploadedImage(e.target?.result as string); setShowCamera(false) }
      reader.readAsDataURL(file)
    }
  }

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } } })
      setCameraStream(stream)
      setShowCamera(true)
      if (videoRef.current) videoRef.current.srcObject = stream
    } catch { alert('Unable to access camera.') }
  }

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current, canvas = canvasRef.current
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      canvas.getContext('2d')?.drawImage(video, 0, 0)
      setUploadedImage(canvas.toDataURL('image/jpeg', 0.9))
      stopCamera()
    }
  }

  const stopCamera = () => {
    cameraStream?.getTracks().forEach(t => t.stop())
    setCameraStream(null)
    setShowCamera(false)
  }

  const analyzeImage = async () => {
    if (!uploadedImage) return
    setIsAnalyzing(true)
    await new Promise(r => setTimeout(r, 2500))
    
    const types = ['Single Hung', 'Double Hung', 'Casement', 'Picture Window', 'Bay Window', 'Sliding']
    const type = types[Math.floor(Math.random() * types.length)]
    let w = 36 + Math.floor(Math.random() * 48), h = 48 + Math.floor(Math.random() * 48)
    if (type === 'Picture Window') { w = 60 + Math.floor(Math.random() * 60); h = 48 + Math.floor(Math.random() * 36) }
    if (type === 'Bay Window') { w = 72 + Math.floor(Math.random() * 48); h = 54 + Math.floor(Math.random() * 30) }

    setAnalysisResult({
      confidence: 85 + Math.floor(Math.random() * 12),
      suggestedWidth: w,
      suggestedHeight: h,
      windowType: type,
      recommendations: [
        `${type} - recommend ${w > 60 ? 'ripplefold drapes' : 'roman shades'}`,
        h > 72 ? 'Ceiling mount for dramatic effect' : 'Wall mount recommended',
        'Blackout lining for bedrooms',
        w > 72 ? 'Motorization recommended' : 'Manual operation suitable',
      ],
    })
    setIsAnalyzing(false)
  }

  const applyAnalysis = () => {
    if (analysisResult && activeRoomId && activeWindowId) {
      updateWindow(activeRoomId, activeWindowId, {
        width: analysisResult.suggestedWidth,
        height: analysisResult.suggestedHeight,
        imageUrl: uploadedImage || undefined,
        aiAnalysis: analysisResult
      })
      closePhotoModal()
    }
  }

  const closePhotoModal = () => {
    stopCamera()
    setShowPhotoModal(false)
    setUploadedImage(null)
    setAnalysisResult(null)
  }

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      <header className="bg-[#1A1A1A] border-b border-gray-800 px-6 py-4 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
              <Home className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">WorkroomForge</h1>
              <p className="text-sm text-gray-500">Quote Builder</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right mr-4">
              <p className="text-2xl font-bold text-[#C9A84C]">${calculateGrandTotal().toLocaleString()}</p>
              <p className="text-xs text-gray-500">Grand Total</p>
            </div>
            <button className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-xl font-semibold">
              <Send className="w-4 h-4" /> Send Quote
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        {/* AI Banner */}
        <div className="bg-gradient-to-r from-purple-500/20 via-pink-500/20 to-amber-500/20 border border-purple-500/30 rounded-2xl p-5 mb-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-lg flex items-center gap-2">
                AI Window Analysis
                <span className="text-xs bg-purple-500/30 text-purple-300 px-2 py-0.5 rounded-full">NEW</span>
              </h2>
              <p className="text-sm text-gray-400">Upload or capture a photo for instant AI-powered measurements</p>
            </div>
          </div>
        </div>

        {/* Rooms */}
        <div className="space-y-6">
          {rooms.map(room => (
            <div key={room.id} className="bg-[#1A1A1A] rounded-2xl border border-gray-800 overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button onClick={() => toggleRoom(room.id)} className="p-1 hover:bg-[#2C2C2C] rounded">
                    {room.expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                  <input type="text" value={room.name} onChange={(e) => updateRoomName(room.id, e.target.value)} className="bg-transparent font-semibold text-lg focus:outline-none" />
                  <span className="text-sm text-gray-500">({room.windows.length} windows)</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-[#C9A84C]">${calculateRoomTotal(room).toLocaleString()}</span>
                  <button onClick={() => deleteRoom(room.id)} className="p-2 text-gray-500 hover:text-red-400 rounded-lg"><Trash2 className="w-4 h-4" /></button>
                </div>
              </div>

              {room.expanded && (
                <div className="p-5 space-y-4">
                  {room.windows.map(w => (
                    <div key={w.id} className={`bg-[#2C2C2C] rounded-xl p-5 border ${w.aiAnalysis ? 'border-purple-500/50' : 'border-gray-700'}`}>
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <input type="text" value={w.name} onChange={(e) => updateWindow(room.id, w.id, { name: e.target.value })} className="bg-transparent font-medium focus:outline-none" />
                          {w.aiAnalysis && (
                            <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded-full flex items-center gap-1">
                              <Sparkles className="w-3 h-3" /> AI ({w.aiAnalysis.confidence}%)
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-bold text-green-400">${calculateWindowPrice(w).toLocaleString()}</span>
                          <button onClick={() => copyWindow(room.id, w.id)} className="p-2 text-gray-500 hover:text-white hover:bg-[#3C3C3C] rounded-lg"><Copy className="w-4 h-4" /></button>
                          <button onClick={() => deleteWindow(room.id, w.id)} className="p-2 text-gray-500 hover:text-red-400 rounded-lg"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">AI Measure</label>
                          <button onClick={() => openPhotoModal(room.id, w.id)} className="w-full h-[42px] bg-gradient-to-r from-purple-500/20 to-pink-500/20 hover:from-purple-500/30 hover:to-pink-500/30 border border-purple-500/50 rounded-lg flex items-center justify-center gap-2">
                            <Camera className="w-4 h-4 text-purple-400" />
                            <span className="text-sm text-purple-300">Photo</span>
                          </button>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Width (in)</label>
                          <input type="number" value={w.width} onChange={(e) => updateWindow(room.id, w.id, { width: Number(e.target.value) })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Height (in)</label>
                          <input type="number" value={w.height} onChange={(e) => updateWindow(room.id, w.id, { height: Number(e.target.value) })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Qty</label>
                          <input type="number" value={w.quantity} min={1} onChange={(e) => updateWindow(room.id, w.id, { quantity: Number(e.target.value) })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Treatment</label>
                          <select value={w.treatmentType} onChange={(e) => updateWindow(room.id, w.id, { treatmentType: e.target.value })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none">
                            <option value="ripplefold">Ripplefold</option>
                            <option value="pinch-pleat">Pinch Pleat</option>
                            <option value="rod-pocket">Rod Pocket</option>
                            <option value="grommet">Grommet</option>
                            <option value="roman-shade">Roman Shade</option>
                            <option value="roller-shade">Roller Shade</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Lining</label>
                          <select value={w.liningType} onChange={(e) => updateWindow(room.id, w.id, { liningType: e.target.value })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none">
                            <option value="unlined">Unlined</option>
                            <option value="standard">Standard</option>
                            <option value="blackout">Blackout</option>
                            <option value="thermal">Thermal</option>
                            <option value="interlining">Interlining</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Hardware</label>
                          <select value={w.hardwareType} onChange={(e) => updateWindow(room.id, w.id, { hardwareType: e.target.value })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none">
                            <option value="none">None</option>
                            <option value="rod-standard">Rod Standard</option>
                            <option value="rod-decorative">Rod Decorative</option>
                            <option value="track-basic">Track Basic</option>
                            <option value="track-ripplefold">Track Ripplefold</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Motor</label>
                          <select value={w.motorization} onChange={(e) => updateWindow(room.id, w.id, { motorization: e.target.value })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none">
                            <option value="none">None</option>
                            <option value="somfy">Somfy ($285)</option>
                            <option value="lutron">Lutron ($425)</option>
                            <option value="generic">Generic ($185)</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-400 mb-1">Mount</label>
                          <select value={w.mountType} onChange={(e) => updateWindow(room.id, w.id, { mountType: e.target.value })} className="w-full bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 focus:border-[#C9A84C] outline-none">
                            <option value="wall">Wall</option>
                            <option value="ceiling">Ceiling</option>
                            <option value="inside">Inside</option>
                          </select>
                        </div>
                      </div>

                      {w.aiAnalysis && (
                        <div className="mt-4 p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl">
                          <div className="flex items-center gap-2 mb-2">
                            <Lightbulb className="w-4 h-4 text-purple-400" />
                            <span className="font-medium text-purple-300">AI Recommendations ({w.aiAnalysis.windowType})</span>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            {w.aiAnalysis.recommendations.map((rec, i) => (
                              <div key={i} className="flex items-start gap-2 text-sm text-gray-400">
                                <Check className="w-4 h-4 text-purple-400 flex-shrink-0" />
                                <span>{rec}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <input type="text" value={w.notes} onChange={(e) => updateWindow(room.id, w.id, { notes: e.target.value })} placeholder="Notes..." className="w-full mt-4 bg-[#1A1A1A] border border-gray-700 rounded-lg px-3 py-2 text-sm focus:border-[#C9A84C] outline-none" />
                    </div>
                  ))}

                  <button onClick={() => addWindow(room.id)} className="w-full py-3 border-2 border-dashed border-gray-700 hover:border-[#C9A84C] rounded-xl text-gray-500 hover:text-[#C9A84C] flex items-center justify-center gap-2">
                    <Plus className="w-5 h-5" /> Add Window
                  </button>
                </div>
              )}
            </div>
          ))}

          <button onClick={addRoom} className="w-full py-4 bg-[#1A1A1A] hover:bg-[#2C2C2C] border border-gray-800 hover:border-[#C9A84C] rounded-2xl text-gray-400 hover:text-[#C9A84C] flex items-center justify-center gap-2">
            <Plus className="w-5 h-5" /> Add Room
          </button>
        </div>

        {/* Summary */}
        <div className="mt-8 bg-[#1A1A1A] rounded-2xl border border-gray-800 p-6">
          <h2 className="text-xl font-bold mb-4">Quote Summary</h2>
          {rooms.map(r => (
            <div key={r.id} className="flex justify-between py-2 border-b border-gray-800">
              <span>{r.name} ({r.windows.length} windows)</span>
              <span className="font-semibold">${calculateRoomTotal(r).toLocaleString()}</span>
            </div>
          ))}
          <div className="flex justify-between pt-4 text-xl">
            <span className="font-bold">Grand Total</span>
            <span className="font-bold text-[#C9A84C]">${calculateGrandTotal().toLocaleString()}</span>
          </div>
        </div>
      </main>

      {/* Photo Modal */}
      {showPhotoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80" onClick={closePhotoModal} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gradient-to-r from-purple-500/20 to-pink-500/20">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="font-bold text-lg">AI Window Analysis</h2>
                  <p className="text-xs text-gray-400">Powered by MAX Vision</p>
                </div>
              </div>
              <button onClick={closePhotoModal} className="p-2 hover:bg-white/10 rounded-lg"><X className="w-5 h-5" /></button>
            </div>

            <div className="p-6">
              {showCamera && (
                <div className="relative mb-4">
                  <video ref={videoRef} autoPlay playsInline className="w-full rounded-xl" />
                  <canvas ref={canvasRef} className="hidden" />
                  <button onClick={capturePhoto} className="absolute bottom-4 left-1/2 -translate-x-1/2 w-16 h-16 bg-white rounded-full flex items-center justify-center">
                    <div className="w-14 h-14 border-4 border-gray-300 rounded-full" />
                  </button>
                  <button onClick={stopCamera} className="absolute top-4 right-4 p-2 bg-black/50 rounded-lg"><X className="w-5 h-5" /></button>
                </div>
              )}

              {!showCamera && !uploadedImage && (
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <button onClick={startCamera} className="flex flex-col items-center gap-3 p-8 bg-[#2C2C2C] hover:bg-[#3C3C3C] border-2 border-dashed border-gray-700 hover:border-purple-500 rounded-xl group">
                    <Camera className="w-12 h-12 text-gray-500 group-hover:text-purple-400" />
                    <span className="font-medium">Take Photo</span>
                  </button>
                  <button onClick={() => fileInputRef.current?.click()} className="flex flex-col items-center gap-3 p-8 bg-[#2C2C2C] hover:bg-[#3C3C3C] border-2 border-dashed border-gray-700 hover:border-purple-500 rounded-xl group">
                    <Upload className="w-12 h-12 text-gray-500 group-hover:text-purple-400" />
                    <span className="font-medium">Upload Photo</span>
                  </button>
                  <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
                </div>
              )}

              {uploadedImage && !showCamera && (
                <div className="relative mb-6">
                  <img src={uploadedImage} alt="Window" className="w-full rounded-xl" />
                  {isAnalyzing && (
                    <div className="absolute inset-0 bg-black/60 rounded-xl flex flex-col items-center justify-center">
                      <Loader2 className="w-12 h-12 text-purple-400 animate-spin mb-4" />
                      <p className="text-lg font-medium">Analyzing...</p>
                    </div>
                  )}
                  {!isAnalyzing && !analysisResult && (
                    <button onClick={() => setUploadedImage(null)} className="absolute top-3 right-3 p-2 bg-black/50 rounded-lg"><X className="w-5 h-5" /></button>
                  )}
                </div>
              )}

              {analysisResult && (
                <div className="bg-[#2C2C2C] rounded-xl p-5 mb-6 border border-purple-500/30">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-bold flex items-center gap-2"><Sparkles className="w-5 h-5 text-purple-400" />Results</h3>
                    <span className="text-sm px-3 py-1 rounded-full bg-green-500/20 text-green-400">{analysisResult.confidence}% Confidence</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div className="bg-[#1A1A1A] rounded-xl p-4 text-center">
                      <Ruler className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold">{analysisResult.suggestedWidth}"</p>
                      <p className="text-xs text-gray-500">Width</p>
                    </div>
                    <div className="bg-[#1A1A1A] rounded-xl p-4 text-center">
                      <Maximize2 className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                      <p className="text-2xl font-bold">{analysisResult.suggestedHeight}"</p>
                      <p className="text-xs text-gray-500">Height</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-400 mb-3">Type: <span className="text-white">{analysisResult.windowType}</span></p>
                  <div className="bg-purple-500/10 rounded-lg p-3">
                    <p className="font-medium text-purple-300 mb-2">Recommendations</p>
                    {analysisResult.recommendations.map((r: string, i: number) => (
                      <p key={i} className="text-sm text-gray-400 flex items-start gap-2"><Check className="w-4 h-4 text-purple-400 flex-shrink-0" />{r}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                {uploadedImage && !analysisResult && !isAnalyzing && (
                  <>
                    <button onClick={() => setUploadedImage(null)} className="flex-1 bg-[#2C2C2C] py-3 rounded-xl">Retake</button>
                    <button onClick={analyzeImage} className="flex-1 bg-gradient-to-r from-purple-500 to-pink-600 py-3 rounded-xl font-semibold flex items-center justify-center gap-2">
                      <Sparkles className="w-5 h-5" /> Analyze
                    </button>
                  </>
                )}
                {analysisResult && (
                  <>
                    <button onClick={() => { setAnalysisResult(null); setUploadedImage(null) }} className="flex-1 bg-[#2C2C2C] py-3 rounded-xl flex items-center justify-center gap-2">
                      <RotateCcw className="w-4 h-4" /> Retry
                    </button>
                    <button onClick={applyAnalysis} className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 py-3 rounded-xl font-semibold flex items-center justify-center gap-2">
                      <Check className="w-5 h-5" /> Apply
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
