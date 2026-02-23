'use client'
import { useState } from 'react'
import {
  Package, Plus, Search, Filter, AlertTriangle, CheckCircle, Clock,
  TrendingUp, TrendingDown, BarChart3, ShoppingCart, Truck, Box,
  Edit, Trash2, X, ChevronRight, RefreshCw, Download, Upload,
  DollarSign, Layers, Tag, Building2, ArrowUpRight, ArrowDownRight
} from 'lucide-react'

// Inventory categories
const CATEGORIES = [
  { id: 'fabric', name: 'Fabrics', icon: Layers, color: 'from-purple-500 to-pink-600' },
  { id: 'lining', name: 'Linings', icon: Layers, color: 'from-blue-500 to-cyan-600' },
  { id: 'hardware', name: 'Hardware', icon: Box, color: 'from-amber-500 to-orange-600' },
  { id: 'motors', name: 'Motors', icon: Box, color: 'from-green-500 to-emerald-600' },
  { id: 'trim', name: 'Trim & Tape', icon: Tag, color: 'from-red-500 to-rose-600' },
  { id: 'supplies', name: 'Supplies', icon: Package, color: 'from-gray-500 to-slate-600' },
]

// Sample inventory items
const INVENTORY_ITEMS = [
  { id: 'inv-001', sku: 'FAB-BLK-001', name: 'Blackout Lining', category: 'lining', quantity: 15, unit: 'yards', minStock: 50, maxStock: 200, cost: 8.50, price: 15.00, vendor: 'Rowley Company', location: 'A1-01', lastOrdered: '2026-02-10', status: 'low' },
  { id: 'inv-002', sku: 'FAB-STD-001', name: 'Standard Lining', category: 'lining', quantity: 85, unit: 'yards', minStock: 30, maxStock: 150, cost: 4.50, price: 9.00, vendor: 'Rowley Company', location: 'A1-02', lastOrdered: '2026-02-15', status: 'good' },
  { id: 'inv-003', sku: 'FAB-THM-001', name: 'Thermal Lining', category: 'lining', quantity: 42, unit: 'yards', minStock: 25, maxStock: 100, cost: 12.00, price: 22.00, vendor: 'Rowley Company', location: 'A1-03', lastOrdered: '2026-02-01', status: 'good' },
  { id: 'inv-004', sku: 'FAB-INT-001', name: 'Interlining', category: 'lining', quantity: 28, unit: 'yards', minStock: 20, maxStock: 80, cost: 6.00, price: 12.00, vendor: 'Rowley Company', location: 'A1-04', lastOrdered: '2026-01-20', status: 'good' },
  { id: 'inv-005', sku: 'HW-RPL-001', name: 'Ripplefold Tape', category: 'trim', quantity: 20, unit: 'meters', minStock: 50, maxStock: 200, cost: 3.25, price: 6.50, vendor: 'Rowley Company', location: 'B2-01', lastOrdered: '2026-02-05', status: 'low' },
  { id: 'inv-006', sku: 'HW-ROD-001', name: 'Drapery Rod 1"', category: 'hardware', quantity: 25, unit: 'pieces', minStock: 15, maxStock: 60, cost: 45.00, price: 85.00, vendor: 'Kirsch', location: 'C1-01', lastOrdered: '2026-02-12', status: 'good' },
  { id: 'inv-007', sku: 'HW-ROD-002', name: 'Drapery Rod 1.5"', category: 'hardware', quantity: 18, unit: 'pieces', minStock: 10, maxStock: 40, cost: 65.00, price: 120.00, vendor: 'Kirsch', location: 'C1-02', lastOrdered: '2026-02-12', status: 'good' },
  { id: 'inv-008', sku: 'HW-BKT-001', name: 'Wall Brackets', category: 'hardware', quantity: 150, unit: 'pieces', minStock: 50, maxStock: 300, cost: 4.00, price: 8.50, vendor: 'Kirsch', location: 'C2-01', lastOrdered: '2026-02-08', status: 'good' },
  { id: 'inv-009', sku: 'MOT-SMF-001', name: 'Somfy Motor RTS', category: 'motors', quantity: 8, unit: 'pieces', minStock: 5, maxStock: 20, cost: 285.00, price: 450.00, vendor: 'Somfy', location: 'D1-01', lastOrdered: '2026-02-18', status: 'good' },
  { id: 'inv-010', sku: 'MOT-LUT-001', name: 'Lutron Motor', category: 'motors', quantity: 3, unit: 'pieces', minStock: 3, maxStock: 15, cost: 425.00, price: 650.00, vendor: 'Lutron', location: 'D1-02', lastOrdered: '2026-01-25', status: 'low' },
  { id: 'inv-011', sku: 'HW-HKS-001', name: 'Drapery Hooks', category: 'hardware', quantity: 500, unit: 'pieces', minStock: 200, maxStock: 1000, cost: 0.15, price: 0.35, vendor: 'Rowley Company', location: 'C3-01', lastOrdered: '2026-02-20', status: 'good' },
  { id: 'inv-012', sku: 'SUP-THD-001', name: 'Thread - White', category: 'supplies', quantity: 12, unit: 'spools', minStock: 10, maxStock: 50, cost: 4.50, price: 8.00, vendor: 'Rowley Company', location: 'E1-01', lastOrdered: '2026-02-15', status: 'good' },
]

const VENDORS = [
  { id: 'v1', name: 'Rowley Company', contact: 'orders@rowley.com', phone: '800-343-4542', lastOrder: '2026-02-20', totalOrders: 45, totalSpent: 28500 },
  { id: 'v2', name: 'Somfy', contact: 'sales@somfy.com', phone: '800-227-6639', lastOrder: '2026-02-18', totalOrders: 12, totalSpent: 15200 },
  { id: 'v3', name: 'Lutron', contact: 'orders@lutron.com', phone: '888-588-7661', lastOrder: '2026-01-25', totalOrders: 8, totalSpent: 12800 },
  { id: 'v4', name: 'Kirsch', contact: 'support@kirsch.com', phone: '800-538-6567', lastOrder: '2026-02-12', totalOrders: 18, totalSpent: 8400 },
]

const PURCHASE_ORDERS = [
  { id: 'PO-2024', vendor: 'Rowley Company', date: '2026-02-20', status: 'pending', items: 3, total: 1250, eta: '2026-02-27' },
  { id: 'PO-2023', vendor: 'Somfy', date: '2026-02-18', status: 'shipped', items: 2, total: 2850, eta: '2026-02-25' },
  { id: 'PO-2022', vendor: 'Rowley Company', date: '2026-02-15', status: 'delivered', items: 5, total: 890, eta: null },
]

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<'inventory' | 'orders' | 'vendors'>('inventory')
  const [items, setItems] = useState(INVENTORY_ITEMS)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedItem, setSelectedItem] = useState<typeof INVENTORY_ITEMS[0] | null>(null)
  const [showAddItem, setShowAddItem] = useState(false)
  const [showNewOrder, setShowNewOrder] = useState(false)

  const filteredItems = items.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          item.sku.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || item.category === selectedCategory
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter
    return matchesSearch && matchesCategory && matchesStatus
  })

  const lowStockItems = items.filter(i => i.status === 'low')
  const totalValue = items.reduce((sum, i) => sum + (i.quantity * i.cost), 0)
  const totalRetailValue = items.reduce((sum, i) => sum + (i.quantity * i.price), 0)

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      good: 'bg-green-500/20 text-green-400',
      low: 'bg-red-500/20 text-red-400',
      overstock: 'bg-yellow-500/20 text-yellow-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  const getOrderStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400',
      shipped: 'bg-blue-500/20 text-blue-400',
      delivered: 'bg-green-500/20 text-green-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  const getStockLevel = (item: typeof INVENTORY_ITEMS[0]) => {
    return Math.round((item.quantity / item.maxStock) * 100)
  }

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      {/* Header */}
      <header className="bg-[#1A1A1A] border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
              <Package className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Empire Inventory</h1>
              <p className="text-sm text-gray-500">Stock Management & Orders</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => setShowNewOrder(true)} className="flex items-center gap-2 bg-[#2C2C2C] hover:bg-[#3C3C3C] px-4 py-2 rounded-xl transition">
              <ShoppingCart className="w-4 h-4" /> New Order
            </button>
            <button onClick={() => setShowAddItem(true)} className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-xl font-semibold transition">
              <Plus className="w-4 h-4" /> Add Item
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-[#1A1A1A] border-b border-gray-800">
        <div className="max-w-7xl mx-auto flex">
          {(['inventory', 'orders', 'vendors'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-6 py-3 text-sm font-medium transition ${activeTab === tab ? 'text-[#C9A84C] border-b-2 border-[#C9A84C]' : 'text-gray-400 hover:text-white'}`}>
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <main className="max-w-7xl mx-auto p-6">
        {activeTab === 'inventory' && (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <Package className="w-5 h-5 text-blue-400" />
                </div>
                <p className="text-2xl font-bold">{items.length}</p>
                <p className="text-sm text-gray-500">Total Items</p>
              </div>
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  {lowStockItems.length > 0 && <span className="text-xs text-red-400">Action needed</span>}
                </div>
                <p className="text-2xl font-bold text-red-400">{lowStockItems.length}</p>
                <p className="text-sm text-gray-500">Low Stock Items</p>
              </div>
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <DollarSign className="w-5 h-5 text-green-400" />
                </div>
                <p className="text-2xl font-bold">${totalValue.toLocaleString()}</p>
                <p className="text-sm text-gray-500">Inventory Cost</p>
              </div>
              <div className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <TrendingUp className="w-5 h-5 text-[#C9A84C]" />
                </div>
                <p className="text-2xl font-bold">${totalRetailValue.toLocaleString()}</p>
                <p className="text-sm text-gray-500">Retail Value</p>
              </div>
            </div>

            {/* Low Stock Alert */}
            {lowStockItems.length > 0 && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center gap-3 mb-3">
                  <AlertTriangle className="w-5 h-5 text-red-400" />
                  <h3 className="font-semibold text-red-400">Low Stock Alert</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {lowStockItems.map(item => (
                    <button key={item.id} onClick={() => setSelectedItem(item)}
                      className="bg-red-500/20 hover:bg-red-500/30 text-red-400 px-3 py-1.5 rounded-lg text-sm transition">
                      {item.name} ({item.quantity} {item.unit})
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Categories */}
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => setSelectedCategory('all')}
                className={`px-4 py-2 rounded-lg text-sm transition ${selectedCategory === 'all' ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'bg-[#2C2C2C] hover:bg-[#3C3C3C]'}`}>
                All Items
              </button>
              {CATEGORIES.map(cat => (
                <button key={cat.id} onClick={() => setSelectedCategory(cat.id)}
                  className={`px-4 py-2 rounded-lg text-sm transition flex items-center gap-2 ${selectedCategory === cat.id ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'bg-[#2C2C2C] hover:bg-[#3C3C3C]'}`}>
                  <cat.icon className="w-4 h-4" /> {cat.name}
                </button>
              ))}
            </div>

            {/* Search & Filter */}
            <div className="flex gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input type="text" placeholder="Search by name or SKU..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 focus:border-[#C9A84C] outline-none" />
              </div>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                <option value="all">All Status</option>
                <option value="good">Good Stock</option>
                <option value="low">Low Stock</option>
              </select>
            </div>

            {/* Inventory Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredItems.map(item => (
                <div key={item.id} onClick={() => setSelectedItem(item)}
                  className={`bg-[#1A1A1A] rounded-xl p-4 border cursor-pointer transition hover:border-gray-600 ${item.status === 'low' ? 'border-red-500/50' : 'border-gray-800'}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-mono text-xs text-gray-500">{item.sku}</p>
                      <h3 className="font-semibold mt-1">{item.name}</h3>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(item.status)}`}>{item.status}</span>
                  </div>
                  <div className="flex items-end justify-between mb-3">
                    <div>
                      <p className="text-2xl font-bold">{item.quantity}</p>
                      <p className="text-xs text-gray-500">{item.unit}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-[#C9A84C]">${item.price.toFixed(2)}</p>
                      <p className="text-xs text-gray-500">Cost: ${item.cost.toFixed(2)}</p>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Stock Level</span>
                      <span>{getStockLevel(item)}%</span>
                    </div>
                    <div className="h-2 bg-[#2C2C2C] rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${item.status === 'low' ? 'bg-red-500' : 'bg-green-500'}`}
                        style={{ width: `${Math.min(getStockLevel(item), 100)}%` }} />
                    </div>
                    <div className="flex justify-between text-xs text-gray-600">
                      <span>Min: {item.minStock}</span>
                      <span>Max: {item.maxStock}</span>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500">
                    <span>{item.vendor}</span>
                    <span>{item.location}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'orders' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Purchase Orders</h2>
              <button onClick={() => setShowNewOrder(true)} className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-xl font-semibold">
                <Plus className="w-4 h-4" /> New Order
              </button>
            </div>

            <div className="bg-[#1A1A1A] rounded-xl border border-gray-800 overflow-hidden">
              <table className="w-full">
                <thead className="bg-[#2C2C2C]">
                  <tr>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">PO Number</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Vendor</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Date</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Items</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Total</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">Status</th>
                    <th className="px-5 py-3 text-left text-xs text-gray-400 font-medium">ETA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {PURCHASE_ORDERS.map(order => (
                    <tr key={order.id} className="hover:bg-[#2C2C2C]/50">
                      <td className="px-5 py-4 font-mono text-sm">{order.id}</td>
                      <td className="px-5 py-4 font-medium">{order.vendor}</td>
                      <td className="px-5 py-4 text-sm text-gray-400">{order.date}</td>
                      <td className="px-5 py-4">{order.items}</td>
                      <td className="px-5 py-4 font-semibold">${order.total.toLocaleString()}</td>
                      <td className="px-5 py-4">
                        <span className={`text-xs px-2 py-1 rounded ${getOrderStatusColor(order.status)}`}>{order.status}</span>
                      </td>
                      <td className="px-5 py-4 text-sm text-gray-400">{order.eta || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'vendors' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Vendors</h2>
              <button className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-xl font-semibold">
                <Plus className="w-4 h-4" /> Add Vendor
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {VENDORS.map(vendor => (
                <div key={vendor.id} className="bg-[#1A1A1A] rounded-xl p-5 border border-gray-800 hover:border-gray-700 transition">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-xl bg-[#2C2C2C] flex items-center justify-center">
                        <Building2 className="w-6 h-6 text-[#C9A84C]" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{vendor.name}</h3>
                        <p className="text-sm text-gray-500">{vendor.contact}</p>
                      </div>
                    </div>
                    <button className="p-2 hover:bg-[#2C2C2C] rounded-lg"><Edit className="w-4 h-4" /></button>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center mb-4">
                    <div className="bg-[#2C2C2C] rounded-lg p-3">
                      <p className="text-lg font-bold text-blue-400">{vendor.totalOrders}</p>
                      <p className="text-xs text-gray-500">Orders</p>
                    </div>
                    <div className="bg-[#2C2C2C] rounded-lg p-3">
                      <p className="text-lg font-bold text-green-400">${(vendor.totalSpent/1000).toFixed(1)}k</p>
                      <p className="text-xs text-gray-500">Total Spent</p>
                    </div>
                    <div className="bg-[#2C2C2C] rounded-lg p-3">
                      <p className="text-sm font-bold">{vendor.lastOrder}</p>
                      <p className="text-xs text-gray-500">Last Order</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-2 rounded-lg text-sm flex items-center justify-center gap-2">
                      <ShoppingCart className="w-4 h-4" /> Order
                    </button>
                    <button className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-2 rounded-lg text-sm">{vendor.phone}</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Item Detail Modal */}
      {selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setSelectedItem(null)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <div>
                <p className="font-mono text-xs text-gray-500">{selectedItem.sku}</p>
                <h2 className="font-bold text-lg">{selectedItem.name}</h2>
              </div>
              <button onClick={() => setSelectedItem(null)} className="p-1 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <span className={`text-sm px-3 py-1 rounded ${getStatusColor(selectedItem.status)}`}>{selectedItem.status} stock</span>
                <span className="text-sm text-gray-500">{selectedItem.vendor}</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#2C2C2C] rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold">{selectedItem.quantity}</p>
                  <p className="text-sm text-gray-500">{selectedItem.unit} in stock</p>
                </div>
                <div className="bg-[#2C2C2C] rounded-xl p-4 text-center">
                  <p className="text-3xl font-bold text-[#C9A84C]">${selectedItem.price}</p>
                  <p className="text-sm text-gray-500">Retail Price</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm"><span className="text-gray-500">Cost</span><span>${selectedItem.cost.toFixed(2)} per {selectedItem.unit.slice(0,-1)}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-500">Min Stock</span><span>{selectedItem.minStock} {selectedItem.unit}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-500">Max Stock</span><span>{selectedItem.maxStock} {selectedItem.unit}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-500">Location</span><span>{selectedItem.location}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-500">Last Ordered</span><span>{selectedItem.lastOrdered}</span></div>
              </div>
              <div className="pt-4 border-t border-gray-800">
                <div className="flex justify-between text-sm mb-2"><span className="text-gray-500">Stock Level</span><span>{getStockLevel(selectedItem)}%</span></div>
                <div className="h-3 bg-[#2C2C2C] rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${selectedItem.status === 'low' ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${Math.min(getStockLevel(selectedItem), 100)}%` }} />
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-800 flex gap-3">
              <button className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-3 rounded-xl flex items-center justify-center gap-2">
                <Edit className="w-4 h-4" /> Edit
              </button>
              <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-3 rounded-xl flex items-center justify-center gap-2">
                <ShoppingCart className="w-4 h-4" /> Reorder
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Item Modal */}
      {showAddItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setShowAddItem(false)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-lg overflow-hidden max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between sticky top-0 bg-[#1A1A1A]">
              <h2 className="font-bold text-lg">Add Inventory Item</h2>
              <button onClick={() => setShowAddItem(false)} className="p-1 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-sm text-gray-400 mb-1">SKU *</label><input type="text" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="FAB-XXX-001" /></div>
                <div><label className="block text-sm text-gray-400 mb-1">Category</label>
                  <select className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                    {CATEGORIES.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
              </div>
              <div><label className="block text-sm text-gray-400 mb-1">Item Name *</label><input type="text" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="Item name" /></div>
              <div className="grid grid-cols-3 gap-4">
                <div><label className="block text-sm text-gray-400 mb-1">Quantity</label><input type="number" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="0" /></div>
                <div><label className="block text-sm text-gray-400 mb-1">Unit</label>
                  <select className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                    <option>yards</option><option>meters</option><option>pieces</option><option>spools</option><option>boxes</option>
                  </select>
                </div>
                <div><label className="block text-sm text-gray-400 mb-1">Location</label><input type="text" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="A1-01" /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-sm text-gray-400 mb-1">Cost Price</label>
                  <div className="relative"><DollarSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" /><input type="number" step="0.01" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="0.00" /></div>
                </div>
                <div><label className="block text-sm text-gray-400 mb-1">Retail Price</label>
                  <div className="relative"><DollarSign className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" /><input type="number" step="0.01" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="0.00" /></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-sm text-gray-400 mb-1">Min Stock</label><input type="number" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="10" /></div>
                <div><label className="block text-sm text-gray-400 mb-1">Max Stock</label><input type="number" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="100" /></div>
              </div>
              <div><label className="block text-sm text-gray-400 mb-1">Vendor</label>
                <select className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                  {VENDORS.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-800 flex gap-3 sticky bottom-0 bg-[#1A1A1A]">
              <button onClick={() => setShowAddItem(false)} className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-3 rounded-xl">Cancel</button>
              <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-3 rounded-xl flex items-center justify-center gap-2">
                <CheckCircle className="w-4 h-4" /> Add Item
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New Order Modal */}
      {showNewOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setShowNewOrder(false)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="font-bold text-lg">Create Purchase Order</h2>
              <button onClick={() => setShowNewOrder(false)} className="p-1 hover:bg-[#2C2C2C] rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div><label className="block text-sm text-gray-400 mb-1">Vendor *</label>
                <select className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                  <option>Select vendor...</option>
                  {VENDORS.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                </select>
              </div>
              <div className="bg-[#2C2C2C] rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium">Quick Add Low Stock Items</span>
                </div>
                <div className="space-y-2">
                  {lowStockItems.map(item => (
                    <label key={item.id} className="flex items-center gap-3 p-2 bg-[#1A1A1A] rounded-lg cursor-pointer hover:bg-[#3C3C3C]">
                      <input type="checkbox" className="rounded" />
                      <span className="flex-1">{item.name}</span>
                      <span className="text-sm text-red-400">{item.quantity}/{item.minStock}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div><label className="block text-sm text-gray-400 mb-1">Notes</label><textarea className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none h-20 resize-none" placeholder="Order notes..." /></div>
            </div>
            <div className="px-6 py-4 border-t border-gray-800 flex gap-3">
              <button onClick={() => setShowNewOrder(false)} className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-3 rounded-xl">Cancel</button>
              <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-3 rounded-xl flex items-center justify-center gap-2">
                <ShoppingCart className="w-4 h-4" /> Create Order
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
