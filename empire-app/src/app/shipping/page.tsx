'use client'
import { useState, useEffect } from 'react'
import { Truck, Plus, ArrowDown, ArrowUp, X } from 'lucide-react'

interface Shipment { id: string; type: 'in' | 'out'; carrier: string; tracking: string; items: string; status: string }

export default function Shipping() {
  const [shipments, setShipments] = useState<Shipment[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ type: 'in' as const, carrier: 'FedEx', tracking: '', items: '' })

  useEffect(() => { const s = localStorage.getItem('empire_ship'); if (s) setShipments(JSON.parse(s)) }, [])
  useEffect(() => { localStorage.setItem('empire_ship', JSON.stringify(shipments)) }, [shipments])

  const add = () => {
    if (!form.items) return
    setShipments([{ ...form, id: Date.now().toString(), status: 'pending' }, ...shipments])
    setShowAdd(false)
    setForm({ type: 'in', carrier: 'FedEx', tracking: '', items: '' })
  }

  const updateStatus = (id: string, status: string) => setShipments(shipments.map(s => s.id === id ? { ...s, status } : s))

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center"><Truck className="w-6 h-6" /></div>
          <div><h1 className="text-2xl font-bold">ShippingForge</h1><p className="text-gray-500">{shipments.length} envíos</p></div>
        </div>
        <button onClick={() => setShowAdd(true)} className="bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 rounded-xl font-semibold flex items-center gap-2"><Plus className="w-5 h-5" />Nuevo</button>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-[#0a0a12] rounded-xl p-4 border border-white/10"><div className="flex items-center gap-2 mb-1"><ArrowDown className="w-4 h-4 text-green-400" /><span className="text-gray-500">Entrantes</span></div><p className="text-2xl font-bold">{shipments.filter(s => s.type === 'in').length}</p></div>
        <div className="bg-[#0a0a12] rounded-xl p-4 border border-white/10"><div className="flex items-center gap-2 mb-1"><ArrowUp className="w-4 h-4 text-blue-400" /><span className="text-gray-500">Salientes</span></div><p className="text-2xl font-bold">{shipments.filter(s => s.type === 'out').length}</p></div>
      </div>

      {shipments.length === 0 ? (
        <div className="text-center py-16">
          <Truck className="w-16 h-16 text-cyan-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Sin envíos</h2>
          <div className="flex gap-4 justify-center mt-6">
            <button onClick={() => { setForm({...form, type: 'in'}); setShowAdd(true) }} className="bg-green-500/20 text-green-400 px-6 py-3 rounded-xl">📥 Entrante</button>
            <button onClick={() => { setForm({...form, type: 'out'}); setShowAdd(true) }} className="bg-blue-500/20 text-blue-400 px-6 py-3 rounded-xl">📤 Saliente</button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {shipments.map(s => (
            <div key={s.id} className="bg-[#0a0a12] rounded-xl border border-white/10 p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${s.type === 'in' ? 'bg-green-500/20' : 'bg-blue-500/20'}`}>
                    {s.type === 'in' ? <ArrowDown className="w-5 h-5 text-green-400" /> : <ArrowUp className="w-5 h-5 text-blue-400" />}
                  </div>
                  <div><p className="font-semibold">{s.carrier} {s.tracking && `• ${s.tracking}`}</p><p className="text-sm text-gray-400">{s.items}</p></div>
                </div>
                <select value={s.status} onChange={(e) => updateStatus(s.id, e.target.value)} className={`text-xs px-3 py-1 rounded-full outline-none ${s.status === 'delivered' ? 'bg-green-500/20 text-green-400' : s.status === 'transit' ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20'}`}>
                  <option value="pending">Pendiente</option>
                  <option value="transit">En Tránsito</option>
                  <option value="delivered">Entregado</option>
                </select>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowAdd(false)} />
          <div className="relative bg-[#0a0a12] border border-white/10 rounded-2xl w-full max-w-md p-6">
            <h2 className="text-xl font-bold mb-4">Nuevo Envío</h2>
            <div className="flex gap-2 mb-4">
              <button onClick={() => setForm({...form, type: 'in'})} className={`flex-1 py-3 rounded-xl flex items-center justify-center gap-2 ${form.type === 'in' ? 'bg-green-500 text-black' : 'bg-white/10'}`}><ArrowDown className="w-5 h-5" />Entrante</button>
              <button onClick={() => setForm({...form, type: 'out'})} className={`flex-1 py-3 rounded-xl flex items-center justify-center gap-2 ${form.type === 'out' ? 'bg-blue-500' : 'bg-white/10'}`}><ArrowUp className="w-5 h-5" />Saliente</button>
            </div>
            <div className="space-y-3">
              <select value={form.carrier} onChange={(e) => setForm({...form, carrier: e.target.value})} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none">
                {['FedEx', 'UPS', 'USPS', 'DHL', 'Local'].map(c => <option key={c}>{c}</option>)}
              </select>
              <input placeholder="# Tracking" value={form.tracking} onChange={(e) => setForm({...form, tracking: e.target.value})} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <input placeholder="Items *" value={form.items} onChange={(e) => setForm({...form, items: e.target.value})} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowAdd(false)} className="flex-1 bg-white/10 py-3 rounded-xl">Cancelar</button>
              <button onClick={add} className="flex-1 bg-cyan-500 py-3 rounded-xl font-semibold">Crear</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
