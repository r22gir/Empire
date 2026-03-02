'use client'
import { useState } from 'react'
import {
  Users, UserPlus, Search, Filter, MoreVertical, Phone, Mail, MapPin,
  Calendar, DollarSign, FileText, MessageSquare, Star, StarOff,
  ChevronRight, Clock, TrendingUp, Building2, Home, Tag, Edit,
  Trash2, X, Plus, Send, Check, AlertCircle
} from 'lucide-react'

// Sample customer data
const CUSTOMERS = [
  {
    id: 'cust-1',
    name: 'Azul Designs',
    contact: 'Maria Rodriguez',
    email: 'maria@azuldesigns.com',
    phone: '(555) 123-4567',
    type: 'commercial',
    status: 'active',
    starred: true,
    address: '123 Design District, Miami, FL 33101',
    totalSpent: 28500,
    totalOrders: 12,
    lastOrder: '2026-02-20',
    nextFollowUp: '2026-02-24',
    tags: ['VIP', 'Designer', 'Repeat'],
    notes: 'Prefers ripplefold drapes, high-end fabrics. Quick decision maker.',
    orders: [
      { id: 'ord-1', date: '2026-02-20', amount: 4500, status: 'in_progress', items: 'Ripplefold Drapes x4' },
      { id: 'ord-2', date: '2026-01-15', amount: 6200, status: 'completed', items: 'Roman Shades x6' },
      { id: 'ord-3', date: '2025-12-01', amount: 3800, status: 'completed', items: 'Motorized Blinds x2' },
    ],
    communications: [
      { id: 'com-1', date: '2026-02-22', type: 'email', subject: 'Quote Follow-up', preview: 'Thanks for the quote, we\'d like to proceed...' },
      { id: 'com-2', date: '2026-02-18', type: 'call', subject: 'Initial Consultation', preview: '15 min call discussing new project requirements' },
    ]
  },
  {
    id: 'cust-2',
    name: 'Johnson Design Co.',
    contact: 'Robert Johnson',
    email: 'robert@johnsondesign.com',
    phone: '(555) 234-5678',
    type: 'commercial',
    status: 'active',
    starred: true,
    address: '456 Business Park, Atlanta, GA 30301',
    totalSpent: 45200,
    totalOrders: 18,
    lastOrder: '2026-02-18',
    nextFollowUp: '2026-02-25',
    tags: ['VIP', 'Commercial', 'Bulk Orders'],
    notes: 'Large commercial projects. Net-30 terms approved.',
    orders: [
      { id: 'ord-4', date: '2026-02-18', amount: 8500, status: 'in_progress', items: 'Office Blinds x20' },
    ],
    communications: []
  },
  {
    id: 'cust-3',
    name: 'Smith Residence',
    contact: 'Jennifer Smith',
    email: 'jen.smith@email.com',
    phone: '(555) 345-6789',
    type: 'residential',
    status: 'active',
    starred: false,
    address: '789 Oak Street, Nashville, TN 37201',
    totalSpent: 6800,
    totalOrders: 2,
    lastOrder: '2026-02-10',
    nextFollowUp: '2026-02-23',
    tags: ['Residential', 'New Customer'],
    notes: 'First-time customer. Very detail-oriented.',
    orders: [
      { id: 'ord-5', date: '2026-02-10', amount: 3200, status: 'completed', items: 'Living Room Drapes' },
    ],
    communications: []
  },
  {
    id: 'cust-4',
    name: 'Luxury Interiors LLC',
    contact: 'Amanda Chen',
    email: 'amanda@luxuryint.com',
    phone: '(555) 456-7890',
    type: 'commercial',
    status: 'lead',
    starred: false,
    address: '321 Luxury Lane, Beverly Hills, CA 90210',
    totalSpent: 0,
    totalOrders: 0,
    lastOrder: null,
    nextFollowUp: '2026-02-24',
    tags: ['Lead', 'High Potential'],
    notes: 'Met at trade show. Interested in partnership for luxury homes.',
    orders: [],
    communications: [
      { id: 'com-3', date: '2026-02-21', type: 'email', subject: 'Introduction', preview: 'Nice meeting you at the show...' },
    ]
  },
  {
    id: 'cust-5',
    name: 'The Shade Store Partner',
    contact: 'Michael Brown',
    email: 'mbrown@shadestorepartner.com',
    phone: '(555) 567-8901',
    type: 'commercial',
    status: 'inactive',
    starred: false,
    address: '555 Trade Center, Dallas, TX 75201',
    totalSpent: 12400,
    totalOrders: 5,
    lastOrder: '2025-10-15',
    nextFollowUp: null,
    tags: ['Inactive', 'Win Back'],
    notes: 'Hasn\'t ordered in 4 months. Reach out for reactivation.',
    orders: [],
    communications: []
  },
]

const STATS = [
  { label: 'Total Customers', value: '127', icon: Users, color: 'text-blue-400', change: '+12 this month' },
  { label: 'Active Leads', value: '23', icon: UserPlus, color: 'text-green-400', change: '+5 this week' },
  { label: 'Follow-ups Today', value: '4', icon: Calendar, color: 'text-yellow-400', change: '2 overdue' },
  { label: 'Lifetime Value', value: '$842k', icon: TrendingUp, color: 'text-purple-400', change: '+18% YoY' },
]

export default function CRMPage() {
  const [customers, setCustomers] = useState(CUSTOMERS)
  const [selectedCustomer, setSelectedCustomer] = useState<typeof CUSTOMERS[0] | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [showAddCustomer, setShowAddCustomer] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'orders' | 'communications'>('overview')

  const filteredCustomers = customers.filter(c => {
    const matchesSearch = c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          c.contact.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          c.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === 'all' || c.type === filterType
    const matchesStatus = filterStatus === 'all' || c.status === filterStatus
    return matchesSearch && matchesType && matchesStatus
  })

  const toggleStar = (id: string) => {
    setCustomers(customers.map(c => c.id === id ? { ...c, starred: !c.starred } : c))
    if (selectedCustomer?.id === id) {
      setSelectedCustomer({ ...selectedCustomer, starred: !selectedCustomer.starred })
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-500/20 text-green-400',
      lead: 'bg-blue-500/20 text-blue-400',
      inactive: 'bg-gray-500/20 text-gray-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  const getOrderStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      completed: 'bg-green-500/20 text-green-400',
      in_progress: 'bg-blue-500/20 text-blue-400',
      pending: 'bg-yellow-500/20 text-yellow-400',
    }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  return (
    <div className="min-h-screen bg-[#0D0D0D] text-white">
      {/* Header */}
      <header className="bg-[#1A1A1A] border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Users className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Empire CRM</h1>
              <p className="text-sm text-gray-500">Customer Relationship Management</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddCustomer(true)}
              className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-xl font-semibold transition"
            >
              <UserPlus className="w-4 h-4" />
              Add Customer
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {STATS.map((stat, i) => (
            <div key={i} className="bg-[#1A1A1A] rounded-xl p-4 border border-gray-800">
              <div className="flex items-center justify-between mb-2">
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <p className="text-2xl font-bold">{stat.value}</p>
              <p className="text-xs text-gray-500">{stat.label}</p>
              <p className="text-xs text-gray-600 mt-1">{stat.change}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Customer List */}
          <div className="lg:col-span-5">
            <div className="bg-[#1A1A1A] rounded-2xl border border-gray-800 overflow-hidden">
              {/* Search & Filters */}
              <div className="p-4 border-b border-gray-800">
                <div className="relative mb-3">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search customers..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:border-[#C9A84C] outline-none"
                  />
                </div>
                <div className="flex gap-2">
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="bg-[#2C2C2C] border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:border-[#C9A84C] outline-none"
                  >
                    <option value="all">All Types</option>
                    <option value="commercial">Commercial</option>
                    <option value="residential">Residential</option>
                  </select>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="bg-[#2C2C2C] border border-gray-700 rounded-lg px-3 py-1.5 text-sm focus:border-[#C9A84C] outline-none"
                  >
                    <option value="all">All Status</option>
                    <option value="active">Active</option>
                    <option value="lead">Lead</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              {/* Customer List */}
              <div className="max-h-[600px] overflow-y-auto">
                {filteredCustomers.map(customer => (
                  <button
                    key={customer.id}
                    onClick={() => setSelectedCustomer(customer)}
                    className={`w-full p-4 border-b border-gray-800 text-left hover:bg-[#2C2C2C] transition ${
                      selectedCustomer?.id === customer.id ? 'bg-[#2C2C2C]' : ''
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        customer.type === 'commercial' ? 'bg-blue-500/20' : 'bg-green-500/20'
                      }`}>
                        {customer.type === 'commercial' ? (
                          <Building2 className="w-5 h-5 text-blue-400" />
                        ) : (
                          <Home className="w-5 h-5 text-green-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold truncate">{customer.name}</h3>
                          <button onClick={(e) => { e.stopPropagation(); toggleStar(customer.id) }}>
                            {customer.starred ? (
                              <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                            ) : (
                              <StarOff className="w-4 h-4 text-gray-600 hover:text-yellow-400" />
                            )}
                          </button>
                        </div>
                        <p className="text-sm text-gray-400">{customer.contact}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(customer.status)}`}>
                            {customer.status}
                          </span>
                          <span className="text-xs text-gray-500">${customer.totalSpent.toLocaleString()}</span>
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-gray-600" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Customer Detail */}
          <div className="lg:col-span-7">
            {selectedCustomer ? (
              <div className="bg-[#1A1A1A] rounded-2xl border border-gray-800 overflow-hidden">
                {/* Customer Header */}
                <div className="p-6 border-b border-gray-800 bg-gradient-to-r from-indigo-500/10 to-violet-500/10">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-16 h-16 rounded-xl flex items-center justify-center ${
                        selectedCustomer.type === 'commercial' ? 'bg-blue-500/20' : 'bg-green-500/20'
                      }`}>
                        {selectedCustomer.type === 'commercial' ? (
                          <Building2 className="w-8 h-8 text-blue-400" />
                        ) : (
                          <Home className="w-8 h-8 text-green-400" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h2 className="text-xl font-bold">{selectedCustomer.name}</h2>
                          <button onClick={() => toggleStar(selectedCustomer.id)}>
                            {selectedCustomer.starred ? (
                              <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
                            ) : (
                              <StarOff className="w-5 h-5 text-gray-600 hover:text-yellow-400" />
                            )}
                          </button>
                        </div>
                        <p className="text-gray-400">{selectedCustomer.contact}</p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(selectedCustomer.status)}`}>
                            {selectedCustomer.status}
                          </span>
                          {selectedCustomer.tags.map(tag => (
                            <span key={tag} className="text-xs bg-[#2C2C2C] px-2 py-0.5 rounded">{tag}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button className="p-2 bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-lg"><Edit className="w-4 h-4" /></button>
                      <button className="p-2 bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-lg"><MoreVertical className="w-4 h-4" /></button>
                    </div>
                  </div>

                  {/* Quick Stats */}
                  <div className="grid grid-cols-3 gap-4 mt-4">
                    <div className="bg-black/20 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-green-400">${selectedCustomer.totalSpent.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">Total Spent</p>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-blue-400">{selectedCustomer.totalOrders}</p>
                      <p className="text-xs text-gray-500">Orders</p>
                    </div>
                    <div className="bg-black/20 rounded-lg p-3 text-center">
                      <p className="text-xl font-bold text-purple-400">{selectedCustomer.lastOrder || 'N/A'}</p>
                      <p className="text-xs text-gray-500">Last Order</p>
                    </div>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-800">
                  {(['overview', 'orders', 'communications'] as const).map(tab => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={`flex-1 py-3 text-sm font-medium transition ${
                        activeTab === tab ? 'text-[#C9A84C] border-b-2 border-[#C9A84C]' : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                  ))}
                </div>

                {/* Tab Content */}
                <div className="p-6 max-h-[400px] overflow-y-auto">
                  {activeTab === 'overview' && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-[#2C2C2C] rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2 text-gray-400">
                            <Mail className="w-4 h-4" />
                            <span className="text-sm">Email</span>
                          </div>
                          <p className="text-sm">{selectedCustomer.email}</p>
                        </div>
                        <div className="bg-[#2C2C2C] rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2 text-gray-400">
                            <Phone className="w-4 h-4" />
                            <span className="text-sm">Phone</span>
                          </div>
                          <p className="text-sm">{selectedCustomer.phone}</p>
                        </div>
                      </div>
                      <div className="bg-[#2C2C2C] rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2 text-gray-400">
                          <MapPin className="w-4 h-4" />
                          <span className="text-sm">Address</span>
                        </div>
                        <p className="text-sm">{selectedCustomer.address}</p>
                      </div>
                      {selectedCustomer.nextFollowUp && (
                        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-2 text-yellow-400">
                            <Calendar className="w-4 h-4" />
                            <span className="text-sm font-medium">Next Follow-up</span>
                          </div>
                          <p className="text-sm">{selectedCustomer.nextFollowUp}</p>
                        </div>
                      )}
                      <div className="bg-[#2C2C2C] rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2 text-gray-400">
                          <FileText className="w-4 h-4" />
                          <span className="text-sm">Notes</span>
                        </div>
                        <p className="text-sm text-gray-300">{selectedCustomer.notes}</p>
                      </div>

                      {/* Quick Actions */}
                      <div className="grid grid-cols-3 gap-2">
                        <button className="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 py-3 rounded-xl text-sm flex items-center justify-center gap-2">
                          <Phone className="w-4 h-4" /> Call
                        </button>
                        <button className="bg-green-500/20 hover:bg-green-500/30 text-green-400 py-3 rounded-xl text-sm flex items-center justify-center gap-2">
                          <Mail className="w-4 h-4" /> Email
                        </button>
                        <button className="bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 py-3 rounded-xl text-sm flex items-center justify-center gap-2">
                          <FileText className="w-4 h-4" /> Quote
                        </button>
                      </div>
                    </div>
                  )}

                  {activeTab === 'orders' && (
                    <div className="space-y-3">
                      {selectedCustomer.orders.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
                          <p>No orders yet</p>
                        </div>
                      ) : (
                        selectedCustomer.orders.map(order => (
                          <div key={order.id} className="bg-[#2C2C2C] rounded-xl p-4">
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <p className="font-semibold">{order.items}</p>
                                <p className="text-xs text-gray-500">{order.date}</p>
                              </div>
                              <span className={`text-xs px-2 py-0.5 rounded ${getOrderStatusColor(order.status)}`}>
                                {order.status.replace('_', ' ')}
                              </span>
                            </div>
                            <p className="text-lg font-bold text-green-400">${order.amount.toLocaleString()}</p>
                          </div>
                        ))
                      )}
                    </div>
                  )}

                  {activeTab === 'communications' && (
                    <div className="space-y-3">
                      {selectedCustomer.communications.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
                          <p>No communications logged</p>
                        </div>
                      ) : (
                        selectedCustomer.communications.map(comm => (
                          <div key={comm.id} className="bg-[#2C2C2C] rounded-xl p-4">
                            <div className="flex items-center gap-2 mb-2">
                              {comm.type === 'email' ? (
                                <Mail className="w-4 h-4 text-blue-400" />
                              ) : (
                                <Phone className="w-4 h-4 text-green-400" />
                              )}
                              <span className="font-semibold text-sm">{comm.subject}</span>
                              <span className="text-xs text-gray-500 ml-auto">{comm.date}</span>
                            </div>
                            <p className="text-sm text-gray-400">{comm.preview}</p>
                          </div>
                        ))
                      )}
                      <button className="w-full bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-xl p-3 text-sm flex items-center justify-center gap-2">
                        <Plus className="w-4 h-4" /> Log Communication
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-[#1A1A1A] rounded-2xl border border-gray-800 h-full flex items-center justify-center p-12">
                <div className="text-center text-gray-500">
                  <Users className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p className="text-lg">Select a customer to view details</p>
                  <p className="text-sm mt-1">Or add a new customer to get started</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Add Customer Modal */}
      {showAddCustomer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setShowAddCustomer(false)} />
          <div className="relative bg-[#1A1A1A] rounded-2xl border border-gray-800 w-full max-w-md overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
              <h2 className="font-bold text-lg">Add New Customer</h2>
              <button onClick={() => setShowAddCustomer(false)} className="p-1 hover:bg-[#2C2C2C] rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Company/Name *</label>
                <input type="text" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="Acme Corp" />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Contact Person *</label>
                <input type="text" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="John Doe" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Email *</label>
                  <input type="email" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="email@company.com" />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Phone</label>
                  <input type="tel" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="(555) 123-4567" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Type</label>
                <select className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none">
                  <option value="commercial">Commercial</option>
                  <option value="residential">Residential</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Address</label>
                <input type="text" className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none" placeholder="123 Main St, City, State ZIP" />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Notes</label>
                <textarea className="w-full bg-[#2C2C2C] border border-gray-700 rounded-lg px-4 py-2 focus:border-[#C9A84C] outline-none h-20 resize-none" placeholder="Any additional notes..." />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-800 flex gap-3">
              <button onClick={() => setShowAddCustomer(false)} className="flex-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] py-3 rounded-xl">
                Cancel
              </button>
              <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-3 rounded-xl flex items-center justify-center gap-2">
                <Check className="w-4 h-4" /> Add Customer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
