'use client'
import { useState, useEffect } from 'react'
import { Package, Plus, Search, AlertTriangle, Trash2, X, TrendingDown, TrendingUp, Download, Filter, RefreshCw } from 'lucide-react'

interface Item {
  id: string
  sku: string
  name: string
  category: string
  subcategory: string
  supplier: string
  quantity: number
  minStock: number
  unit: string
  costPrice: number
  sellPrice: number
  location: string
}

// Base de datos de materiales pre-cargados
const DEFAULT_MATERIALS: Omit<Item, 'id'>[] = [
  // TELAS
  { sku: 'FAB-SILK-001', name: 'Seda Dupioni - Ivory', category: 'Telas', subcategory: 'Seda', supplier: 'Rowley', quantity: 0, minStock: 10, unit: 'yardas', costPrice: 45, sellPrice: 85, location: 'A1' },
  { sku: 'FAB-SILK-002', name: 'Seda Dupioni - Champagne', category: 'Telas', subcategory: 'Seda', supplier: 'Rowley', quantity: 0, minStock: 10, unit: 'yardas', costPrice: 45, sellPrice: 85, location: 'A1' },
  { sku: 'FAB-LIN-001', name: 'Lino Belga - Natural', category: 'Telas', subcategory: 'Lino', supplier: 'Rowley', quantity: 0, minStock: 15, unit: 'yardas', costPrice: 35, sellPrice: 65, location: 'A2' },
  { sku: 'FAB-LIN-002', name: 'Lino Belga - Blanco', category: 'Telas', subcategory: 'Lino', supplier: 'Rowley', quantity: 0, minStock: 15, unit: 'yardas', costPrice: 35, sellPrice: 65, location: 'A2' },
  { sku: 'FAB-VEL-001', name: 'Terciopelo - Carbón', category: 'Telas', subcategory: 'Terciopelo', supplier: 'Rowley', quantity: 0, minStock: 10, unit: 'yardas', costPrice: 55, sellPrice: 95, location: 'A3' },
  { sku: 'FAB-VEL-002', name: 'Terciopelo - Navy', category: 'Telas', subcategory: 'Terciopelo', supplier: 'Rowley', quantity: 0, minStock: 10, unit: 'yardas', costPrice: 55, sellPrice: 95, location: 'A3' },
  { sku: 'FAB-SHR-001', name: 'Velo Sheer - Blanco', category: 'Telas', subcategory: 'Sheers', supplier: 'Rowley', quantity: 0, minStock: 20, unit: 'yardas', costPrice: 12, sellPrice: 28, location: 'A4' },
  { sku: 'FAB-OUT-001', name: 'Sunbrella Canvas - Natural', category: 'Telas', subcategory: 'Outdoor', supplier: 'Sunbrella', quantity: 0, minStock: 10, unit: 'yardas', costPrice: 35, sellPrice: 65, location: 'A5' },
  { sku: 'FAB-BLK-001', name: 'Blackout - Blanco', category: 'Telas', subcategory: 'Blackout', supplier: 'Rowley', quantity: 0, minStock: 15, unit: 'yardas', costPrice: 28, sellPrice: 55, location: 'A6' },
  
  // FORROS
  { sku: 'LIN-STD-001', name: 'Forro Sateen Standard - Blanco', category: 'Forros', subcategory: 'Standard', supplier: 'Rowley', quantity: 0, minStock: 25, unit: 'yardas', costPrice: 6, sellPrice: 12, location: 'B1' },
  { sku: 'LIN-STD-002', name: 'Forro Sateen Standard - Ivory', category: 'Forros', subcategory: 'Standard', supplier: 'Rowley', quantity: 0, minStock: 25, unit: 'yardas', costPrice: 6, sellPrice: 12, location: 'B1' },
  { sku: 'LIN-BLK-001', name: 'Forro Blackout - Blanco', category: 'Forros', subcategory: 'Blackout', supplier: 'Rowley', quantity: 0, minStock: 20, unit: 'yardas', costPrice: 12, sellPrice: 22, location: 'B2' },
  { sku: 'LIN-THR-001', name: 'Interlining Térmico', category: 'Forros', subcategory: 'Térmico', supplier: 'Rowley', quantity: 0, minStock: 15, unit: 'yardas', costPrice: 15, sellPrice: 28, location: 'B3' },
  
  // HERRAJES
  { sku: 'HW-TRK-001', name: 'Riel Ripplefold - Blanco', category: 'Herrajes', subcategory: 'Rieles', supplier: 'Kirsch', quantity: 0, minStock: 5, unit: 'pies', costPrice: 8, sellPrice: 15, location: 'C1' },
  { sku: 'HW-TRK-002', name: 'Riel Ripplefold - Negro', category: 'Herrajes', subcategory: 'Rieles', supplier: 'Kirsch', quantity: 0, minStock: 5, unit: 'pies', costPrice: 8, sellPrice: 15, location: 'C1' },
  { sku: 'HW-ROD-001', name: 'Barra Decorativa 1.5" - Brass', category: 'Herrajes', subcategory: 'Barras', supplier: 'Graber', quantity: 0, minStock: 3, unit: 'pies', costPrice: 12, sellPrice: 25, location: 'C2' },
  { sku: 'HW-ROD-002', name: 'Barra Decorativa 1.5" - Negro', category: 'Herrajes', subcategory: 'Barras', supplier: 'Graber', quantity: 0, minStock: 3, unit: 'pies', costPrice: 12, sellPrice: 25, location: 'C2' },
  { sku: 'HW-BRK-001', name: 'Brackets Standard (par)', category: 'Herrajes', subcategory: 'Brackets', supplier: 'Graber', quantity: 0, minStock: 20, unit: 'pares', costPrice: 8, sellPrice: 18, location: 'C3' },
  { sku: 'HW-RNG-001', name: 'Anillos Drapery (10pk)', category: 'Herrajes', subcategory: 'Anillos', supplier: 'Graber', quantity: 0, minStock: 10, unit: 'packs', costPrice: 15, sellPrice: 32, location: 'C3' },
  { sku: 'HW-FIN-001', name: 'Finial Ball - Brass', category: 'Herrajes', subcategory: 'Finiales', supplier: 'Graber', quantity: 0, minStock: 6, unit: 'pares', costPrice: 25, sellPrice: 55, location: 'C4' },
  
  // MOTORES
  { sku: 'MOT-SOM-001', name: 'Somfy Glydea 35 DCT', category: 'Motores', subcategory: 'Somfy', supplier: 'Somfy', quantity: 0, minStock: 2, unit: 'unidad', costPrice: 285, sellPrice: 485, location: 'D1' },
  { sku: 'MOT-SOM-002', name: 'Somfy Glydea 60 DCT', category: 'Motores', subcategory: 'Somfy', supplier: 'Somfy', quantity: 0, minStock: 2, unit: 'unidad', costPrice: 325, sellPrice: 545, location: 'D1' },
  { sku: 'MOT-LUT-001', name: 'Lutron Sivoia QS', category: 'Motores', subcategory: 'Lutron', supplier: 'Lutron', quantity: 0, minStock: 2, unit: 'unidad', costPrice: 425, sellPrice: 695, location: 'D2' },
  
  // INSUMOS
  { sku: 'SUP-THR-001', name: 'Hilo Blanco (5000yd)', category: 'Insumos', subcategory: 'Hilos', supplier: 'Rowley', quantity: 0, minStock: 5, unit: 'carretes', costPrice: 8, sellPrice: 15, location: 'E1' },
  { sku: 'SUP-BUC-001', name: 'Buckram 4"', category: 'Insumos', subcategory: 'Entretelas', supplier: 'Rowley', quantity: 0, minStock: 20, unit: 'yardas', costPrice: 3, sellPrice: 6, location: 'E2' },
  { sku: 'SUP-WGT-001', name: 'Pesas de Plomo (100pc)', category: 'Insumos', subcategory: 'Pesas', supplier: 'Rowley', quantity: 0, minStock: 5, unit: 'cajas', costPrice: 25, sellPrice: 45, location: 'E3' },
  { sku: 'SUP-HK-001', name: 'Ganchos Drapery (100pc)', category: 'Insumos', subcategory: 'Ganchos', supplier: 'Rowley', quantity: 0, minStock: 5, unit: 'cajas', costPrice: 12, sellPrice: 25, location: 'E4' },
  { sku: 'SUP-VEL-001', name: 'Velcro Blanco (25yd)', category: 'Insumos', subcategory: 'Velcro', supplier: 'Rowley', quantity: 0, minStock: 3, unit: 'rollos', costPrice: 35, sellPrice: 65, location: 'E5' },
  
  // TRIM
  { sku: 'TRM-CRD-001', name: 'Cordón Decorativo - Oro', category: 'Trim', subcategory: 'Cordones', supplier: 'Rowley', quantity: 0, minStock: 15, unit: 'yardas', costPrice: 8, sellPrice: 18, location: 'F1' },
  { sku: 'TRM-FRG-001', name: 'Flecos Bullion 3" - Oro', category: 'Trim', subcategory: 'Flecos', supplier: 'Rowley', quantity: 0, minStock: 10, unit: 'yardas', costPrice: 22, sellPrice: 45, location: 'F2' },
  { sku: 'TRM-TAS-001', name: 'Borla Tieback Grande - Oro', category: 'Trim', subcategory: 'Borlas', supplier: 'Rowley', quantity: 0, minStock: 4, unit: 'unidad', costPrice: 35, sellPrice: 75, location: 'F3' },
]

const CATEGORIES = ['Todos', 'Telas', 'Forros', 'Herrajes', 'Motores', 'Insumos', 'Trim']
const SUPPLIERS = ['Todos', 'Rowley', 'Somfy', 'Lutron', 'Kirsch', 'Graber', 'Sunbrella']

export default function InventoryPage() {
  const [items, setItems] = useState<Item[]>([])
  const [showModal, setShowModal] = useState(false)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('Todos')
  const [supplierFilter, setSupplierFilter] = useState('Todos')
  const [showLowStock, setShowLowStock] = useState(false)
  const [form, setForm] = useState({
    sku: '', name: '', category: 'Telas', subcategory: '', supplier: 'Rowley',
    quantity: 0, minStock: 5, unit: 'yardas', costPrice: 0, sellPrice: 0, location: ''
  })

  useEffect(() => {
    const saved = localStorage.getItem('empire_inventory')
    if (saved) {
      setItems(JSON.parse(saved))
    }
  }, [])

  useEffect(() => {
    if (items.length > 0) {
      localStorage.setItem('empire_inventory', JSON.stringify(items))
    }
  }, [items])

  const loadDefaults = () => {
    if (confirm('¿Cargar materiales predeterminados? Esto no borrará los existentes.')) {
      const newItems = DEFAULT_MATERIALS.map(m => ({ ...m, id: Math.random().toString(36).substr(2, 9) }))
      setItems([...items, ...newItems])
    }
  }

  const addItem = () => {
    if (!form.name) return
    setItems([{ ...form, id: Date.now().toString() }, ...items])
    setShowModal(false)
    setForm({ sku: '', name: '', category: 'Telas', subcategory: '', supplier: 'Rowley', quantity: 0, minStock: 5, unit: 'yardas', costPrice: 0, sellPrice: 0, location: '' })
  }

  const updateQty = (id: string, delta: number) => {
    setItems(items.map(i => i.id === id ? { ...i, quantity: Math.max(0, i.quantity + delta) } : i))
  }

  const deleteItem = (id: string) => {
    if (confirm('¿Eliminar este item?')) {
      setItems(items.filter(i => i.id !== id))
    }
  }

  const lowStockItems = items.filter(i => i.quantity <= i.minStock && i.quantity > 0)
  const outOfStock = items.filter(i => i.quantity === 0)

  const filtered = items.filter(i => {
    const matchSearch = i.name.toLowerCase().includes(search.toLowerCase()) || i.sku.toLowerCase().includes(search.toLowerCase())
    const matchCategory = categoryFilter === 'Todos' || i.category === categoryFilter
    const matchSupplier = supplierFilter === 'Todos' || i.supplier === supplierFilter
    const matchLowStock = !showLowStock || i.quantity <= i.minStock
    return matchSearch && matchCategory && matchSupplier && matchLowStock
  })

  const totalValue = items.reduce((sum, i) => sum + (i.quantity * i.costPrice), 0)

  return (
    <div className="min-h-screen bg-[#030308] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
            <Package className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Inventario</h1>
            <p className="text-gray-500">{items.length} items • Valor: ${totalValue.toLocaleString()}</p>
          </div>
        </div>
        <div className="flex gap-3">
          {items.length === 0 && (
            <button onClick={loadDefaults} className="flex items-center gap-2 bg-amber-500/20 text-amber-400 px-4 py-2 rounded-xl">
              <Download className="w-5 h-5" />Cargar Materiales
            </button>
          )}
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-2 rounded-xl font-semibold">
            <Plus className="w-5 h-5" />Agregar
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-[#0a0a12] rounded-xl p-4 border border-white/10">
          <p className="text-gray-500 text-sm">Total Items</p>
          <p className="text-2xl font-bold">{items.length}</p>
        </div>
        <div className="bg-[#0a0a12] rounded-xl p-4 border border-yellow-500/30">
          <p className="text-yellow-400 text-sm flex items-center gap-1"><AlertTriangle className="w-4 h-4" />Stock Bajo</p>
          <p className="text-2xl font-bold text-yellow-400">{lowStockItems.length}</p>
        </div>
        <div className="bg-[#0a0a12] rounded-xl p-4 border border-red-500/30">
          <p className="text-red-400 text-sm">Sin Stock</p>
          <p className="text-2xl font-bold text-red-400">{outOfStock.length}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
          <input type="text" placeholder="Buscar por nombre o SKU..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full bg-[#0a0a12] border border-white/10 rounded-xl pl-12 pr-4 py-3 outline-none" />
        </div>
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="bg-[#0a0a12] border border-white/10 rounded-xl px-4 py-3 outline-none">
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)} className="bg-[#0a0a12] border border-white/10 rounded-xl px-4 py-3 outline-none">
          {SUPPLIERS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button onClick={() => setShowLowStock(!showLowStock)} className={`px-4 py-3 rounded-xl flex items-center gap-2 ${showLowStock ? 'bg-yellow-500 text-black' : 'bg-white/10'}`}>
          <AlertTriangle className="w-4 h-4" />Solo bajo stock
        </button>
      </div>

      {/* Empty State */}
      {items.length === 0 && (
        <div className="text-center py-16">
          <Package className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold mb-2">Sin inventario</h2>
          <p className="text-gray-500 mb-6">Carga los materiales predeterminados o agrega manualmente</p>
          <button onClick={loadDefaults} className="bg-gradient-to-r from-green-500 to-emerald-600 px-6 py-3 rounded-xl font-semibold">
            Cargar Materiales Base
          </button>
        </div>
      )}

      {/* Items Grid */}
      {filtered.length > 0 && (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map(item => (
            <div key={item.id} className={`bg-[#0a0a12] rounded-xl border p-4 ${
              item.quantity === 0 ? 'border-red-500/50' : 
              item.quantity <= item.minStock ? 'border-yellow-500/50' : 'border-white/10'
            }`}>
              <div className="flex justify-between mb-2">
                <div>
                  <p className="text-xs text-gray-500">{item.sku}</p>
                  <h3 className="font-semibold">{item.name}</h3>
                </div>
                <button onClick={() => deleteItem(item.id)} className="text-gray-500 hover:text-red-400">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs bg-white/10 px-2 py-0.5 rounded">{item.category}</span>
                <span className="text-xs text-gray-500">{item.supplier}</span>
                <span className="text-xs text-gray-600">{item.location}</span>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-2xl font-bold ${item.quantity === 0 ? 'text-red-400' : item.quantity <= item.minStock ? 'text-yellow-400' : ''}`}>
                    {item.quantity}
                  </p>
                  <p className="text-xs text-gray-500">{item.unit} (min: {item.minStock})</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => updateQty(item.id, -1)} className="w-10 h-10 bg-red-500/20 text-red-400 rounded-lg flex items-center justify-center hover:bg-red-500/30">
                    <TrendingDown className="w-5 h-5" />
                  </button>
                  <button onClick={() => updateQty(item.id, 1)} className="w-10 h-10 bg-green-500/20 text-green-400 rounded-lg flex items-center justify-center hover:bg-green-500/30">
                    <TrendingUp className="w-5 h-5" />
                  </button>
                </div>
              </div>
              <div className="flex justify-between mt-2 pt-2 border-t border-white/5 text-xs text-gray-500">
                <span>Costo: ${item.costPrice}</span>
                <span>Venta: ${item.sellPrice}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowModal(false)} />
          <div className="relative bg-[#0a0a12] border border-white/10 rounded-2xl w-full max-w-lg p-6">
            <div className="flex justify-between mb-4">
              <h2 className="text-xl font-bold">Agregar Item</h2>
              <button onClick={() => setShowModal(false)}><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <input type="text" placeholder="SKU" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
                <input type="text" placeholder="Ubicación" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              </div>
              <input type="text" placeholder="Nombre del material *" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
              <div className="grid grid-cols-2 gap-4">
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none">
                  {CATEGORIES.filter(c => c !== 'Todos').map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select value={form.supplier} onChange={(e) => setForm({ ...form, supplier: e.target.value })} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none">
                  {SUPPLIERS.filter(s => s !== 'Todos').map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-xs text-gray-500">Cantidad</label>
                  <input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Min Stock</label>
                  <input type="number" value={form.minStock} onChange={(e) => setForm({ ...form, minStock: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Unidad</label>
                  <input type="text" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-500">Precio Costo</label>
                  <input type="number" value={form.costPrice} onChange={(e) => setForm({ ...form, costPrice: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
                </div>
                <div>
                  <label className="text-xs text-gray-500">Precio Venta</label>
                  <input type="number" value={form.sellPrice} onChange={(e) => setForm({ ...form, sellPrice: +e.target.value })} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowModal(false)} className="flex-1 bg-white/10 py-3 rounded-xl">Cancelar</button>
              <button onClick={addItem} className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 py-3 rounded-xl font-semibold">Agregar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
