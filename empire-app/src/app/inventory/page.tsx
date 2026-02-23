'use client'
import { useState } from 'react'
import { Package, Plus, Search, AlertTriangle, Trash2, X, TrendingDown, TrendingUp } from 'lucide-react'

interface Item { id: string; name: string; category: string; quantity: number; minStock: number; unit: string; cost: number }

const CATEGORIES = ['Fabric', 'Hardware', 'Lining', 'Thread', 'Trim', 'Motors', 'Other']

export default function Inventory() {
  const [items, setItems] = useState<Item[]>([])
  const [showModal, setShowModal] = useState(false)
  const [search, setSearch] = useState('')
  const [form, setForm] = useState({ name: '', category: 'Fabric', quantity: 0, minStock: 5, unit: 'yards', cost: 0 })

  const save = () => {
    if (!form.name) return
    setItems([...items, { ...form, id: Date.now().toString() }])
    setShowModal(false)
    setForm({ name: '', category: 'Fabric', quantity: 0, minStock: 5, unit: 'yards', cost: 0 })
  }

  const updateQty = (id: string, delta: number) => setItems(items.map(i => i.id === id ? { ...i, quantity: Math.max(0, i.quantity + delta) } : i))
  const del = (id: string) => setItems(items.filter(i => i.id !== id))
  const lowStock = items.filter(i => i.quantity <= i.minStock)
  const filtered = items.filter(i => i.name.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center"><Package className="w-6 h-6" /></div>
          <div><h1 className="text-2xl font-bold">Inventory</h1><p className="text-gray-500">{items.length} items</p></div>
        </div>
        <button onClick={() => setShowModal(true)} className="flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-2 rounded-xl font-semibold"><Plus className="w-5 h-5" />Add Item</button>
      </div>

      {lowStock.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 mb-6 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-400">{lowStock.length} items low on stock</span>
        </div>
      )}

      <div className="relative mb-6">
        <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
        <input type="text" placeholder="Search..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-[#0a0a12] border border-white/10 rounded-xl pl-12 pr-4 py-3 outline-none" />
      </div>

      {items.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4"><Package className="w-10 h-10 text-green-400" /></div>
          <h2 className="text-xl font-bold mb-2">No inventory yet</h2>
          <p className="text-gray-500 mb-6">Add your first item</p>
          <button onClick={() => setShowModal(true)} className="bg-gradient-to-r from-green-500 to-emerald-600 px-6 py-3 rounded-xl font-semibold">Add First Item</button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(item => (
            <div key={item.id} className={`bg-[#0a0a12] rounded-xl border p-5 ${item.quantity <= item.minStock ? 'border-red-500/50' : 'border-white/10'}`}>
              <div className="flex justify-between mb-3">
                <div><h3 className="font-semibold">{item.name}</h3><span className="text-xs bg-white/10 px-2 py-0.5 rounded">{item.category}</span></div>
                <button onClick={() => del(item.id)} className="text-gray-500 hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-2xl font-bold ${item.quantity <= item.minStock ? 'text-red-400' : ''}`}>{item.quantity}</p>
                  <p className="text-sm text-gray-500">{item.unit}</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => updateQty(item.id, -1)} className="w-10 h-10 bg-red-500/20 text-red-400 rounded-lg flex items-center justify-center"><TrendingDown className="w-5 h-5" /></button>
                  <button onClick={() => updateQty(item.id, 1)} className="w-10 h-10 bg-green-500/20 text-green-400 rounded-lg flex items-center justify-center"><TrendingUp className="w-5 h-5" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowModal(false)} />
          <div className="relative bg-[#0a0a12] border border-white/10 rounded-2xl w-full max-w-md p-6">
            <div className="flex justify-between mb-4"><h2 className="text-xl font-bold">Add Item</h2><button onClick={() => setShowModal(false)}><X className="w-5 h-5" /></button></div>
            <div className="space-y-4">
              <input type="text" placeholder="Item name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none">
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-4">
                <input type="number" placeholder="Quantity" value={form.quantity || ''} onChange={(e) => setForm({ ...form, quantity: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
                <input type="number" placeholder="Min Stock" value={form.minStock || ''} onChange={(e) => setForm({ ...form, minStock: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              </div>
              <input type="text" placeholder="Unit (yards, pcs)" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="flex-1 bg-white/10 py-3 rounded-xl">Cancel</button>
              <button onClick={save} className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 py-3 rounded-xl font-semibold">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
