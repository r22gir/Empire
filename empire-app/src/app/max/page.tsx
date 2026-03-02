'use client'
import { useState, useRef, useEffect } from 'react'
import { Brain, Send, Mic, Upload, X, Loader2, Factory, Package, Users, TrendingUp, Square } from 'lucide-react'
import Link from 'next/link'

interface Msg { id: string; role: 'user' | 'max'; content: string }

export default function MaxPage() {
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [typing, setTyping] = useState(false)
  const [showAudio, setShowAudio] = useState(false)
  const [audioFile, setAudioFile] = useState<File|null>(null)
  const [audioUrl, setAudioUrl] = useState<string|null>(null)
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const recorder = useRef<MediaRecorder|null>(null)
  const chunks = useRef<Blob[]>([])
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const h = new Date().getHours()
    const g = h < 12 ? 'Buenos días' : h < 17 ? 'Buenas tardes' : 'Buenas noches'
    setMsgs([{ id: '1', role: 'max', content: `¡${g}! Soy MAX.\n\n🎤 Sube un audio y lo analizo.\n\n¿Qué necesitas?` }])
  }, [])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = (text?: string) => {
    const m = text || input.trim()
    if (!m) return
    setMsgs(p => [...p, { id: Date.now().toString(), role: 'user', content: m }])
    setInput('')
    setTyping(true)
    setTimeout(() => {
      const r = genResponse(m)
      setMsgs(p => [...p, { id: (Date.now()+1).toString(), role: 'max', content: r }])
      setTyping(false)
    }, 800)
  }

  const genResponse = (i: string): string => {
    const l = i.toLowerCase()
    if (l.includes('cotiza') || l.includes('quote')) return '📝 Ve a Workroom → Nueva Cotización'
    if (l.includes('inventario') || l.includes('stock')) return '📦 Ve a Inventory → Cargar Base'
    if (l.includes('cliente')) return '👥 Ve a CRM → Nuevo Contacto'
    if (l.includes('audio')) return '🎤 Click Audio arriba → Graba o sube archivo'
    return `Entiendo: "${i}"\n\nPuedo ayudar con:\n• Cotizaciones → /workroom\n• Inventario → /inventory\n• Clientes → /customers`
  }

  const startRec = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      recorder.current = new MediaRecorder(stream)
      chunks.current = []
      recorder.current.ondataavailable = (e) => { if (e.data.size > 0) chunks.current.push(e.data) }
      recorder.current.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        setAudioFile(new File([blob], 'rec.webm'))
        setAudioUrl(URL.createObjectURL(blob))
        stream.getTracks().forEach(t => t.stop())
      }
      recorder.current.start()
      setRecording(true)
    } catch { alert('Sin acceso al mic') }
  }

  const stopRec = () => { if (recorder.current) { recorder.current.stop(); setRecording(false) } }

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f && f.size < 25*1024*1024) { setAudioFile(f); setAudioUrl(URL.createObjectURL(f)) }
  }

  const transcribe = async () => {
    if (!audioFile) return
    setTranscribing(true)
    try {
      const fd = new FormData(); fd.append('audio', audioFile)
      const res = await fetch('http://localhost:8000/api/transcribe', { method: 'POST', body: fd })
      if (res.ok) {
        const d = await res.json()
        setShowAudio(false); setAudioFile(null); setAudioUrl(null)
        send(`🎤 Audio: ${d.text}`)
      } else { alert('Error transcripción') }
    } catch { alert('Backend no disponible') }
    setTranscribing(false)
  }

  const actions = [
    { label: 'Nueva Cotización', icon: Factory, href: '/workroom' },
    { label: 'Ver Stock', icon: Package, href: '/inventory' },
    { label: 'Agregar Cliente', icon: Users, href: '/customers' },
    { label: 'Finanzas', icon: TrendingUp, href: '/finance' },
  ]

  return (
    <div className="min-h-screen bg-[#030308] flex flex-col">
      <div className="bg-amber-500/10 border-b border-amber-500/20 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center"><Brain className="w-6 h-6" /></div>
            <div><h1 className="text-2xl font-bold">MAX <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Online</span></h1><p className="text-gray-500">AI Director</p></div>
          </div>
          <button onClick={() => setShowAudio(!showAudio)} className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold ${showAudio ? 'bg-amber-500 text-black' : 'bg-amber-500/20 text-amber-400'}`}><Mic className="w-5 h-5" />Audio</button>
        </div>
      </div>

      <div className="px-6 py-3 border-b border-white/10 flex gap-3 overflow-x-auto">
        {actions.map((a, i) => <Link key={i} href={a.href} className="flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 px-4 py-2 rounded-xl whitespace-nowrap"><a.icon className="w-4 h-4 text-amber-400" /><span className="text-sm">{a.label}</span></Link>)}
      </div>

      {showAudio && (
        <div className="px-6 py-4 bg-[#0a0a12] border-b border-white/10">
          {!audioFile ? (
            <div className="space-y-3 max-w-lg mx-auto">
              <button onClick={recording ? stopRec : startRec} className={`w-full py-4 rounded-xl font-semibold flex items-center justify-center gap-2 ${recording ? 'bg-red-500 animate-pulse' : 'bg-amber-500'}`}>
                {recording ? <><Square className="w-5 h-5" />Detener</> : <><Mic className="w-5 h-5" />Grabar</>}
              </button>
              <div className="relative">
                <input type="file" accept="audio/*" onChange={onFile} className="absolute inset-0 opacity-0 cursor-pointer" />
                <div className="py-4 border-2 border-dashed border-gray-700 rounded-xl text-center text-gray-400"><Upload className="w-5 h-5 inline mr-2" />Subir archivo (MP3, WAV)</div>
              </div>
            </div>
          ) : (
            <div className="space-y-3 max-w-lg mx-auto">
              <audio src={audioUrl!} controls className="w-full" />
              <div className="flex gap-3">
                <button onClick={() => { setAudioFile(null); setAudioUrl(null) }} className="flex-1 bg-white/10 py-3 rounded-xl"><X className="w-5 h-5 inline" /> Cancelar</button>
                <button onClick={transcribe} disabled={transcribing} className="flex-1 bg-amber-500 py-3 rounded-xl font-semibold disabled:opacity-50">
                  {transcribing ? <Loader2 className="w-5 h-5 inline animate-spin" /> : <Brain className="w-5 h-5 inline" />} Analizar
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {msgs.map(m => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${m.role === 'user' ? 'bg-amber-500 text-black' : 'bg-[#0a0a12] border border-white/10'}`}>
              {m.role === 'max' && <div className="flex items-center gap-2 mb-2 text-amber-400"><Brain className="w-4 h-4" /><span className="text-xs">MAX</span></div>}
              <p className="whitespace-pre-wrap text-sm">{m.content}</p>
            </div>
          </div>
        ))}
        {typing && <div className="flex justify-start"><div className="bg-[#0a0a12] border border-white/10 rounded-2xl px-5 py-3"><Loader2 className="w-5 h-5 animate-spin text-amber-400" /></div></div>}
        <div ref={endRef} />
      </div>

      <div className="p-4 border-t border-white/10 bg-[#0a0a12]">
        <div className="flex gap-3">
          <input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Pregunta a MAX..." className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
          <button onClick={() => send()} className="bg-amber-500 px-6 rounded-xl"><Send className="w-5 h-5" /></button>
        </div>
      </div>
    </div>
  )
}
