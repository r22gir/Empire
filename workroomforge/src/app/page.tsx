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

interface UpholsteryItem {
  id: string; name: string; furnitureType: string; style: string
  width: number; depth: number; height: number; cushionCount: number
  fabricYards: number; fabricType: 'plain' | 'patterned' | 'leather'
  laborType: 'standard' | 'tufted' | 'channeled' | 'leather'
  notes: string; imageUrl?: string
  aiAnalysis?: {
    confidence: number; furnitureType: string; style: string
    dimensions: { width: number; depth: number; height: number }
    cushions: { seat: number; back: number; throw_pillows: number }
    fabricYardsPlain: number; fabricYardsPatterned: number
    hasWelting: boolean; hasTufting: boolean; hasChanneling: boolean
    hasSkirt: boolean; hasNailhead: boolean; suggestedLaborType: string
    laborCostLow: number; laborCostHigh: number; newFoamRecommended: boolean
    notes: string; questions: string[]
  }
}

interface Room {
  id: string; name: string; windows: WindowItem[]; upholstery: UpholsteryItem[]; expanded: boolean
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

const UPHOLSTERY_PRICING = {
  labor: { 'standard': 62, 'tufted': 78, 'channeled': 72, 'leather': 100 } as Record<string, number>,
  fabric: { 'plain': 22, 'patterned': 50, 'leather': 110 } as Record<string, number>,
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
    { id: 'room-1', name: 'Living Room', expanded: true, upholstery: [], windows: [
      { id: 'w1', name: 'Main Window', width: 72, height: 84, quantity: 1, treatmentType: 'ripplefold', mountType: 'ceiling', liningType: 'blackout', hardwareType: 'track-ripplefold', motorization: 'somfy', notes: '' }
    ]}
  ])
  const [showPhotoModal, setShowPhotoModal] = useState(false)
  const [activeWindowId, setActiveWindowId] = useState<string | null>(null)
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null)
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<any>(null)
  const [photoModalMode, setPhotoModalMode] = useState<'window' | 'upholstery'>('window')
  const [activeUpholsteryId, setActiveUpholsteryId] = useState<string | null>(null)
  const [showCamera, setShowCamera] = useState(false)
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const file3DInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  // Inventory State
  const [inventoryTab, setInventoryTab] = useState<InventoryTab>('inventory')
  const [inventoryItems, setInventoryItems] = useState(INITIAL_INVENTORY)
  const [invSearch, setInvSearch] = useState('')
  const [invCategory, setInvCategory] = useState('all')
  const [invStatus, setInvStatus] = useState('all')
  const [selectedInvItem, setSelectedInvItem] = useState<InventoryItem | null>(null)
  const [editingInv, setEditingInv] = useState<InventoryItem | null>(null)
  const [viewer3DUrl, setViewer3DUrl] = useState<string | null>(null)
  const [viewer3DName, setViewer3DName] = useState('')

  const saveInvEdit = () => {
    if (!editingInv) return;
    const status = editingInv.quantity <= editingInv.minStock ? 'low' : editingInv.quantity <= editingInv.minStock * 1.5 ? 'medium' : 'good';
    const updated = { ...editingInv, status };
    setInventoryItems(prev => prev.map(i => i.id === updated.id ? updated : i));
    setSelectedInvItem(updated);
    setEditingInv(null);
  };

  // CRM State
  const [crmTab, setCrmTab] = useState<CrmTab>('customers')
  const [customers] = useState(INITIAL_CUSTOMERS)
  const [jobs] = useState(INITIAL_JOBS)
  const [crmSearch, setCrmSearch] = useState('')

  // Finance State
  const [financeTab, setFinanceTab] = useState<FinanceTab>('overview')
  const [invoices] = useState(INITIAL_INVOICES)

  // PDF State
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false)

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

  const calculateUpholsteryPrice = (u: UpholsteryItem): number => {
    const yards = Number(u.fabricYards) || 0
    const labor = UPHOLSTERY_PRICING.labor[u.laborType] || 62
    const fabric = UPHOLSTERY_PRICING.fabric[u.fabricType] || 22
    return Math.round(yards * (labor + fabric))
  }

  const calculateRoomTotal = (room: Room): number =>
    room.windows.reduce((sum, w) => sum + calculateWindowPrice(w), 0) +
    (room.upholstery || []).reduce((sum, u) => sum + calculateUpholsteryPrice(u), 0)
  const calculateGrandTotal = (): number => rooms.reduce((sum, r) => sum + calculateRoomTotal(r), 0)

  const handleDownloadPdf = async () => {
    setIsGeneratingPdf(true)
    try {
      const API = 'http://localhost:8000/api/v1'
      const lineItems = rooms.flatMap(room => [
        ...room.windows.map(w => ({
          description: `${room.name} - ${w.name} (${w.treatmentType}, ${w.liningType})`,
          quantity: w.quantity,
          unit: 'ea',
          rate: calculateWindowPrice(w) / (w.quantity || 1),
          amount: calculateWindowPrice(w),
          category: 'labor'
        })),
        ...(room.upholstery || []).map(u => ({
          description: `${room.name} - ${u.name} (${u.furnitureType}, ${u.laborType})`,
          quantity: 1,
          unit: 'ea',
          rate: calculateUpholsteryPrice(u),
          amount: calculateUpholsteryPrice(u),
          category: 'labor'
        }))
      ])
      const createRes = await fetch(`${API}/quotes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: 'Customer',
          line_items: lineItems,
          subtotal: calculateGrandTotal(),
          total: calculateGrandTotal(),
          business_name: 'Empire',
          terms: 'Payment due upon completion. 50% deposit required to begin work.',
          valid_days: 30,
        })
      })
      if (!createRes.ok) throw new Error('Failed to create quote')
      const { quote } = await createRes.json()
      const pdfRes = await fetch(`${API}/quotes/${quote.id}/pdf`, { method: 'POST' })
      if (!pdfRes.ok) throw new Error('Failed to generate PDF')
      const blob = await pdfRes.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${quote.quote_number}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('PDF generation failed:', err)
      alert('Failed to generate PDF. Check that the backend is running.')
    } finally {
      setIsGeneratingPdf(false)
    }
  }

  // Room/Window CRUD
  const addRoom = () => setRooms([...rooms, { id: genId(), name: `Room ${rooms.length + 1}`, expanded: true, windows: [], upholstery: [] }])
  const deleteRoom = (roomId: string) => { if (rooms.length > 1) setRooms(rooms.filter(r => r.id !== roomId)) }
  const toggleRoom = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, expanded: !r.expanded } : r))
  const updateRoomName = (roomId: string, name: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, name } : r))
  const addWindow = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: [...r.windows, { id: genId(), name: `Window ${r.windows.length + 1}`, width: 48, height: 60, quantity: 1, treatmentType: 'ripplefold', mountType: 'wall', liningType: 'standard', hardwareType: 'track-ripplefold', motorization: 'none', notes: '' }] } : r))
  const updateWindow = (roomId: string, windowId: string, updates: Partial<WindowItem>) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.map(w => w.id === windowId ? { ...w, ...updates } : w) } : r))
  const deleteWindow = (roomId: string, windowId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.filter(w => w.id !== windowId) } : r))
  const copyWindow = (roomId: string, windowId: string) => setRooms(rooms.map(r => { if (r.id === roomId) { const w = r.windows.find(w => w.id === windowId); if (w) return { ...r, windows: [...r.windows, { ...w, id: genId(), name: `${w.name} (Copy)` }] } } return r }))

  // Upholstery CRUD
  const addUpholstery = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, upholstery: [...(r.upholstery || []), { id: genId(), name: `Piece ${(r.upholstery || []).length + 1}`, furnitureType: 'sofa', style: '', width: 84, depth: 36, height: 34, cushionCount: 3, fabricYards: 14, fabricType: 'plain' as const, laborType: 'standard' as const, notes: '' }] } : r))
  const updateUpholstery = (roomId: string, uId: string, updates: Partial<UpholsteryItem>) => setRooms(rooms.map(r => r.id === roomId ? { ...r, upholstery: (r.upholstery || []).map(u => u.id === uId ? { ...u, ...updates } : u) } : r))
  const deleteUpholstery = (roomId: string, uId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, upholstery: (r.upholstery || []).filter(u => u.id !== uId) } : r))
  const copyUpholstery = (roomId: string, uId: string) => setRooms(rooms.map(r => { if (r.id === roomId) { const u = (r.upholstery || []).find(u => u.id === uId); if (u) return { ...r, upholstery: [...(r.upholstery || []), { ...u, id: genId(), name: `${u.name} (Copy)` }] } } return r }))

  // Photo/AI
  const openPhotoModal = (roomId: string, itemId: string, mode: 'window' | 'upholstery' = 'window') => {
    setActiveRoomId(roomId); setPhotoModalMode(mode); setShowPhotoModal(true); setUploadedImage(null); setAnalysisResult(null)
    if (mode === 'window') { setActiveWindowId(itemId); setActiveUpholsteryId(null) }
    else { setActiveUpholsteryId(itemId); setActiveWindowId(null) }
  }
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => { const file = e.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = (e) => { setUploadedImage(e.target?.result as string); setShowCamera(false) }; reader.readAsDataURL(file) } }
  const handle3DUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['glb', 'gltf', 'obj', 'ply'].includes(ext || '')) { alert('Please upload a 3D file (.glb, .gltf, .obj, .ply)'); return; }
    try {
      const fd = new FormData(); fd.append('file', file);
      const res = await fetch('http://localhost:8000/api/v1/files/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (data.status === 'success') {
        const fileUrl = `http://localhost:8000/api/v1/files/other/${data.filename}`;
        setViewer3DUrl(fileUrl);
        setViewer3DName(data.filename);
      } else { alert('Upload failed: ' + (data.detail || 'Unknown error')); }
    } catch (err) { alert('Upload failed — ensure the backend is running on port 8000'); }
    e.target.value = '';
  }
  const startCamera = async () => { try { const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } } }); setCameraStream(stream); setShowCamera(true); if (videoRef.current) videoRef.current.srcObject = stream } catch { alert('Unable to access camera.') } }
  const capturePhoto = () => { if (videoRef.current && canvasRef.current) { const v = videoRef.current, c = canvasRef.current; c.width = v.videoWidth; c.height = v.videoHeight; c.getContext('2d')?.drawImage(v, 0, 0); setUploadedImage(c.toDataURL('image/jpeg', 0.9)); stopCamera() } }
  const stopCamera = () => { cameraStream?.getTracks().forEach(t => t.stop()); setCameraStream(null); setShowCamera(false) }
  const closePhotoModal = () => { stopCamera(); setShowPhotoModal(false); setUploadedImage(null); setAnalysisResult(null) }

  // Compress image to reduce payload size and speed up API calls
  const compressImage = (dataUrl: string, maxWidth = 1600, quality = 0.8): Promise<string> => {
    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        let w = img.width, h = img.height
        if (w > maxWidth) { h = (h * maxWidth) / w; w = maxWidth }
        canvas.width = w; canvas.height = h
        canvas.getContext('2d')?.drawImage(img, 0, 0, w, h)
        resolve(canvas.toDataURL('image/jpeg', quality))
      }
      img.src = dataUrl
    })
  }

  const analyzeImage = async () => {
    if (!uploadedImage) return
    setIsAnalyzing(true)
    try {
      // Compress image to speed up transfer
      const compressed = await compressImage(uploadedImage)
      const endpoint = photoModalMode === 'upholstery' ? '/api/upholstery' : '/api/measure'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: compressed }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Analysis failed')

      if (photoModalMode === 'upholstery') {
        setAnalysisResult({
          mode: 'upholstery',
          confidence: Math.min(100, Math.max(0, data.confidence || 70)),
          furnitureType: data.furniture_type || 'Unknown',
          style: data.style || '',
          dimensions: data.estimated_dimensions || { width: 0, depth: 0, height: 0 },
          cushions: data.cushion_count || { seat: 0, back: 0, throw_pillows: 0 },
          fabricYardsPlain: data.fabric_yards_plain || 0,
          fabricYardsPatterned: data.fabric_yards_patterned || 0,
          hasWelting: data.has_welting || false,
          hasTufting: data.has_tufting || false,
          hasChanneling: data.has_channeling || false,
          hasSkirt: data.has_skirt || false,
          hasNailhead: data.has_nailhead || false,
          suggestedLaborType: data.suggested_labor_type || 'standard',
          laborCostLow: data.estimated_labor_cost_low || 0,
          laborCostHigh: data.estimated_labor_cost_high || 0,
          newFoamRecommended: data.new_foam_recommended || false,
          notes: data.notes || '',
          questions: data.questions || [],
        })
      } else {
        const w = Math.round(data.width_inches || 36)
        const h = Math.round(data.height_inches || 48)
        const type = data.window_type || 'Standard'
        const confidence = Math.min(100, Math.max(0, data.confidence || 70))
        const suggestions: string[] = data.treatment_suggestions || []
        const notes = data.notes || ''
        const refs: string[] = data.reference_objects_used || []
        setAnalysisResult({
          mode: 'window', confidence, suggestedWidth: w, suggestedHeight: h, windowType: type,
          recommendations: [
            ...(refs.length > 0 ? [`Scale references: ${refs.join(', ')}`] : []),
            ...(suggestions.length > 0 ? suggestions : [`${type} - recommend ${w > 60 ? 'ripplefold drapes' : 'roman shades'}`, h > 72 ? 'Ceiling mount for dramatic effect' : 'Wall mount recommended']),
            ...(notes ? [notes] : []),
          ],
        })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Analysis failed'
      alert('AI analysis error: ' + msg)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const applyAnalysis = () => {
    if (!analysisResult || !activeRoomId) return
    if (analysisResult.mode === 'upholstery' && activeUpholsteryId) {
      const suggestedLabor = analysisResult.hasTufting ? 'tufted' : analysisResult.hasChanneling ? 'channeled' : 'standard'
      updateUpholstery(activeRoomId, activeUpholsteryId, {
        furnitureType: analysisResult.furnitureType, style: analysisResult.style,
        width: analysisResult.dimensions?.width || 0, depth: analysisResult.dimensions?.depth || 0, height: analysisResult.dimensions?.height || 0,
        cushionCount: (analysisResult.cushions?.seat || 0) + (analysisResult.cushions?.back || 0),
        fabricYards: analysisResult.fabricYardsPlain || 0,
        laborType: suggestedLabor as UpholsteryItem['laborType'],
        imageUrl: uploadedImage || undefined, aiAnalysis: analysisResult,
      })
      closePhotoModal()
    } else if (analysisResult.mode === 'window' && activeWindowId) {
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
    { id: 'quotes' as const, label: 'Quote Builder', icon: Calculator, badge: rooms.reduce((s, r) => s + r.windows.length + (r.upholstery || []).length, 0) },
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
                <button
                  onClick={handleDownloadPdf}
                  disabled={isGeneratingPdf}
                  className="flex items-center gap-2 bg-[#1a1a2e] hover:bg-[#252540] text-white px-4 py-2 rounded-lg font-semibold text-sm transition border border-white/10 disabled:opacity-50"
                >
                  {isGeneratingPdf ? (
                    <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</>
                  ) : (
                    <><Download className="w-3.5 h-3.5" /> Download PDF</>
                  )}
                </button>
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
                  <h3 className="font-semibold text-sm flex items-center gap-2">AI Window & Upholstery Analysis <span className="text-[10px] bg-purple-500/30 text-purple-300 px-1.5 py-0.5 rounded-full">BETA</span></h3>
                  <p className="text-xs text-gray-400">Upload photo for AI-powered window measurement or upholstery estimation with DC-area pricing</p>
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
                      <span className="text-xs text-gray-500">({room.windows.length} windows{(room.upholstery || []).length > 0 ? `, ${(room.upholstery || []).length} upholstery` : ''})</span>
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

                      {/* Upholstery Items */}
                      {(room.upholstery || []).map(u => (
                        <div key={u.id} className={`bg-[#1a1a2e] rounded-lg p-4 border ${u.aiAnalysis ? 'border-amber-500/30' : 'border-white/[0.04]'}`}>
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                              <input type="text" value={u.name} onChange={(e) => updateUpholstery(room.id, u.id, { name: e.target.value })} className="bg-transparent font-medium text-sm focus:outline-none" />
                              <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded-full">UPHOLSTERY</span>
                              {u.aiAnalysis && <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded-full flex items-center gap-1"><Sparkles className="w-2.5 h-2.5" /> AI {u.aiAnalysis.confidence}%</span>}
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className="text-sm font-bold text-green-400">${calculateUpholsteryPrice(u).toLocaleString()}</span>
                              <button onClick={() => copyUpholstery(room.id, u.id)} className="p-1.5 text-gray-500 hover:text-white hover:bg-white/[0.06] rounded"><Copy className="w-3.5 h-3.5" /></button>
                              <button onClick={() => deleteUpholstery(room.id, u.id)} className="p-1.5 text-gray-500 hover:text-red-400 rounded"><Trash2 className="w-3.5 h-3.5" /></button>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">AI Estimate</label>
                              <button onClick={() => openPhotoModal(room.id, u.id, 'upholstery')} className="w-full h-9 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg flex items-center justify-center gap-1.5 text-xs text-amber-300 transition">
                                <Camera className="w-3.5 h-3.5" /> Photo
                              </button>
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">Type</label>
                              <select value={u.furnitureType} onChange={(e) => updateUpholstery(room.id, u.id, { furnitureType: e.target.value })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-2 text-sm focus:border-[#C9A84C] outline-none">
                                {['sofa','loveseat','chair','club-chair','wing-chair','recliner','ottoman','bench','chaise','daybed','sectional','dining-chair','stool','headboard'].map(t => <option key={t} value={t}>{t.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')}</option>)}
                              </select>
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">Fabric Yards</label>
                              <input type="number" value={u.fabricYards} onChange={(e) => updateUpholstery(room.id, u.id, { fabricYards: Number(e.target.value) })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-3 text-sm focus:border-[#C9A84C] outline-none" />
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">Cushions</label>
                              <input type="number" value={u.cushionCount} onChange={(e) => updateUpholstery(room.id, u.id, { cushionCount: Number(e.target.value) })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-3 text-sm focus:border-[#C9A84C] outline-none" />
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">Fabric</label>
                              <select value={u.fabricType} onChange={(e) => updateUpholstery(room.id, u.id, { fabricType: e.target.value as UpholsteryItem['fabricType'] })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-2 text-sm focus:border-[#C9A84C] outline-none">
                                <option value="plain">Plain $22/yd</option>
                                <option value="patterned">Patterned $50/yd</option>
                                <option value="leather">Leather $110/yd</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">Labor</label>
                              <select value={u.laborType} onChange={(e) => updateUpholstery(room.id, u.id, { laborType: e.target.value as UpholsteryItem['laborType'] })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-2 text-sm focus:border-[#C9A84C] outline-none">
                                <option value="standard">Standard $62/yd</option>
                                <option value="tufted">Tufted $78/yd</option>
                                <option value="channeled">Channeled $72/yd</option>
                                <option value="leather">Leather $100/yd</option>
                              </select>
                            </div>
                            {[
                              { label: 'W (in)', value: u.width, key: 'width' },
                              { label: 'D (in)', value: u.depth, key: 'depth' },
                              { label: 'H (in)', value: u.height, key: 'height' },
                            ].map(f => (
                              <div key={f.key}>
                                <label className="block text-[10px] text-gray-500 mb-1">{f.label}</label>
                                <input type="number" value={f.value} onChange={(e) => updateUpholstery(room.id, u.id, { [f.key]: Number(e.target.value) })} className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-3 text-sm focus:border-[#C9A84C] outline-none" />
                              </div>
                            ))}
                            <div>
                              <label className="block text-[10px] text-gray-500 mb-1">Style</label>
                              <input type="text" value={u.style} onChange={(e) => updateUpholstery(room.id, u.id, { style: e.target.value })} placeholder="e.g. Chesterfield" className="w-full h-9 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-3 text-sm focus:border-[#C9A84C] outline-none" />
                            </div>
                          </div>

                          {u.aiAnalysis && (
                            <div className="mt-3 p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                              <div className="flex items-center gap-2 mb-2">
                                <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
                                <span className="text-xs font-medium text-amber-300">AI: {u.aiAnalysis.furnitureType} — {u.aiAnalysis.style}</span>
                              </div>
                              <div className="grid grid-cols-2 gap-1.5 mb-2">
                                <div className="text-[11px] text-gray-400">Fabric: {u.aiAnalysis.fabricYardsPlain} yd (plain) / {u.aiAnalysis.fabricYardsPatterned} yd (patterned)</div>
                                <div className="text-[11px] text-gray-400">Cushions: {u.aiAnalysis.cushions.seat}S + {u.aiAnalysis.cushions.back}B + {u.aiAnalysis.cushions.throw_pillows}P</div>
                                <div className="text-[11px] text-gray-400">Labor est: ${u.aiAnalysis.laborCostLow} — ${u.aiAnalysis.laborCostHigh}</div>
                                <div className="text-[11px] text-gray-400">
                                  {[u.aiAnalysis.hasWelting && 'Welting', u.aiAnalysis.hasTufting && 'Tufting', u.aiAnalysis.hasChanneling && 'Channeling', u.aiAnalysis.hasSkirt && 'Skirt', u.aiAnalysis.hasNailhead && 'Nailhead'].filter(Boolean).join(', ') || 'No special details'}
                                </div>
                              </div>
                              {u.aiAnalysis.newFoamRecommended && (
                                <p className="text-[11px] text-amber-400 mb-2">New foam recommended ($45-85/seat)</p>
                              )}
                              {u.aiAnalysis.questions.length > 0 && (
                                <div className="bg-amber-500/5 rounded-lg p-2">
                                  <p className="text-[10px] font-medium text-amber-300 mb-1">Questions for customer:</p>
                                  {u.aiAnalysis.questions.map((q, i) => (
                                    <p key={i} className="text-[11px] text-gray-400 flex items-start gap-1.5 mb-1 last:mb-0">
                                      <span className="text-amber-400 flex-shrink-0">?</span>{q}
                                    </p>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          <input type="text" value={u.notes} onChange={(e) => updateUpholstery(room.id, u.id, { notes: e.target.value })} placeholder="Notes..." className="w-full mt-3 bg-[#0c0c18] border border-white/[0.08] rounded-lg px-3 py-2 text-xs focus:border-[#C9A84C] outline-none" />
                        </div>
                      ))}

                      <div className="flex gap-2">
                        <button onClick={() => addWindow(room.id)} className="flex-1 py-2.5 border border-dashed border-white/10 hover:border-purple-500/40 rounded-lg text-gray-500 hover:text-purple-400 flex items-center justify-center gap-2 text-sm transition">
                          <Plus className="w-4 h-4" /> Add Window
                        </button>
                        <button onClick={() => addUpholstery(room.id)} className="flex-1 py-2.5 border border-dashed border-white/10 hover:border-amber-500/40 rounded-lg text-gray-500 hover:text-amber-400 flex items-center justify-center gap-2 text-sm transition">
                          <Plus className="w-4 h-4" /> Add Upholstery
                        </button>
                      </div>
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
                    <span className="text-gray-400">{r.name} ({r.windows.length} win{(r.upholstery || []).length > 0 ? `, ${(r.upholstery || []).length} uph` : ''})</span>
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
            <div className={`px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between bg-gradient-to-r ${photoModalMode === 'upholstery' ? 'from-amber-500/10 to-orange-500/10' : 'from-purple-500/10 to-pink-500/10'}`}>
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${photoModalMode === 'upholstery' ? 'from-amber-500 to-orange-600' : 'from-purple-500 to-pink-600'} flex items-center justify-center`}><Brain className="w-4 h-4 text-white" /></div>
                <div><h2 className="font-bold text-sm">{photoModalMode === 'upholstery' ? 'AI Upholstery Estimation' : 'AI Window Analysis'}</h2><p className="text-[10px] text-gray-400">{photoModalMode === 'upholstery' ? 'Photo • Yardage • DC Pricing' : 'Photo • Polycam 3D • Manual'}</p></div>
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
                  <button onClick={() => file3DInputRef.current?.click()} className="flex flex-col items-center gap-2 p-6 bg-[#1a1a2e] hover:bg-[#252540] border border-dashed border-white/10 hover:border-purple-500/50 rounded-xl group transition">
                    <Box className="w-8 h-8 text-gray-500 group-hover:text-purple-400" /><span className="text-xs">Polycam 3D</span>
                  </button>
                  <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
                  <input ref={file3DInputRef} type="file" accept=".glb,.gltf,.obj,.ply" onChange={handle3DUpload} className="hidden" />
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

              {analysisResult && analysisResult.mode === 'window' && (
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

              {analysisResult && analysisResult.mode === 'upholstery' && (
                <div className="bg-[#1a1a2e] rounded-xl p-4 mb-4 border border-amber-500/20">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-bold flex items-center gap-2"><Sparkles className="w-4 h-4 text-amber-400" /> Upholstery Estimate</h3>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">{analysisResult.confidence}%</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <div className="bg-[#0c0c18] rounded-lg p-3 text-center">
                      <p className="text-lg font-bold">{analysisResult.fabricYardsPlain}</p>
                      <p className="text-[10px] text-gray-500">Yards (plain)</p>
                    </div>
                    <div className="bg-[#0c0c18] rounded-lg p-3 text-center">
                      <p className="text-lg font-bold">{(analysisResult.cushions?.seat || 0) + (analysisResult.cushions?.back || 0)}</p>
                      <p className="text-[10px] text-gray-500">Cushions</p>
                    </div>
                    <div className="bg-[#0c0c18] rounded-lg p-3 text-center">
                      <p className="text-lg font-bold text-amber-400">${analysisResult.laborCostLow}-{analysisResult.laborCostHigh}</p>
                      <p className="text-[10px] text-gray-500">Labor Est.</p>
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mb-1">{analysisResult.furnitureType} — <span className="text-white">{analysisResult.style}</span></p>
                  <p className="text-xs text-gray-400 mb-2">Dimensions: {analysisResult.dimensions?.width}" W x {analysisResult.dimensions?.depth}" D x {analysisResult.dimensions?.height}" H</p>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {[analysisResult.hasWelting && 'Welting', analysisResult.hasTufting && 'Tufting', analysisResult.hasChanneling && 'Channeling', analysisResult.hasSkirt && 'Skirt', analysisResult.hasNailhead && 'Nailhead', analysisResult.newFoamRecommended && 'New Foam Rec.'].filter(Boolean).map((tag, i) => (
                      <span key={i} className="text-[10px] bg-amber-500/15 text-amber-300 px-1.5 py-0.5 rounded">{tag}</span>
                    ))}
                  </div>
                  {analysisResult.notes && <p className="text-[11px] text-gray-400 mb-2">{analysisResult.notes}</p>}
                  {analysisResult.questions?.length > 0 && (
                    <div className="bg-amber-500/5 rounded-lg p-2.5">
                      <p className="text-[10px] font-medium text-amber-300 mb-1">Ask the customer:</p>
                      {analysisResult.questions.map((q: string, i: number) => (
                        <p key={i} className="text-[11px] text-gray-400 flex items-start gap-1.5 mb-1 last:mb-0"><span className="text-amber-400 flex-shrink-0">?</span>{q}</p>
                      ))}
                    </div>
                  )}
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

      {/* ═══ INVENTORY DETAIL / EDIT MODAL ═══ */}
      {selectedInvItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70" onClick={() => { setSelectedInvItem(null); setEditingInv(null); }} />
          <div className="relative bg-[#12121e] rounded-2xl border border-white/[0.08] w-full max-w-md overflow-hidden">
            <div className="px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between">
              <div>
                <p className="font-mono text-[10px] text-gray-500">{selectedInvItem.sku}</p>
                {editingInv ? (
                  <input value={editingInv.name} onChange={e => setEditingInv({ ...editingInv, name: e.target.value })}
                    className="font-bold text-sm bg-[#1a1a2e] border border-white/10 rounded px-2 py-0.5 mt-0.5 w-full outline-none focus:border-[#C9A84C]" />
                ) : (
                  <h2 className="font-bold text-sm">{selectedInvItem.name}</h2>
                )}
              </div>
              <button onClick={() => { setSelectedInvItem(null); setEditingInv(null); }} className="p-1 hover:bg-white/[0.06] rounded"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-5 space-y-3">
              {editingInv ? (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="text-[10px] text-gray-500">Quantity</label><input type="number" value={editingInv.quantity} onChange={e => setEditingInv({ ...editingInv, quantity: Number(e.target.value) })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                    <div><label className="text-[10px] text-gray-500">Retail Price ($)</label><input type="number" step="0.01" value={editingInv.price} onChange={e => setEditingInv({ ...editingInv, price: Number(e.target.value) })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="text-[10px] text-gray-500">Cost ($)</label><input type="number" step="0.01" value={editingInv.cost} onChange={e => setEditingInv({ ...editingInv, cost: Number(e.target.value) })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                    <div><label className="text-[10px] text-gray-500">Unit</label><input value={editingInv.unit} onChange={e => setEditingInv({ ...editingInv, unit: e.target.value })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="text-[10px] text-gray-500">Min Stock</label><input type="number" value={editingInv.minStock} onChange={e => setEditingInv({ ...editingInv, minStock: Number(e.target.value) })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                    <div><label className="text-[10px] text-gray-500">Max Stock</label><input type="number" value={editingInv.maxStock} onChange={e => setEditingInv({ ...editingInv, maxStock: Number(e.target.value) })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><label className="text-[10px] text-gray-500">Vendor</label><input value={editingInv.vendor} onChange={e => setEditingInv({ ...editingInv, vendor: e.target.value })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                    <div><label className="text-[10px] text-gray-500">Location</label><input value={editingInv.location} onChange={e => setEditingInv({ ...editingInv, location: e.target.value })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]" /></div>
                  </div>
                  <div><label className="text-[10px] text-gray-500">Category</label>
                    <select value={editingInv.category} onChange={e => setEditingInv({ ...editingInv, category: e.target.value })} className="w-full bg-[#1a1a2e] border border-white/10 rounded px-2 py-1.5 text-sm outline-none focus:border-[#C9A84C]">
                      {['fabrics','linings','hardware','motors','trim','supplies'].map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                    </select>
                  </div>
                </>
              ) : (
                <>
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
                </>
              )}
            </div>
            <div className="px-5 py-3 border-t border-white/[0.06] flex gap-2">
              {editingInv ? (
                <>
                  <button onClick={() => setEditingInv(null)} className="flex-1 bg-[#1a1a2e] hover:bg-[#252540] py-2.5 rounded-lg text-xs flex items-center justify-center gap-1.5">Cancel</button>
                  <button onClick={saveInvEdit} className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 rounded-lg text-xs flex items-center justify-center gap-1.5"><Check className="w-3 h-3" /> Save</button>
                </>
              ) : (
                <>
                  <button onClick={() => setEditingInv({ ...selectedInvItem })} className="flex-1 bg-[#1a1a2e] hover:bg-[#252540] py-2.5 rounded-lg text-xs flex items-center justify-center gap-1.5"><Edit className="w-3 h-3" /> Edit</button>
                  <button className="flex-1 bg-[#C9A84C] hover:bg-[#B8973F] text-[#0D0D0D] font-semibold py-2.5 rounded-lg text-xs flex items-center justify-center gap-1.5"><ShoppingCart className="w-3 h-3" /> Reorder</button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══ 3D VIEWER MODAL (model-viewer web component) ═══ */}
      {viewer3DUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(5,5,13,0.95)' }}>
          <div className="w-full h-full max-w-6xl max-h-[95vh] mx-4 my-2 flex flex-col rounded-2xl overflow-hidden"
            style={{ background: '#0a0a1a', border: '1px solid rgba(255,255,255,0.08)' }}>
            {/* Header */}
            <div className="shrink-0 px-6 py-3 flex items-center justify-between"
              style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.12), rgba(212,175,55,0.12))', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
              <div className="flex items-center gap-3">
                <Ruler className="w-4 h-4 text-purple-400" />
                <div>
                  <h1 className="text-sm font-bold text-purple-400">3D Scan Viewer</h1>
                  <p className="text-[10px] text-gray-500">{viewer3DName}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(212,175,55,0.15)', color: '#C9A84C' }}>
                  Orbit: drag &bull; Zoom: scroll &bull; Pan: right-drag
                </span>
                <button onClick={() => setViewer3DUrl(null)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-red-500/15 hover:text-red-400 text-gray-500 transition"
                  style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            {/* Viewer */}
            <div className="flex-1 relative bg-[#0a0a14]">
              {/* eslint-disable-next-line @next/next/no-sync-scripts */}
              <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js"></script>
              {/* @ts-expect-error model-viewer is a web component */}
              <model-viewer
                src={viewer3DUrl}
                alt={viewer3DName}
                camera-controls
                touch-action="pan-y"
                auto-rotate
                shadow-intensity="1"
                environment-image="neutral"
                style={{ width: '100%', height: '100%', background: '#0a0a14' }}
              />
            </div>
            {/* Footer */}
            <div className="shrink-0 px-6 py-3 flex items-center justify-between"
              style={{ borderTop: '1px solid rgba(255,255,255,0.06)', background: '#0e0e1a' }}>
              <div className="flex items-center gap-2">
                <a href={viewer3DUrl} download={viewer3DName}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 bg-[#1a1a2e] hover:bg-[#252540] transition"
                  style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
                  <Download className="w-3.5 h-3.5" /> Download
                </a>
                <button onClick={() => window.open(`http://localhost:3009?view3d=${encodeURIComponent(viewer3DUrl)}&name=${encodeURIComponent(viewer3DName)}`, '_blank')}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
                  style={{ background: 'rgba(139,92,246,0.15)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.3)' }}>
                  <Ruler className="w-3.5 h-3.5" /> Open Measure Tool
                </button>
              </div>
              <span className="text-[10px] font-mono text-gray-600">3D Viewer</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
