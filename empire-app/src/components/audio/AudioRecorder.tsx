'use client'
import { useState, useRef } from 'react'
import { Mic, Square, Upload, Loader2, Check, X, FileAudio } from 'lucide-react'

interface AudioRecorderProps {
  onTranscription: (text: string) => void
  onClose?: () => void
}

export default function AudioRecorder({ onTranscription, onClose }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [transcription, setTranscription] = useState('')
  const [error, setError] = useState('')
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  const startRecording = async () => {
    try {
      setError('')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorder.current = new MediaRecorder(stream)
      chunks.current = []

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data)
      }

      mediaRecorder.current.onstop = () => {
        const blob = new Blob(chunks.current, { type: 'audio/webm' })
        setAudioBlob(blob)
        setAudioUrl(URL.createObjectURL(blob))
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.current.start()
      setIsRecording(true)
    } catch (err) {
      setError('No se pudo acceder al micrófono. Verifica los permisos.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop()
      setIsRecording(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (file.size > 25 * 1024 * 1024) {
        setError('Archivo muy grande. Máximo 25MB.')
        return
      }
      setAudioBlob(file)
      setAudioUrl(URL.createObjectURL(file))
      setError('')
    }
  }

  const transcribeAudio = async () => {
    if (!audioBlob) return

    setIsProcessing(true)
    setError('')

    try {
      // Opción 1: Usar API de OpenAI Whisper (requiere API key)
      // Opción 2: Usar Web Speech API (gratis, solo Chrome)
      // Opción 3: Enviar a backend con Whisper local
      
      // Por ahora usamos Web Speech API como fallback
      const recognition = new (window.webkitSpeechRecognition || window.SpeechRecognition)()
      recognition.lang = 'es-ES'
      recognition.continuous = true
      recognition.interimResults = false

      // Para archivos, necesitamos reproducir y capturar
      // Simulamos transcripción por ahora - en producción usar Whisper API
      
      // Intentar con el backend
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.webm')

      const response = await fetch('http://localhost:8000/api/transcribe', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        setTranscription(data.text)
      } else {
        // Fallback: pedir al usuario que escriba
        setError('Transcripción automática no disponible. Escribe el contenido manualmente.')
      }
    } catch (err) {
      // Si no hay backend, mostrar opción manual
      setError('Servicio de transcripción no disponible. Puedes escribir el contenido manualmente o configurar Whisper.')
    } finally {
      setIsProcessing(false)
    }
  }

  const submitTranscription = () => {
    if (transcription.trim()) {
      onTranscription(transcription.trim())
      if (onClose) onClose()
    }
  }

  const reset = () => {
    setAudioBlob(null)
    setAudioUrl(null)
    setTranscription('')
    setError('')
  }

  return (
    <div className="bg-[#0a0a12] border border-white/10 rounded-2xl p-6">
      <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
        <Mic className="w-5 h-5 text-amber-400" />
        Audio a Tarea
      </h3>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 mb-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Recording Controls */}
      {!audioBlob && (
        <div className="space-y-4">
          <div className="flex gap-4">
            {/* Record Button */}
            <button
              onClick={isRecording ? stopRecording : startRecording}
              className={`flex-1 flex items-center justify-center gap-3 py-6 rounded-xl font-semibold transition ${
                isRecording 
                  ? 'bg-red-500 animate-pulse' 
                  : 'bg-gradient-to-r from-amber-500 to-orange-600 hover:opacity-90'
              }`}
            >
              {isRecording ? (
                <>
                  <Square className="w-6 h-6" />
                  <span>Detener Grabación</span>
                </>
              ) : (
                <>
                  <Mic className="w-6 h-6" />
                  <span>Grabar Audio</span>
                </>
              )}
            </button>
          </div>

          {/* Recording indicator */}
          {isRecording && (
            <div className="flex items-center justify-center gap-2 text-red-400">
              <span className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
              <span>Grabando...</span>
            </div>
          )}

          {/* Upload Option */}
          <div className="relative">
            <input
              type="file"
              accept="audio/*"
              onChange={handleFileUpload}
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
            <div className="flex items-center justify-center gap-3 py-4 border-2 border-dashed border-gray-700 hover:border-amber-500 rounded-xl text-gray-400 hover:text-amber-400 transition cursor-pointer">
              <Upload className="w-5 h-5" />
              <span>O sube un archivo de audio (MP3, WAV, M4A - máx 25MB)</span>
            </div>
          </div>
        </div>
      )}

      {/* Audio Preview */}
      {audioUrl && (
        <div className="space-y-4">
          <div className="bg-white/5 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <FileAudio className="w-5 h-5 text-amber-400" />
              <span className="text-sm text-gray-400">Audio listo para transcribir</span>
            </div>
            <audio src={audioUrl} controls className="w-full" />
          </div>

          {/* Transcribe Button */}
          {!transcription && (
            <div className="flex gap-3">
              <button
                onClick={reset}
                className="px-4 py-3 bg-white/10 rounded-xl hover:bg-white/20 transition"
              >
                <X className="w-5 h-5" />
              </button>
              <button
                onClick={transcribeAudio}
                disabled={isProcessing}
                className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-amber-500 to-orange-600 py-3 rounded-xl font-semibold disabled:opacity-50"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Transcribiendo...</span>
                  </>
                ) : (
                  <>
                    <Mic className="w-5 h-5" />
                    <span>Transcribir Audio</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Manual Transcription Input */}
          {error && !transcription && (
            <div className="space-y-3">
              <p className="text-sm text-gray-400">Escribe el contenido del audio manualmente:</p>
              <textarea
                value={transcription}
                onChange={(e) => setTranscription(e.target.value)}
                placeholder="Escribe aquí lo que dice el audio..."
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 min-h-[100px] outline-none focus:border-amber-500"
              />
            </div>
          )}

          {/* Transcription Result */}
          {transcription && (
            <div className="space-y-3">
              <label className="text-sm text-gray-400">Transcripción (puedes editar):</label>
              <textarea
                value={transcription}
                onChange={(e) => setTranscription(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 min-h-[100px] outline-none focus:border-amber-500"
              />
              <div className="flex gap-3">
                <button
                  onClick={reset}
                  className="px-6 py-3 bg-white/10 rounded-xl hover:bg-white/20 transition"
                >
                  Cancelar
                </button>
                <button
                  onClick={submitTranscription}
                  className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 py-3 rounded-xl font-semibold"
                >
                  <Check className="w-5 h-5" />
                  <span>Crear Tarea</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Info */}
      <p className="text-xs text-gray-600 mt-4 text-center">
        El audio se transcribe usando IA. Para mejor precisión, habla claro y en un ambiente silencioso.
      </p>
    </div>
  )
}

// Add type declaration for webkit speech recognition
declare global {
  interface Window {
    webkitSpeechRecognition: any
    SpeechRecognition: any
  }
}
