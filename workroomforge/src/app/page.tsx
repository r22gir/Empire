'use client'
import { useState, useRef, useCallback } from 'react'
import {
  Plus, Trash2, Copy, ChevronDown, ChevronUp, Camera, Upload, X,
  Ruler, Sparkles, Check, AlertTriangle, Loader2,
  Home, Maximize2, Calculator, FileText, Send, Brain,
  Eye, RotateCcw, Lightbulb, Package, Search, Filter,
  ShoppingCart, Truck, Box, Edit, RefreshCw, Download,
  DollarSign, Layers, Tag, Building2, Users, UserPlus,
  Phone, Mail, MapPin, Calendar, Clock, FileCheck,
  TrendingUp, TrendingDown, BarChart3, Receipt,
  CreditCard, PieChart, ArrowUpRight, ArrowDownRight,
  CheckCircle, XCircle, MoreHorizontal, ChevronRight,
  Briefcase, Star, Hash, Percent, Settings, Bell,
  Menu, Factory, Zap
} from 'lucide-react'

// ═══════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════

type AppSection = 'quotes' | 'inventory' | 'crm' | 'finance'
type InventoryTab = 'inventory' | 'orders' | 'vendors'
type CrmTab = 'customers' | 'jobs' | 'pipeline'
type FinanceTab = 'overview' | 'invoices' | 'expenses'

interface WindowItem {
  id: string; name: string; width: number; height: number; quantity: number
  treatmentType: string; mountType: string; liningType: string
  hardwareType: string; motorization: string; notes: string
  imageUrl?: string
  aiAnalysis?: { confidence: number; suggestedWidth: number; suggestedHeight: number; windowType: string; recommendations: string[] }
}

interface Room {
  id: string; name: string; windows: WindowItem[]; expanded: boolean
}

interface InventoryItem {
  id: string; sku: string; name: string; category: string; quantity: number; unit: string
  minStock: number; maxStock: number; cost: number; price: number
  vendor: string; location: string; lastOrdered: string; status: string
}

interface Customer {
  id: string; name: string; email: string; phone: string; address: string
  totalJobs: number; totalRevenue: number; lastJob: string; status: string; rating: number
}

interface Job {
  id: string; customerId: string; customerName: string; title: string
  status: 'lead' | 'quoted' | 'approved' | 'in-progress' | 'completed' | 'invoiced'
  total: number; rooms: number; windows: number; createdAt: string; dueDate: string
}

interface Invoice {
  id: string; jobId: string; customerName: string; amount: number
  status: 'draft' | 'sent' | 'paid' | 'overdue'; date: string; dueDate: string
}

// ═══════════════════════════════════════════════════════
// PRICING
// ═══════════════════════════════════════════════════════

const PRICING = {
  base: { 'ripplefold': 45, 'pinch-pleat': 38, 'rod-pocket': 28, 'grommet': 32, 'roman-shade': 55, 'roller-shade': 42 } as Record<string, number>,
  lining: { 'unlined': 0, 'standard': 8, 'blackout': 15, 'thermal': 12, 'interlining': 18 } as Record<string, number>,
  hardware: { 'none': 0, 'rod-standard': 45, 'rod-decorative': 85, 'track-basic': 65, 'track-ripplefold': 95 } as Record<string, number>,
  motor: { 'none': 0, 'somfy': 285, 'lutron': 425, 'generic': 185 } as Record<string, number>,
}

// ═══════════════════════════════════════════════════════
// SAMPLE DATA
// ═══════════════════════════════════════════════════════

const CATEGORIES = [
  { id: 'fabric', name: 'Fabrics', icon: Layers, color: 'from-purple-500 to-pink-600' },
  { id: 'lining', name: 'Linings', icon: Layers, color: 'from-blue-500 to-cyan-600' },
  { id: 'hardware', name: 'Hardware', icon: Box, color: 'from-amber-500 to-orange-600' },
  { id: 'motors', name: 'Motors', icon: Zap, color: 'from-green-500 to-emerald-600' },
  { id: 'trim', name: 'Trim & Tape', icon: Tag, color: 'from-red-500 to-rose-600' },
  { id: 'supplies', name: 'Supplies', icon: Package, color: 'from-gray-500 to-slate-600' },
]

const INITIAL_INVENTORY: InventoryItem[] = [
  { id: 'inv-001', sku: 'FAB-BLK-001', name: 'Blackout Lining', category: 'lining', quantity: 15, unit: 'yards', minStock: 50, maxStock: 200, cost: 8.50, price: 15.00, vendor: 'Rowley Company', location: 'A1-01', lastOrdered: '2026-02-10', status: 'low' },
  { id: 'inv-002', sku: 'FAB-STD-001', name: 'Standard Lining', category: 'lining', quantity: 85, unit: 'yards', minStock: 30, maxStock: 150, cost: 4.50, price: 9.00, vendor: 'Rowley Company', location: 'A1-02', lastOrdered: '2026-02-15', status: 'good' },
  { id: 'inv-003', sku: 'FAB-THM-001', name: 'Thermal Lining', category: 'lining', quantity: 42, unit: 'yards', minStock: 25, maxStock: 100, cost: 12.00, price: 22.00, vendor: 'Rowley Company', location: 'A1-03', lastOrdered: '2026-02-01', status: 'good' },
  { id: 'inv-004', sku: 'HW-RPL-001', name: 'Ripplefold Tape', category: 'trim', quantity: 20, unit: 'meters', minStock: 50, maxStock: 200, cost: 3.25, price: 6.50, vendor: 'Rowley Company', location: 'B2-01', lastOrdered: '2026-02-05', status: 'low' },
  { id: 'inv-005', sku: 'HW-ROD-001', name: 'Drapery Rod 1"', category: 'hardware', quantity: 25, unit: 'pieces', minStock: 15, maxStock: 60, cost: 45.00, price: 85.00, vendor: 'Kirsch', location: 'C1-01', lastOrdered: '2026-02-12', status: 'good' },
  { id: 'inv-006', sku: 'MOT-SMF-001', name: 'Somfy Motor RTS', category: 'motors', quantity: 8, unit: 'pieces', minStock: 5, maxStock: 20, cost: 285.00, price: 450.00, vendor: 'Somfy', location: 'D1-01', lastOrdered: '2026-02-18', status: 'good' },
  { id: 'inv-007', sku: 'MOT-LUT-001', name: 'Lutron Motor', category: 'motors', quantity: 3, unit: 'pieces', minStock: 3, maxStock: 15, cost: 425.00, price: 650.00, vendor: 'Lutron', location: 'D1-02', lastOrdered: '2026-01-25', status: 'low' },
  { id: 'inv-008', sku: 'HW-HKS-001', name: 'Drapery Hooks', category: 'hardware', quantity: 500, unit: 'pieces', minStock: 200, maxStock: 1000, cost: 0.15, price: 0.35, vendor: 'Rowley Company', location: 'C3-01', lastOrdered: '2026-02-20', status: 'good' },
  { id: 'inv-009', sku: 'HW-BKT-001', name: 'Wall Brackets', category: 'hardware', quantity: 150, unit: 'pieces', minStock: 50, maxStock: 300, cost: 4.00, price: 8.50, vendor: 'Kirsch', location: 'C2-01', lastOrdered: '2026-02-08', status: 'good' },
  { id: 'inv-010', sku: 'SUP-THD-001', name: 'Thread - White', category: 'supplies', quantity: 12, unit: 'spools', minStock: 10, maxStock: 50, cost: 4.50, price: 8.00, vendor: 'Rowley Company', location: 'E1-01', lastOrdered: '2026-02-15', status: 'good' },
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

const INITIAL_CUSTOMERS: Customer[] = [
  { id: 'c1', name: 'Sarah Mitchell', email: 'sarah@mitchell.com', phone: '(512) 555-0142', address: '1422 Lake Austin Blvd, Austin TX', totalJobs: 3, totalRevenue: 12400, lastJob: '2026-02-15', status: 'active', rating: 5 },
  { id: 'c2', name: 'David Chen', email: 'dchen@email.com', phone: '(512) 555-0198', address: '8900 Shoal Creek Blvd, Austin TX', totalJobs: 1, totalRevenue: 4200, lastJob: '2026-01-28', status: 'active', rating: 4 },
  { id: 'c3', name: 'Maria Gonzalez', email: 'maria.g@email.com', phone: '(512) 555-0234', address: '2100 Barton Springs Rd, Austin TX', totalJobs: 2, totalRevenue: 8900, lastJob: '2026-02-20', status: 'active', rating: 5 },
  { id: 'c4', name: 'James Wilson', email: 'jwilson@email.com', phone: '(512) 555-0167', address: '4500 Congress Ave, Austin TX', totalJobs: 1, totalRevenue: 3100, lastJob: '2025-12-10', status: 'inactive', rating: 3 },
  { id: 'c5', name: 'Emily Rodriguez', email: 'emily.r@email.com', phone: '(512) 555-0289', address: '7200 MoPac Expy, Austin TX', totalJobs: 4, totalRevenue: 22600, lastJob: '2026-02-22', status: 'active', rating: 5 },
]

const INITIAL_JOBS: Job[] = [
  { id: 'j1', customerId: 'c5', customerName: 'Emily Rodriguez', title: 'Master Bedroom Drapes', status: 'in-progress', total: 4800, rooms: 1, windows: 3, createdAt: '2026-02-22', dueDate: '2026-03-08' },
  { id: 'j2', customerId: 'c3', customerName: 'Maria Gonzalez', title: 'Living Room & Dining Room', status: 'approved', total: 6200, rooms: 2, windows: 5, createdAt: '2026-02-20', dueDate: '2026-03-15' },
  { id: 'j3', customerId: 'c1', customerName: 'Sarah Mitchell', title: 'Whole House Remodel', status: 'quoted', total: 18500, rooms: 6, windows: 14, createdAt: '2026-02-15', dueDate: '2026-04-01' },
  { id: 'j4', customerId: 'c2', customerName: 'David Chen', title: 'Home Office Roman Shades', status: 'lead', total: 2400, rooms: 1, windows: 2, createdAt: '2026-02-24', dueDate: '' },
  { id: 'j5', customerId: 'c5', customerName: 'Emily Rodriguez', title: 'Kitchen Valance', status: 'completed', total: 1200, rooms: 1, windows: 1, createdAt: '2026-01-15', dueDate: '2026-02-01' },
  { id: 'j6', customerId: 'c1', customerName: 'Sarah Mitchell', title: 'Nursery Blackouts', status: 'invoiced', total: 3200, rooms: 1, windows: 2, createdAt: '2026-01-20', dueDate: '2026-02-10' },
]

const INITIAL_INVOICES: Invoice[] = [
  { id: 'INV-1042', jobId: 'j6', customerName: 'Sarah Mitchell', amount: 3200, status: 'sent', date: '2026-02-10', dueDate: '2026-03-10' },
  { id: 'INV-1041', jobId: 'j5', customerName: 'Emily Rodriguez', amount: 1200, status: 'paid', date: '2026-02-01', dueDate: '2026-03-01' },
  { id: 'INV-1040', jobId: '', customerName: 'David Chen', amount: 4200, status: 'paid', date: '2026-01-28', dueDate: '2026-02-28' },
  { id: 'INV-1039', jobId: '', customerName: 'Maria Gonzalez', amount: 5400, status: 'overdue', date: '2026-01-05', dueDate: '2026-02-05' },
]

// ═══════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════

export default function WorkroomForge() {
  // Navigation
  const [section, setSection] = useState<AppSection>('quotes')
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Quote Builder State
  const [rooms, setRooms] = useState<Room[]>([
    { id: 'room-1', name: 'Living Room', expanded: true, windows: [
      { id: 'w1', name: 'Main Window', width: 72, height: 84, quantity: 1, treatmentType: 'ripplefold', mountType: 'ceiling', liningType: 'blackout', hardwareType: 'track-ripplefold', motorization: 'somfy', notes: '' }
    ]}
  ])
  const [showPhotoModal, setShowPhotoModal] = useState(false)
  const [activeWindowId, setActiveWindowId] = useState<string | null>(null)
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [showCamera, setShowCamera] = useState(false)
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Inventory State
  const [inventoryTab, setInventoryTab] = useState<InventoryTab>('inventory')
  const [inventoryItems, setInventoryItems] = useState(INITIAL_INVENTORY)
  const [invSearch, setInvSearch] = useState('')
  const [invCategory, setInvCategory] = useState('all')
  const [invStatus, setInvStatus] = useState('all')
  const [selectedInvItem, setSelectedInvItem] = useState<InventoryItem | null>(null)

  // CRM State
  const [crmTab, setCrmTab] = useState<CrmTab>('customers')
  const [customers] = useState(INITIAL_CUSTOMERS)
  const [jobs] = useState(INITIAL_JOBS)
  const [crmSearch, setCrmSearch] = useState('')

  // Finance State
  const [financeTab, setFinanceTab] = useState<FinanceTab>('overview')
  const [invoices] = useState(INITIAL_INVOICES)

  // ═══════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════

  const genId = () => Math.random().toString(36).substr(2, 9)

  const calculateWindowPrice = (w: WindowItem): number => {
    const width = Number(w.width) || 0
    const height = Number(w.height) || 0
    const qty = Number(w.quantity) || 1
    const sqft = (width * height) / 144
    const base = (PRICING.base[w.treatmentType] || 40) * sqft
    const lining = (PRICING.lining[w.liningType] || 0) * sqft
    const hardware = PRICING.hardware[w.hardwareType] || 0
    const motor = PRICING.motor[w.motorization] || 0
    return Math.round((base + lining + hardware + motor) * qty)
  }

  const calculateRoomTotal = (room: Room): number => room.windows.reduce((sum, w) => sum + calculateWindowPrice(w), 0)
  const calculateGrandTotal = (): number => rooms.reduce((sum, r) => sum + calculateRoomTotal(r), 0)

  // Room/Window CRUD
  const addRoom = () => setRooms([...rooms, { id: genId(), name: `Room ${rooms.length + 1}`, expanded: true, windows: [] }])
  const deleteRoom = (roomId: string) => { if (rooms.length > 1) setRooms(rooms.filter(r => r.id !== roomId)) }
  const toggleRoom = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, expanded: !r.expanded } : r))
  const updateRoomName = (roomId: string, name: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, name } : r))
  const addWindow = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: [...r.windows, { id: genId(), name: `Window ${r.windows.length + 1}`, width: 48, height: 60, quantity: 1, treatmentType: 'ripplefold', mountType: 'wall', liningType: 'standard', hardwareType: 'track-ripplefold', motorization: 'none', notes: '' }] } : r))
  const updateWindow = (roomId: string, windowId: string, updates: Partial<WindowItem>) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.map(w => w.id === windowId ? { ...w, ...updates } : w) } : r))
  const deleteWindow = (roomId: string, windowId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.filter(w => w.id !== windowId) } : r))
  const copyWindow = (roomId: string, windowId: string) => setRooms(rooms.map(r => { if (r.id === roomId) { const w = r.windows.find(w => w.id === windowId); if (w) return { ...r, windows: [...r.windows, { ...w, id: genId(), name: `${w.name} (Copy)` }] } } return r }))

  // Photo/AI
  const openPhotoModal = (roomId: string, windowId: string) => { setActiveRoomId(roomId); setActiveWindowId(windowId); setShowPhotoModal(true); setUploadedImage(null); setAnalysisResult(null) }
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => { const file = e.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = (e) => { setUploadedImage(e.target?.result as string); setShowCamera(false) }; reader.readAsDataURL(file) } }
  const startCamera = async () => { try { const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } } }); setCameraStream(stream); setShowCamera(true); if (videoRef.current) videoRef.current.srcObject = stream } catch { alert('Unable to access camera.') } }
  const capturePhoto = () => { if (videoRef.current && canvasRef.current) { const v = videoRef.current, c = canvasRef.current; c.width = v.videoWidth; c.height = v.videoHeight; c.getContext('2d')?.drawImage(v, 0, 0); setUploadedImage(c.toDataURL('image/jpeg', 0.9)); stopCamera() } }
  const stopCamera = () => { cameraStream?.getTracks().forEach(t => t.stop()); setCameraStream(null); setShowCamera(false) }
  const closePhotoModal = () => { stopCamera(); setShowPhotoModal(false); setUploadedImage(null); setAnalysisResult(null) }

  const analyzeImage = async () => {
    if (!uploadedImage) return
    setIsAnalyzing(true)
    // TODO: Replace with real API call to /api/v1/smart-analyze
    await new Promise(r => setTimeout(r, 2500))
    const types = ['Single Hung', 'Double Hung', 'Casement', 'Picture Window', 'Bay Window', 'Sliding']
    const type = types[Math.floor(Math.random() * types.length)]
    let w = 36 + Math.floor(Math.random() * 48), h = 48 + Math.floor(Math.random() * 48)
    if (type === 'Picture Window') { w = 60 + Math.floor(Math.random() * 60); h = 48 + Math.floor(Math.random() * 36) }
    if (type === 'Bay Window') { w = 72 + Math.floor(Math.random() * 48); h = 54 + Math.floor(Math.random() * 30) }
    setAnalysisResult({ confidence: 85 + Math.floor(Math.random() * 12), suggestedWidth: w, suggestedHeight: h, windowType: type, recommendations: [`${type} - recommend ${w > 60 ? 'ripplefold drapes' : 'roman shades'}`, h > 72 ? 'Ceiling mount for dramatic effect' : 'Wall mount recommended', 'Blackout lining for bedrooms', w > 72 ? 'Motorization recommended' : 'Manual operation suitable'] })
    setIsAnalyzing(false)
  }

  const applyAnalysis = () => {
    if (analysisResult && activeRoomId && activeWindowId) {
      updateWindow(activeRoomId, activeWindowId, { width: analysisResult.suggestedWidth, height: analysisResult.suggestedHeight, imageUrl: uploadedImage || undefined, aiAnalysis: analysisResult })
      closePhotoModal()
    }
  }

  // Inventory helpers
  const filteredInventory = inventoryItems.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(invSearch.toLowerCase()) || item.sku.toLowerCase().includes(invSearch.toLowerCase())
    const matchesCat = invCategory === 'all' || item.category === invCategory
    const matchesStatus = invStatus === 'all' || item.status === invStatus
    return matchesSearch && matchesCat && matchesStatus
  })
  const lowStockItems = inventoryItems.filter(i => i.status === 'low')
  const totalInvCost = inventoryItems.reduce((s, i) => s + (i.quantity * i.cost), 0)
  const totalRetailValue = inventoryItems.reduce((s, i) => s + (i.quantity * i.price), 0)
  const getStockLevel = (item: InventoryItem) => Math.round((item.quantity / item.maxStock) * 100)

  // CRM helpers
  const filteredCustomers = customers.filter(c => c.name.toLowerCase().includes(crmSearch.toLowerCase()) || c.email.toLowerCase().includes(crmSearch.toLowerCase()))
  const activeJobs = jobs.filter(j => !['completed', 'invoiced'].includes(j.status))
  const pipelineStages = ['lead', 'quoted', 'approved', 'in-progress', 'completed', 'invoiced'] as const

  // Finance helpers
  const totalRevenue = invoices.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount, 0)
  const totalOutstanding = invoices.filter(i => ['sent', 'overdue'].includes(i.status)).reduce((s, i) => s + i.amount, 0)
  const totalOverdue = invoices.filter(i => i.status === 'overdue').reduce((s, i) => s + i.amount, 0)

  // Status colors
  const statusColor = (s: string) => ({ good: 'bg-green-500/20 text-green-400', low: 'bg-red-500/20 text-red-400', active: 'bg-green-500/20 text-green-400', inactive: 'bg-gray-500/20 text-gray-400', lead: 'bg-blue-500/20 text-blue-400', quoted: 'bg-yellow-500/20 text-yellow-400', approved: 'bg-purple-500/20 text-purple-400', 'in-progress': 'bg-orange-500/20 text-orange-400', completed: 'bg-green-500/20 text-green-400', invoiced: 'bg-emerald-500/20 text-emerald-400', draft: 'bg-gray-500/20 text-gray-400', sent: 'bg-blue-500/20 text-blue-400', paid: 'bg-green-500/20 text-green-400', overdue: 'bg-red-500/20 text-red-400', pending: 'bg-yellow-500/20 text-yellow-400', shipped: 'bg-blue-500/20 text-blue-400', delivered: 'bg-green-500/20 text-green-400' }[s] || 'bg-gray-500/20 text-gray-400')

  // Section configs
  const sections = [
    { id: 'quotes' as const, label: 'Quote Builder', icon: Calculator, badge: rooms.reduce((s, r) => s + r.windows.length, 0) },
    { id: 'inventory' as const, label: 'Inventory', icon: Package, badge: lowStockItems.length > 0 ? lowStockItems.length : undefined, badgeColor: 'bg-red-500' },
    { id: 'crm' as const, label: 'CRM', icon: Users, badge: activeJobs.length },
    { id: 'finance' as const, label: 'Finance', icon: DollarSign },
  ]

  // ═══════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════

  return (
    <div className="h-screen bg-[#080810] text-white flex overflow-hidden">
      {/* ═══ SIDEBAR ═══ */}
      <aside className={`${sidebarOpen ? 'w-60' : 'w-16'} bg-[#0c0c18] border-r border-white/[0.06] flex flex-col transition-all duration-200 flex-shrink-0`}>
        {/* Logo */}
        <div className="h-14 flex items-center px-4 border-b border-white/[0.06]">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center flex-shrink-0">
            <Factory className="w-4 h-4 text-white" />
          </div>
          {sidebarOpen && (
            <div className="ml-3">
              <h1 className="text-sm font-bold text-white">WorkroomForge</h1>
              <p className="text-[10px] text-gray-500">Empire Workroom</p>
            </div>
          )}
        </div>

        {/* Nav Items */}
        <nav className="flex-1 py-3 px-2 space-y-1">
          {sections.map(s => (
            <button key={s.id} onClick={() => setSection(s.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                section === s.id 
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20' 
                  : 'text-gray-400 hover:text-white hover:bg-white/[0.04]'
              }`}>
              <s.icon className="w-4.5 h-4.5 flex-shrink-0" />
              {sidebarOpen && (
                <>
                  <span className="flex-1 text-left">{s.label}</span>
                  {s.badge !== undefined && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${s.badgeColor || 'bg-white/10 text-gray-400'} ${section === s.id ? 'text-amber-300' : ''}`}>
                      {s.badge}
                    </span>
                  )}
                </>
              )}
            </button>
          ))}
        </nav>

        {/* Bottom */}
        <div className="p-2 border-t border-white/[0.06]">
          <button onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/[0.04] text-sm">
            <Menu className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>Collapse</span>}
          </button>
          <button onClick={() => window.location.href = 'http://localhost:8080'}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-500 hover:text-white hover:bg-white/[0.04] text-sm mt-1">
            <Home className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>Empire Home</span>}
          </button>
        </div>
      </aside>

      {/* ═══ MAIN CONTENT ═══ */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-14 bg-[#0c0c18] border-b border-white/[0.06] flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold">{sections.find(s => s.id === section)?.label}</h2>
          </div>
          <div className="flex items-center gap-3">
            {section === 'quotes' && (
              <>
                <div className="text-right mr-2">
                  <p className="text-xl font-bold text-[#C9A84C]">${calculateGrandTotal().toLocaleString()}</p>
                  <p className="text-[10px] text-gray-500">Grand Total</p>
                </div>
                <button className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-lg font-semibold text-sm transition">
                  <Send className="w-3.5 h-3.5" /> Send Quote
                </button>
              </>
            )}
            <button onClick={() => window.location.href = 'http://localhost:3009'}
              className="flex items-center gap-1.5 bg-purple-500/15 text-purple-400 px-3 py-1.5 rounded-lg text-xs hover:bg-purple-500/25 transition">
              <Brain className="w-3.5 h-3.5" /> MAX
            </button>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-6">

          {/* ════════════════════════════════════════════════ */}
          {/* QUOTE BUILDER */}
          {/* ════════════════════════════════════════════════ */}
          {section === 'quotes' && (
            <div className="max-w-6xl mx-auto space-y-5">
              {/* AI Banner */}
              <div className="bg-gradient-to-r from-purple-500/10 via-pink-500/10 to-amber-500/10 border border-purple-500/20 rounded-xl p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center flex-shrink-0">
                  <Brain className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm flex items-center gap-2">AI Window Analysis <span className="text-[10px] bg-purple-500/30 text-purple-300 px-1.5 py-0.5 rounded-full">BETA</span></h3>
                  <p className="text-xs text-gray-400">Upload photo, use Polycam 3D scan, or enter manual measurements</p>
                </div>
              </div>

              {/* Rooms */}
              {rooms.map(room => (
                <div key={room.id} className="bg-[#12121e] rounded-xl border border-white/[0.06] overflow-hidden">
                  <div className="px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <button onClick={() => toggleRoom(room.id)} className="p-1 hover:bg-white/[0.06] rounded">
                        {room.expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      <input type="text" value={room.name} onChange={(e) => updateRoomName(room.id, e.target.value)} className="bg-transparent font-semibold focus:outline-none text-sm" />
                      <span className="text-xs text-gray-500">({room.windows.length} windows)</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-[#C9A84C]">${calculateRoomTotal(room).toLocaleString()}</span>
                      <button onClick={() => deleteRoom(room.id)} className="p-1.5 text-gray-500 hover:text-red-400 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>

                  {room.expanded && (
                    <div className="p-4 space-y-3">
                      {room.windows.map(w => (
                        <div key={w.id} className={`bg-[#1a1a2e] rounded-lg p-4 border ${w.aiAnalysis ? 'border-purple-500/30' : 'border-white/[0.04]'}`}>
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <input type="text" value={w.name} onChange={(e) => updateWindow(room.id, w.id, { name: e.target.value })} className="bg-transparent font-medium text-sm focus:outline-none" />
                              {w.aiAnalysis && <span className="text-[10px] bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded-full flex items-center gap-1"><Sparkles className="w-2.5 h-2.5" /> AI {w.aiAnalysis.confidence}%</span>}
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm font-bold text-green-400">${calculateWindowPrice(w).toLocaleString()}</span>
                              <button onClick={() => copyWindow(room.id, w.id)} className="p-1.5 text-gray-500 hover:text-white hover:bg-white/[0.06] rounded"><Copy className="w-3.5 h-3.5" /></button>
                              <button onClick={() => deleteWindow(room.id, w.id)} className="p-1.5 text-gray-500 hover:text-red-400 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">AI Measure</label>
                              <button onClick={() => openPhotoModal(room.id, w.id)} className="w-full h-9 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg flex items-center justify-center gap-1.5 text-xs text-purple-300 transition">
                                <Camera className="w-3.5 h-3.5" /> Photo
                              </button>
                            </div>
                            {[
                              { label: 'Width (in)', value: w.width, key: 'width', type: 'number' },
                              { label: 'Height (in)', value: w.height, key: 'height', type: 'number' },
                              { label: 'Qty', value: w.quantity, key: 'quantity', type: 'number' },
                            ].map(f => (
                              <div key={f.key}>
                                <label className="block text-[10px] text-gray-500 mb-1">{f.label}</label>
                                <input type="number" value={f.value} onChange={(e) => updateWindow(room.id, w.id, { [f.key]: Number(e.target.value) })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-3 text-sm focus:border-[#C9A84C] outline-none" />
                              </div>
                            ))}
                            {[
                              { label: 'Treatment', key: 'treatmentType', value: w.treatmentType, options: [['ripplefold','Ripplefold'],['pinch-pleat','Pinch Pleat'],['rod-pocket','Rod Pocket'],['grommet','Grommet'],['roman-shade','Roman Shade'],['roller-shade','Roller Shade']] },
                              { label: 'Lining', key: 'liningType', value: w.liningType, options: [['unlined','Unlined'],['standard','Standard'],['blackout','Blackout'],['thermal','Thermal'],['interlining','Interlining']] },
                              { label: 'Hardware', key: 'hardwareType', value: w.hardwareType, options: [['none','None'],['rod-standard','Rod Std'],['rod-decorative','Rod Deco'],['track-basic','Track Basic'],['track-ripplefold','Track Ripple']] },
                              { label: 'Motor', key: 'motorization', value: w.motorization, options: [['none','None'],['somfy','Somfy $285'],['lutron','Lutron $425'],['generic','Generic $185']] },
                              { label: 'Mount', key: 'mountType', value: w.mountType, options: [['wall','Wall'],['ceiling','Ceiling'],['inside','Inside']] },
                            ].map(f => (
                              <div key={f.key}>
                                <label className="block text-[10px] text-gray-500 mb-1">{f.label}</label>
                                <select value={f.value} onChange={(e) => updateWindow(room.id, w.id, { [f.key]: e.target.value })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-2 text-sm focus:border-[#C9A84C] outline-none">
                                  {f.options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                                </select>
                              </div>
                            ))}
                          </div>

                          {w.aiAnalysis && (
                            <div className="mt-3 p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg">
                              <div className="flex items-center gap-2 mb-2">
                                <Lightbulb className="w-3.5 h-3.5 text-purple-400" />
                                <span className="text-xs font-medium text-purple-300">AI: {w.aiAnalysis.windowType}</span>
                              </div>
                              <div className="grid grid-cols-2 gap-1.5">
                                {w.aiAnalysis.recommendations.map((rec, i) => (
                                  <div key={i} className="flex items-start gap-1.5 text-[11px] text-gray-400">
                                    <Check className="w-3 h-3 text-purple-400 flex-shrink-0 mt-0.5" /><span>{rec}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          <input type="text" value={w.notes} onChange={(e) => updateWindow(room.id, w.id, { notes: e.target.value })} placeholder="Notes..." className="w-full mt-3 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-3 py-2 text-xs focus:border-[#C9A84C] outline-none" />
                        </div>
                      ))}

                      <button onClick={() => addWindow(room.id)} className="w-full py-2.5 border border-dashed border-white/10 hover:border-[#C9A84C] rounded-lg text-gray-500 hover:text-[#C9A84C] flex items-center justify-center gap-2 text-sm transition">
                        <Plus className="w-4 h-4" /> Add Window
                      </button>
                    </div>
                  )}
                </div>
              ))}

              <button onClick={addRoom} className="w-full py-3 bg-[#12121e] hover:bg-[#1a1a2e] border border-white/[0.06] hover:border-[#C9A84C] rounded-xl text-gray-400 hover:text-[#C9A84C] flex items-center justify-center gap-2 text-sm transition">
                <Plus className="w-4 h-4" /> Add Room
              </button>

              {/* Quote Summary */}
              <div className="bg-[#12121e] rounded-xl border border-white/[0.06] p-5">
                <h3 className="text-sm font-bold mb-3">Quote Summary</h3>
                {rooms.map(r => (
                  <div key={r.id} className="flex justify-between py-2 border-b border-white/[0.04] text-sm">
                    <span className="text-gray-400">{r.name} ({r.windows.length} windows)</span>
                    <span className="font-semibold">${calculateRoomTotal(r).toLocaleString()}</span>
                  </div>
                ))}
                <div className="flex justify-between pt-3 text-lg">
                  <span className="font-bold">Grand Total</span>
                  <span className="font-bold text-[#C9A84C]">${calculateGrandTotal().toLocaleString()}</span>
                </div>
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════ */}
          {/* INVENTORY */}
          {/* ════════════════════════════════════════════════ */}
          {section === 'inventory' && (
            <div className="max-w-6xl mx-auto space-y-5">
              {/* Sub-tabs */}
              <div className="flex gap-1 bg-[#12121e] rounded-lg p-1 w-fit">
                {(['inventory', 'orders', 'vendors'] as const).map(tab => (
                  <button key={tab} onClick={() => setInventoryTab(tab)}
                    className={`px-4 py-1.5 rounded-md text-xs font-medium transition ${inventoryTab === tab ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'text-gray-400 hover:text-white'}`}>
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {inventoryTab === 'inventory' && (
                <>
                  {/* Stats */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      { icon: Package, label: 'Total Items', value: inventoryItems.length, color: 'text-blue-400' },
                      { icon: AlertTriangle, label: 'Low Stock', value: lowStockItems.length, color: 'text-red-400', sub: lowStockItems.length > 0 ? 'Action needed' : undefined },
                      { icon: DollarSign, label: 'Inventory Cost', value: `$${totalInvCost.toLocaleString()}`, color: 'text-green-400' },
                      { icon: TrendingUp, label: 'Retail Value', value: `$${totalRetailValue.toLocaleString()}`, color: 'text-[#C9A84C]' },
                    ].map((s, i) => (
                      <div key={i} className="bg-[#12121e] rounded-xl p-4 border border-white/[0.06]">
                        <div className="flex items-center justify-between mb-2">
                          <s.icon className={`w-4 h-4 ${s.color}`} />
                          {s.sub && <span className="text-[10px] text-red-400">{s.sub}</span>}
                        </div>
                        <p className="text-xl font-bold">{s.value}</p>
                        <p className="text-[11px] text-gray-500">{s.label}</p>
                      </div>
                    ))}
                  </div>

                  {/* Low Stock Alert */}
                  {lowStockItems.length > 0 && (
                    <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        <h3 className="text-xs font-semibold text-red-400">Low Stock Alert</h3>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {lowStockItems.map(item => (
                          <button key={item.id} onClick={() => setSelectedInvItem(item)} className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-2.5 py-1 rounded-lg text-xs transition">
                            {item.name} ({item.quantity} {item.unit})
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Filters */}
                  <div className="flex gap-2 flex-wrap">
                    <button onClick={() => setInvCategory('all')} className={`px-3 py-1.5 rounded-lg text-xs transition ${invCategory === 'all' ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'bg-[#1a1a2e] hover:bg-[#252540]'}`}>All</button>
                    {CATEGORIES.map(cat => (
                      <button key={cat.id} onClick={() => setInvCategory(cat.id)} className={`px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition ${invCategory === cat.id ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'bg-[#1a1a2e] hover:bg-[#252540]'}`}>
                        <cat.icon className="w-3 h-3" /> {cat.name}
                      </button>
                    ))}
                  </div>

                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                      <input type="text" placeholder="Search by name or SKU..." value={invSearch} onChange={(e) => setInvSearch(e.target.value)} className="w-full bg-[#1a1a2e] border border-white/[0.08] rounded-lg pl-9 pr-4 py-2 text-sm focus:border-[#C9A84C] outline-none" />
                    </div>
                    <select value={invStatus} onChange={(e) => setInvStatus(e.target.value)} className="bg-[#1a1a2e] border border-white/[0.08] rounded-lg px-3 py-2 text-sm focus:border-[#C9A84C] outline-none">
                      <option value="all">All Status</option>
                      <option value="good">Good Stock</option>
                      <option value="low">Low Stock</option>
                    </select>
                  </div>

                  {/* Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {filteredInventory.map(item => (
                      <div key={item.id} onClick={() => setSelectedInvItem(item)} className={`bg-[#12121e] rounded-xl p-4 border cursor-pointer transition hover:border-gray-600 ${item.status === 'low' ? 'border-red-500/30' : 'border-white/[0.06]'}`}>
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <p className="font-mono text-[10px] text-gray-500">{item.sku}</p>
                            <h3 className="font-semibold text-sm mt-0.5">{item.name}</h3>
                          </div>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor(item.status)}`}>{item.status}</span>
                        </div>
                        <div className="flex items-end justify-between mb-2">
                          <div><p className="text-xl font-bold">{item.quantity}</p><p className="text-[10px] text-gray-500">{item.unit}</p></div>
                          <div className="text-right"><p className="text-xs font-semibold text-[#C9A84C]">${item.price.toFixed(2)}</p><p className="text-[10px] text-gray-500">Cost: ${item.cost.toFixed(2)}</p></div>
                        </div>
                        <div className="h-1.5 bg-[#1a1a2e] rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${item.status === 'low' ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${Math.min(getStockLevel(item), 100)}%` }} />
                        </div>
                        <div className="mt-2 flex items-center justify-between text-[10px] text-gray-600">
                          <span>{item.vendor}</span><span>{item.location}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {inventoryTab === 'orders' && (
                <div className="bg-[#12121e] rounded-xl border border-white/[0.06] overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-[#1a1a2e]">
                      <tr>{['PO #', 'Vendor', 'Date', 'Items', 'Total', 'Status', 'ETA'].map(h => <th key={h} className="px-4 py-2.5 text-left text-[10px] text-gray-400 font-medium">{h}</th>)}</tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {PURCHASE_ORDERS.map(o => (
                        <tr key={o.id} className="hover:bg-white/[0.02]">
                          <td className="px-4 py-3 font-mono text-xs">{o.id}</td>
                          <td className="px-4 py-3 text-sm">{o.vendor}</td>
                          <td className="px-4 py-3 text-xs text-gray-400">{o.date}</td>
                          <td className="px-4 py-3 text-xs">{o.items}</td>
                          <td className="px-4 py-3 text-sm font-semibold">${o.total.toLocaleString()}</td>
                          <td className="px-4 py-3"><span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor(o.status)}`}>{o.status}</span></td>
                          <td className="px-4 py-3 text-xs text-gray-400">{o.eta || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {inventoryTab === 'vendors' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {VENDORS.map(v => (
                    <div key={v.id} className="bg-[#12121e] rounded-xl p-4 border border-white/[0.06]">
                      <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 rounded-lg bg-[#1a1a2e] flex items-center justify-center">
                          <Building2 className="w-5 h-5 text-[#C9A84C]" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-sm">{v.name}</h3>
                          <p className="text-xs text-gray-500">{v.contact}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-2 mb-3">
                        {[
                          { label: 'Orders', value: v.totalOrders, color: 'text-blue-400' },
                          { label: 'Spent', value: `$${(v.totalSpent/1000).toFixed(1)}k`, color: 'text-green-400' },
                          { label: 'Last', value: v.lastOrder.slice(5), color: 'text-white' },
                        ].map((s, i) => (
                          <div key={i} className="bg-[#1a1a2e] rounded-lg p-2 text-center">
                            <p className={`text-sm font-bold ${s.color}`}>{s.value}</p>
                            <p className="text-[10px] text-gray-500">{s.label}</p>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-2">
                        <button className="flex-1 bg-[#1a1a2e] hover:bg-[#252540] py-2 rounded-lg text-xs flex items-center justify-center gap-1.5 transition"><ShoppingCart className="w-3 h-3" /> Order</button>
                        <button className="flex-1 bg-[#1a1a2e] hover:bg-[#252540] py-2 rounded-lg text-xs transition">{v.phone}</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ════════════════════════════════════════════════ */}
          {/* CRM */}
          {/* ════════════════════════════════════════════════ */}
          {section === 'crm' && (
            <div className="max-w-6xl mx-auto space-y-5">
              <div className="flex gap-1 bg-[#12121e] rounded-lg p-1 w-fit">
                {(['customers', 'jobs', 'pipeline'] as const).map(tab => (
                  <button key={tab} onClick={() => setCrmTab(tab)}
                    className={`px-4 py-1.5 rounded-md text-xs font-medium transition ${crmTab === tab ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'text-gray-400 hover:text-white'}`}>
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {crmTab === 'customers' && (
                <>
                  <div className="flex gap-3">
                    <div className="relative flex-1">
                      <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                      <input type="text" placeholder="Search customers..." value={crmSearch} onChange={(e) => setCrmSearch(e.target.value)} className="w-full bg-[#1a1a2e] border border-white/[0.08] rounded-lg pl-9 pr-4 py-2 text-sm focus:border-[#C9A84C] outline-none" />
                    </div>
                    <button className="flex items-center gap-2 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] px-4 py-2 rounded-lg font-semibold text-sm"><UserPlus className="w-3.5 h-3.5" /> Add Customer</button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {filteredCustomers.map(c => (
                      <div key={c.id} className="bg-[#12121e] rounded-xl p-4 border border-white/[0.06] hover:border-gray-600 transition cursor-pointer">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500/20 to-orange-600/20 flex items-center justify-center text-[#C9A84C] font-bold text-sm">
                              {c.name.split(' ').map(n => n[0]).join('')}
                            </div>
                            <div>
                              <h3 className="font-semibold text-sm">{c.name}</h3>
                              <p className="text-xs text-gray-500">{c.email}</p>
                            </div>
                          </div>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor(c.status)}`}>{c.status}</span>
                        </div>
                        <div className="grid grid-cols-3 gap-2 mb-3">
                          <div className="bg-[#1a1a2e] rounded-lg p-2 text-center">
                            <p className="text-sm font-bold">{c.totalJobs}</p><p className="text-[10px] text-gray-500">Jobs</p>
                          </div>
                          <div className="bg-[#1a1a2e] rounded-lg p-2 text-center">
                            <p className="text-sm font-bold text-green-400">${(c.totalRevenue/1000).toFixed(1)}k</p><p className="text-[10px] text-gray-500">Revenue</p>
                          </div>
                          <div className="bg-[#1a1a2e] rounded-lg p-2 text-center">
                            <div className="flex items-center justify-center gap-0.5">{Array(5).fill(0).map((_, i) => <Star key={i} className={`w-3 h-3 ${i < c.rating ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`} />)}</div>
                            <p className="text-[10px] text-gray-500">Rating</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-gray-500">
                          <span className="flex items-center gap-1"><Phone className="w-3 h-3" /> {c.phone}</span>
                          <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {c.address.split(',')[1]?.trim()}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {crmTab === 'jobs' && (
                <div className="space-y-3">
                  {jobs.map(j => (
                    <div key={j.id} className="bg-[#12121e] rounded-xl p-4 border border-white/[0.06] flex items-center justify-between hover:border-gray-600 transition cursor-pointer">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-lg bg-[#1a1a2e] flex items-center justify-center">
                          <Briefcase className="w-4 h-4 text-[#C9A84C]" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-sm">{j.title}</h3>
                          <p className="text-xs text-gray-500">{j.customerName} • {j.rooms} rooms, {j.windows} windows</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-sm font-bold text-[#C9A84C]">${j.total.toLocaleString()}</p>
                          <p className="text-[10px] text-gray-500">{j.dueDate ? `Due ${j.dueDate}` : 'No date'}</p>
                        </div>
                        <span className={`text-[10px] px-2 py-0.5 rounded ${statusColor(j.status)}`}>{j.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {crmTab === 'pipeline' && (
                <div className="flex gap-3 overflow-x-auto pb-4">
                  {pipelineStages.map(stage => {
                    const stageJobs = jobs.filter(j => j.status === stage)
                    const stageTotal = stageJobs.reduce((s, j) => s + j.total, 0)
                    return (
                      <div key={stage} className="min-w-[220px] flex-shrink-0">
                        <div className="flex items-center justify-between mb-2 px-1">
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor(stage)}`}>{stage}</span>
                            <span className="text-[10px] text-gray-500">{stageJobs.length}</span>
                          </div>
                          <span className="text-[10px] text-gray-500">${stageTotal.toLocaleString()}</span>
                        </div>
                        <div className="space-y-2">
                          {stageJobs.map(j => (
                            <div key={j.id} className="bg-[#12121e] rounded-lg p-3 border border-white/[0.06] cursor-pointer hover:border-gray-600 transition">
                              <h4 className="text-xs font-semibold mb-1">{j.title}</h4>
                              <p className="text-[10px] text-gray-500">{j.customerName}</p>
                              <p className="text-xs font-bold text-[#C9A84C] mt-1">${j.total.toLocaleString()}</p>
                            </div>
                          ))}
                          {stageJobs.length === 0 && (
                            <div className="bg-[#12121e] rounded-lg p-3 border border-dashed border-white/[0.06] text-center">
                              <p className="text-[10px] text-gray-600">Empty</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* ════════════════════════════════════════════════ */}
          {/* FINANCE */}
          {/* ════════════════════════════════════════════════ */}
          {section === 'finance' && (
            <div className="max-w-6xl mx-auto space-y-5">
              <div className="flex gap-1 bg-[#12121e] rounded-lg p-1 w-fit">
                {(['overview', 'invoices', 'expenses'] as const).map(tab => (
                  <button key={tab} onClick={() => setFinanceTab(tab)}
                    className={`px-4 py-1.5 rounded-md text-xs font-medium transition ${financeTab === tab ? 'bg-[#C9A84C] text-[#0D0D0D]' : 'text-gray-400 hover:text-white'}`}>
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {financeTab === 'overview' && (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {[
                      { icon: DollarSign, label: 'Revenue (Paid)', value: `$${totalRevenue.toLocaleString()}`, color: 'text-green-400' },
                      { icon: Clock, label: 'Outstanding', value: `$${totalOutstanding.toLocaleString()}`, color: 'text-blue-400' },
                      { icon: AlertTriangle, label: 'Overdue', value: `$${totalOverdue.toLocaleString()}`, color: 'text-red-400' },
                      { icon: TrendingUp, label: 'Pipeline Value', value: `$${jobs.reduce((s, j) => s + j.total, 0).toLocaleString()}`, color: 'text-[#C9A84C]' },
                    ].map((s, i) => (
                      <div key={i} className="bg-[#12121e] rounded-xl p-4 border border-white/[0.06]">
                        <s.icon className={`w-4 h-4 ${s.color} mb-2`} />
                        <p className="text-xl font-bold">{s.value}</p>
                        <p className="text-[11px] text-gray-500">{s.label}</p>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Recent Invoices */}
                    <div className="bg-[#12121e] rounded-xl border border-white/[0.06] p-4">
                      <h3 className="text-sm font-bold mb-3">Recent Invoices</h3>
                      <div className="space-y-2">
                        {invoices.slice(0, 4).map(inv => (
                          <div key={inv.id} className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
                            <div>
                              <p className="text-xs font-semibold">{inv.id}</p>
                              <p className="text-[10px] text-gray-500">{inv.customerName}</p>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="text-sm font-bold">${inv.amount.toLocaleString()}</span>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor(inv.status)}`}>{inv.status}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Top Customers */}
                    <div className="bg-[#12121e] rounded-xl border border-white/[0.06] p-4">
                      <h3 className="text-sm font-bold mb-3">Top Customers</h3>
                      <div className="space-y-2">
                        {[...customers].sort((a, b) => b.totalRevenue - a.totalRevenue).slice(0, 4).map((c, i) => (
                          <div key={c.id} className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] text-gray-500 w-4">{i + 1}.</span>
                              <span className="text-xs font-semibold">{c.name}</span>
                            </div>
                            <span className="text-sm font-bold text-green-400">${c.totalRevenue.toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              )}

              {financeTab === 'invoices' && (
                <div className="bg-[#12121e] rounded-xl border border-white/[0.06] overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-[#1a1a2e]">
                      <tr>{['Invoice', 'Customer', 'Amount', 'Date', 'Due', 'Status'].map(h => <th key={h} className="px-4 py-2.5 text-left text-[10px] text-gray-400 font-medium">{h}</th>)}</tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04]">
                      {invoices.map(inv => (
                        <tr key={inv.id} className="hover:bg-white/[0.02]">
                          <td className="px-4 py-3 font-mono text-xs">{inv.id}</td>
                          <td className="px-4 py-3 text-sm">{inv.customerName}</td>
                          <td className="px-4 py-3 text-sm font-bold">${inv.amount.toLocaleString()}</td>
                          <td className="px-4 py-3 text-xs text-gray-400">{inv.date}</td>
                          <td className="px-4 py-3 text-xs text-gray-400">{inv.dueDate}</td>
                          <td className="px-4 py-3"><span className={`text-[10px] px-1.5 py-0.5 rounded ${statusColor(inv.status)}`}>{inv.status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {financeTab === 'expenses' && (
                <div className="bg-[#12121e] rounded-xl border border-white/[0.06] p-8 text-center">
                  <Receipt className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                  <h3 className="text-sm font-semibold mb-1">Expense Tracking</h3>
                  <p className="text-xs text-gray-500">Coming soon — will connect to QuickBooks</p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* ═══ PHOTO MODAL ═══ */}
      {showPhotoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80" onClick={closePhotoModal} />
          <div className="relative bg-[#12121e] rounded-2xl border border-white/[0.08] w-full max-w-2xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between bg-gradient-to-r from-purple-500/10 to-pink-500/10">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center"><Brain className="w-4 h-4 text-white" /></div>
                <div><h2 className="font-bold text-sm">AI Window Analysis</h2><p className="text-[10px] text-gray-400">Photo • Polycam 3D • Manual</p></div>
              </div>
              <button onClick={closePhotoModal} className="p-1.5 hover:bg-white/10 rounded-lg"><X className="w-4 h-4" /></button>
            </div>

            <div className="p-5">
              {showCamera && (
                <div className="relative mb-4">
                  <video ref={videoRef} autoPlay playsInline className="w-full rounded-xl" />
                  <canvas ref={canvasRef} className="hidden" />
                  <button onClick={capturePhoto} className="absolute bottom-4 left-1/2 -translate-x-1/2 w-14 h-14 bg-white rounded-full flex items-center justify-center"><div className="w-12 h-12 border-4 border-gray-300 rounded-full" /></button>
                  <button onClick={stopCamera} className="absolute top-3 right-3 p-1.5 bg-black/50 rounded-lg"><X className="w-4 h-4" /></button>
                </div>
              )}

              {!showCamera && !uploadedImage && (
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <button onClick={startCamera} className="flex flex-col items-center gap-2 p-6 bg-[#1a1a2e] hover:bg-[#252540] border border-dashed border-white/10 hover:border-purple-500/50 rounded-xl group transition">
                    <Camera className="w-8 h-8 text-gray-500 group-hover:text-purple-400" /><span className="text-xs">Take Photo</span>
                  </button>
                  <button onClick={() => fileInputRef.current?.click()} className="flex flex-col items-center gap-2 p-6 bg-[#1a1a2e] hover:bg-[#252540] border border-dashed border-white/10 hover:border-purple-500/50 rounded-xl group transition">
                    <Upload className="w-8 h-8 text-gray-500 group-hover:text-purple-400" /><span className="text-xs">Upload Photo</span>
                  </button>
                  <button className="flex flex-col items-center gap-2 p-6 bg-[#1a1a2e] hover:bg-[#252540] border border-dashed border-white/10 hover:border-purple-500/50 rounded-xl group transition">
                    <Box className="w-8 h-8 text-gray-500 group-hover:text-purple-400" /><span className="text-xs">Polycam 3D</span>
                  </button>
                  <input ref={fileInputRef} type="file" accept="image/*,.obj,.ply,.glb" onChange={handleFileUpload} className="hidden" />
                </div>
              )}

              {uploadedImage && !showCamera && (
                <div className="relative mb-4">
                  <img src={uploadedImage} alt="Window" className="w-full rounded-xl" />
                  {isAnalyzing && (
                    <div className="absolute inset-0 bg-black/60 rounded-xl flex flex-col items-center justify-center">
                      <Loader2 className="w-10 h-10 text-purple-400 animate-spin mb-3" />
                      <p className="text-sm font-medium">Analyzing...</p>
                    </div>
                  )}
                  {!isAnalyzing && !analysisResult && <button onClick={() => setUploadedImage(null)} className="absolute top-3 right-3 p-1.5 bg-black/50 rounded-lg"><X className="w-4 h-4" /></button>}
                </div>
              )}

              {analysisResult && (
                <div className="bg-[#1a1a2e] rounded-xl p-4 mb-4 border border-purple-500/20">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-bold flex items-center gap-2"><Sparkles className="w-4 h-4 text-purple-400" /> Results</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">{analysisResult.confidence}%</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div className="bg-[#0c0c18] rounded-lg p-3 text-center">
                      <Ruler className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                      <p className="text-xl font-bold">{analysisResult.suggestedWidth}"</p>
                      <p className="text-[10px] text-gray-500">Width</p>
                    </div>
                    <div className="bg-[#0c0c18] rounded-lg p-3 text-center">
                      <Maximize2 className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                      <p className="text-xl font-bold">{analysisResult.suggestedHeight}"</p>
                      <p className="text-[10px] text-gray-500">Height</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mb-2">Type: <span className="text-white">{analysisResult.windowType}</span></p>
                  <div className="bg-purple-500/5 rounded-lg p-2.5">
                    {analysisResult.recommendations.map((r: string, i: number) => (
                      <p key={i} className="text-[11px] text-gray-400 flex items-start gap-1.5 mb-1 last:mb-0"><Check className="w-3 h-3 text-purple-400 flex-shrink-0 mt-0.5" />{r}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                {uploadedImage && !analysisResult && !isAnalyzing && (
                  <>
                    <button onClick={() => setUploadedImage(null)} className="flex-1 bg-[#1a1a2e] py-2.5 rounded-lg text-sm">Retake</button>
                    <button onClick={analyzeImage} className="flex-1 bg-gradient-to-r from-purple-500 to-pink-600 py-2.5 rounded-lg font-semibold text-sm flex items-center justify-center gap-2"><Sparkles className="w-4 h-4" /> Analyze</button>
                  </>
                )}
                {analysisResult && (
                  <>
                    <button onClick={() => { setAnalysisResult(null); setUploadedImage(null) }} className="flex-1 bg-[#1a1a2e] py-2.5 rounded-lg text-sm flex items-center justify-center gap-2"><RotateCcw className="w-3.5 h-3.5" /> Retry</button>
                    <button onClick={applyAnalysis} className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 py-2.5 rounded-lg font-semibold text-sm flex items-center justify-center gap-2"><Check className="w-4 h-4" /> Apply</button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ═══ INVENTORY DETAIL MODAL ═══ */}
      {selectedInvItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => setSelectedInvItem(null)} />
          <div className="relative bg-[#12121e] rounded-2xl border border-white/[0.08] w-full max-w-md overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between">
              <div><p className="font-mono text-[10px] text-gray-500">{selectedInvItem.sku}</p><h2 className="font-bold text-sm">{selectedInvItem.name}</h2></div>
              <button onClick={() => setSelectedInvItem(null)} className="p-1 hover:bg-white/[0.06] rounded"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className={`text-xs px-2 py-0.5 rounded ${statusColor(selectedInvItem.status)}`}>{selectedInvItem.status} stock</span>
                <span className="text-xs text-gray-500">{selectedInvItem.vendor}</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#1a1a2e] rounded-lg p-3 text-center"><p className="text-2xl font-bold">{selectedInvItem.quantity}</p><p className="text-[10px] text-gray-500">{selectedInvItem.unit} in stock</p></div>
                <div className="bg-[#1a1a2e] rounded-lg p-3 text-center"><p className="text-2xl font-bold text-[#C9A84C]">${selectedInvItem.price}</p><p className="text-[10px] text-gray-500">Retail Price</p></div>
              </div>
              {[
                ['Cost', `$${selectedInvItem.cost.toFixed(2)} per unit`],
                ['Min Stock', `${selectedInvItem.minStock} ${selectedInvItem.unit}`],
                ['Max Stock', `${selectedInvItem.maxStock} ${selectedInvItem.unit}`],
                ['Location', selectedInvItem.location],
                ['Last Ordered', selectedInvItem.lastOrdered],
              ].map(([l, v]) => (
                <div key={l} className="flex justify-between text-xs"><span className="text-gray-500">{l}</span><span>{v}</span></div>
              ))}
              <div className="pt-2">
                <div className="h-2 bg-[#1a1a2e] rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${selectedInvItem.status === 'low' ? 'bg-red-500' : 'bg-green-500'}`} style={{ width: `${Math.min(getStockLevel(selectedInvItem), 100)}%` }} />
                </div>
              </div>
            </div>
            <div className="px-5 py-3 border-t border-white/[0.06] flex gap-2">
              <button className="flex-1 bg-[#1a1a2e] hover:bg-[#252540] py-2.5 rounded-lg text-xs flex items-center justify-center gap-1.5"><Edit className="w-3 h-3" /> Edit</button>
              <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-2.5 rounded-lg text-xs flex items-center justify-center gap-1.5"><ShoppingCart className="w-3 h-3" /> Reorder</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
