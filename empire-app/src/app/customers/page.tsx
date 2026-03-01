'use client'
import { useState, useEffect, useCallback } from 'react'
import { Users, Plus, Search, Phone, Mail, MapPin, Trash2, X, User, Loader2 } from 'lucide-react'

const API = 'http://localhost:8000/api/v1'

interface Customer { id: string; name: string; email: string; phone: string; address: string; type: string }

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', phone: '', address: '', type: 'client' })
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const loadCustomers = useCallback(async () => {
    try {
      const res = await fetch(`${API}/contacts/?type=client&limit=200`)
      if (res.ok) {
        const data = await res.json()
        setCustomers(data.contacts || [])
      }
    } catch (err) {
      console.error('Failed to load customers:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadCustomers() }, [loadCustomers])

  const save = async () => {
    if (!form.name) return
    setSaving(true)
    try {
      const res = await fetch(`${API}/contacts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.ok) {
        await loadCustomers()
        setShowModal(false)
        setForm({ name: '', email: '', phone: '', address: '', type: 'client' })
      } else {
        alert('Failed to save customer')
      }
    } catch (err) {
      console.error('Save failed:', err)
      alert('Backend not reachable. Check that it\'s running on port 8000.')
    } finally {
      setSaving(false)
    }
  }

  const del = async (id: string) => {
    if (!confirm('Delete this customer?')) return
    try {
      await fetch(`${API}/contacts/${id}`, { method: 'DELETE' })
      setCustomers(customers.filter(c => c.id !== id))
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const filtered = customers.filter(c => c.name.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center"><Users className="w-6 h-6" /></div>
          <div><h1 className="text-2xl font-bold">Customers</h1><p className="text-gray-500">{customers.length} total</p></div>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-pink-600 px-4 py-2 rounded-xl font-semibold"><Plus className="w-5 h-5" />Add Customer</button>
      </div>
      <div className="relative mb-6">
        <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
        <input type="text" placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-[#0a0a12] border border-white/10 rounded-xl pl-12 pr-4 py-3 outline-none" />
      </div>
      {loading ? (
        <div className="text-center py-16"><Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto" /><p className="text-gray-500 mt-4">Loading customers...</p></div>
      ) : customers.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-purple-500/20 flex items-center justify-center mx-auto mb-4"><Users className="w-10 h-10 text-purple-400" /></div>
          <h2 className="text-xl font-bold mb-2">No customers yet</h2>
          <p className="text-gray-500 mb-6">Add your first customer to get started</p>
          <button onClick={() => setShowModal(true)} className="bg-gradient-to-r from-purple-500 to-pink-600 px-6 py-3 rounded-xl font-semibold">Add First Customer</button>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map(c => (
            <div key={c.id} className="bg-[#0a0a12] rounded-xl border border-white/10 p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center"><User className="w-6 h-6 text-purple-400" /></div>
                <div>
                  <h3 className="font-semibold">{c.name}</h3>
                  <div className="flex gap-4 text-sm text-gray-500">
                    {c.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{c.email}</span>}
                    {c.phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{c.phone}</span>}
                    {c.address && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{c.address}</span>}
                  </div>
                </div>
              </div>
              <button onClick={() => del(c.id)} className="p-2 hover:bg-red-500/20 rounded-lg"><Trash2 className="w-4 h-4 text-gray-400" /></button>
            </div>
          ))}
        </div>
      )}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowModal(false)} />
          <div className="relative bg-[#0a0a12] border border-white/10 rounded-2xl w-full max-w-md p-6">
            <div className="flex justify-between mb-4"><h2 className="text-xl font-bold">Add Customer</h2><button onClick={() => setShowModal(false)}><X className="w-5 h-5" /></button></div>
            <div className="space-y-4">
              <input type="text" placeholder="Name *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <input type="tel" placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <input type="text" placeholder="Address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="flex-1 bg-white/10 py-3 rounded-xl">Cancel</button>
              <button onClick={save} disabled={saving} className="flex-1 bg-gradient-to-r from-purple-500 to-pink-600 py-3 rounded-xl font-semibold disabled:opacity-50">
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
