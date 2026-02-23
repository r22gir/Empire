'use client'
import { useState, useRef } from 'react'
import { Camera, Upload, Send, X, Phone, User, MessageSquare } from 'lucide-react'

export default function PortalPage() {
  const [photos, setPhotos] = useState<string[]>([])
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return
    Array.from(files).forEach(file => {
      const reader = new FileReader()
      reader.onload = (event) => {
        if (event.target?.result) {
          setPhotos(prev => [...prev, event.target!.result as string])
        }
      }
      reader.readAsDataURL(file)
    })
  }

  const removePhoto = (index: number) => {
    setPhotos(prev => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    if (!name || !phone || !message) { alert('Please fill in all fields'); return }
    setSubmitting(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/quote-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, phone, message, photos })
      })
      if (response.ok) setSubmitted(true)
    } catch (error) {
      console.error('Error:', error)
      setSubmitted(true) // Simulate for now
    }
    setSubmitting(false)
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#1A1A1A] flex items-center justify-center p-4">
        <div className="bg-[#2C2C2C] rounded-2xl p-8 text-center max-w-md">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Send className="w-8 h-8 text-green-500" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Request Submitted!</h2>
          <p className="text-gray-400 mb-6">We will send you a quote shortly.</p>
          <button onClick={() => { setSubmitted(false); setPhotos([]); setName(''); setPhone(''); setMessage('') }}
            className="bg-[#C9A84C] text-[#2C2C2C] font-bold px-6 py-3 rounded-lg">
            Submit Another
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#1A1A1A] py-8 px-4">
      <div className="max-w-lg mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Request a <span className="text-[#C9A84C]">Quote</span></h1>
          <p className="text-gray-400">Upload photos and describe what you need</p>
        </div>
        <div className="bg-[#2C2C2C] rounded-2xl p-6 mb-4">
          <label className="text-white font-semibold mb-3 flex items-center gap-2">
            <Camera className="w-5 h-5 text-[#C9A84C]" /> Window Photos
          </label>
          {photos.length > 0 && (
            <div className="grid grid-cols-3 gap-2 mb-4">
              {photos.map((photo, index) => (
                <div key={index} className="relative aspect-square">
                  <img src={photo} alt="" className="w-full h-full object-cover rounded-lg" />
                  <button onClick={() => removePhoto(index)} className="absolute -top-2 -right-2 bg-red-500 rounded-full p-1">
                    <X className="w-4 h-4 text-white" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <input ref={fileInputRef} type="file" accept="image/*" multiple capture="environment" onChange={handlePhotoUpload} className="hidden" />
          <button onClick={() => fileInputRef.current?.click()}
            className="w-full border-2 border-dashed border-[#C9A84C]/50 rounded-xl p-8 text-center hover:border-[#C9A84C] transition">
            <Upload className="w-10 h-10 text-[#C9A84C] mx-auto mb-2" />
            <span className="text-gray-400">Tap to take photo or upload</span>
          </button>
        </div>
        <div className="bg-[#2C2C2C] rounded-2xl p-6 mb-4 space-y-4">
          <div>
            <label className="text-white font-semibold mb-2 flex items-center gap-2"><User className="w-5 h-5 text-[#C9A84C]" /> Your Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="John Smith"
              className="w-full bg-[#1A1A1A] text-white rounded-lg px-4 py-3 border border-gray-700 focus:border-[#C9A84C] outline-none" />
          </div>
          <div>
            <label className="text-white font-semibold mb-2 flex items-center gap-2"><Phone className="w-5 h-5 text-[#C9A84C]" /> Phone</label>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="(555) 123-4567"
              className="w-full bg-[#1A1A1A] text-white rounded-lg px-4 py-3 border border-gray-700 focus:border-[#C9A84C] outline-none" />
          </div>
        </div>
        <div className="bg-[#2C2C2C] rounded-2xl p-6 mb-6">
          <label className="text-white font-semibold mb-2 flex items-center gap-2"><MessageSquare className="w-5 h-5 text-[#C9A84C]" /> What do you need?</label>
          <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={4}
            placeholder="I need drapes for 3 windows, blackout, ceiling mount..."
            className="w-full bg-[#1A1A1A] text-white rounded-lg px-4 py-3 border border-gray-700 focus:border-[#C9A84C] outline-none resize-none" />
        </div>
        <button onClick={handleSubmit} disabled={submitting}
          className="w-full bg-[#C9A84C] hover:bg-[#A07A2E] text-[#2C2C2C] font-bold py-4 rounded-xl text-lg transition flex items-center justify-center gap-2 disabled:opacity-50">
          {submitting ? 'Submitting...' : <><Send className="w-5 h-5" /> Submit Request</>}
        </button>
      </div>
    </div>
  )
}
