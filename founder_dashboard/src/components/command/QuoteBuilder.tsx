'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { API_URL } from '@/lib/api';
import {
  Plus, Trash2, Copy, ChevronDown, ChevronUp, Camera, Upload, X,
  Sparkles, Check, Loader2, Send, Download, Printer,
  Brain, Eye, Lightbulb, Calculator, Ruler, Palette, PenTool,
  Share2, Mail, Link, ExternalLink, Scissors, ImageIcon, Clock, FileText,
} from 'lucide-react';
import { FABRIC_GRADES, BASE_PRICES, type TreatmentType, type FabricGrade } from '@/lib/deskData';
import dynamic from 'next/dynamic';
const Viewer3D = dynamic(() => import('./Viewer3D'), { ssr: false });

// ═══════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════

interface WindowItem {
  id: string; name: string; width: number; height: number; quantity: number;
  treatmentType: string; mountType: string; liningType: string;
  hardwareType: string; hardwareColor: string; motorization: string; notes: string;
  fabricGrade: FabricGrade; fullness: number; laborRate: number;
  drawDirection: string; fabricColor: string;
  sourcePhoto?: string; // base64 photo used for AI analysis
  photos?: string[]; // additional reference photos
  aiAnalysis?: { confidence: number; suggestedWidth: number; suggestedHeight: number; windowType: string; recommendations: string[] };
}

interface UpholsteryItem {
  id: string; name: string; furnitureType: string; fabricYards: number;
  fabricType: 'plain' | 'patterned' | 'leather';
  laborType: 'standard' | 'tufted' | 'channeled' | 'leather';
  cushionCount: number; width: number; depth: number; height: number; notes: string;
  aiAnalysis?: {
    confidence: number; furnitureType: string; style: string;
    fabricYardsPlain: number; fabricYardsPatterned: number;
    cushions: { seat: number; back: number; throw_pillows: number };
    hasWelting: boolean; hasTufting: boolean; suggestedLaborType: string;
    laborCostLow: number; laborCostHigh: number; newFoamRecommended: boolean;
    questions: string[];
    generated_image?: string | null;
  };
  sourcePhoto?: string;
  photos?: string[]; // additional reference photos
}

interface Room {
  id: string; name: string; windows: WindowItem[]; upholstery: UpholsteryItem[]; expanded: boolean;
}

// ═══════════════════════════════════════════════════════
// PRICING ENGINE
// ═══════════════════════════════════════════════════════

const PRICING = {
  base: { 'ripplefold': 45, 'pinch-pleat': 38, 'rod-pocket': 28, 'grommet': 32, 'roman-shade': 55, 'roller-shade': 42 } as Record<string, number>,
  lining: { 'unlined': 0, 'standard': 8, 'blackout': 15, 'thermal': 12, 'interlining': 18 } as Record<string, number>,
  hardware: { 'none': 0, 'rod-standard': 45, 'rod-decorative': 85, 'track-basic': 65, 'track-ripplefold': 95 } as Record<string, number>,
  motor: { 'none': 0, 'somfy': 285, 'lutron': 425, 'generic': 185 } as Record<string, number>,
};

const UPHOLSTERY_PRICING = {
  labor: { 'standard': 72, 'tufted': 90, 'channeled': 82, 'leather': 115 } as Record<string, number>,
  fabric: { 'plain': 28, 'patterned': 55, 'leather': 125 } as Record<string, number>,
};

// Accurate defaults per furniture type (DC-area high-end workroom rates)
const FURNITURE_DEFAULTS: Record<string, { yards: number; cushions: number; width: number; depth: number; height: number }> = {
  'sofa': { yards: 14, cushions: 3, width: 84, depth: 36, height: 34 },
  'loveseat': { yards: 10, cushions: 2, width: 60, depth: 36, height: 34 },
  'chair': { yards: 6, cushions: 1, width: 32, depth: 34, height: 34 },
  'club-chair': { yards: 7, cushions: 1, width: 36, depth: 36, height: 32 },
  'wing-chair': { yards: 8, cushions: 1, width: 32, depth: 34, height: 42 },
  'recliner': { yards: 9, cushions: 1, width: 36, depth: 38, height: 40 },
  'ottoman': { yards: 3, cushions: 0, width: 30, depth: 24, height: 18 },
  'bench': { yards: 4, cushions: 0, width: 48, depth: 18, height: 20 },
  'chaise': { yards: 9, cushions: 1, width: 68, depth: 30, height: 34 },
  'headboard': { yards: 5, cushions: 0, width: 62, depth: 4, height: 48 },
  'throw-pillow': { yards: 1, cushions: 0, width: 20, depth: 20, height: 6 },
  'bolster-pillow': { yards: 1.5, cushions: 0, width: 36, depth: 8, height: 8 },
  'lumbar-pillow': { yards: 0.75, cushions: 0, width: 20, depth: 12, height: 5 },
  'euro-sham': { yards: 1.5, cushions: 0, width: 26, depth: 26, height: 4 },
};

const STYLE_PRESETS = [
  { id: 'farmhouse', label: 'Farmhouse', keywords: 'rustic linen, natural wood hardware, relaxed puddled draping, warm whites and cream' },
  { id: 'modern', label: 'Modern Minimal', keywords: 'clean roller shades, neutral palette, hidden tracks, solid colors, no pattern' },
  { id: 'glam', label: 'Hollywood Glam', keywords: 'velvet drapes, crystal finials, floor-to-ceiling panels, jewel tones, silk' },
  { id: 'coastal', label: 'Coastal', keywords: 'light linen sheers, white and blue palette, bamboo shades, natural fiber' },
  { id: 'bohemian', label: 'Bohemian', keywords: 'layered textiles, macrame accents, warm earth tones, tassels and fringe' },
  { id: 'traditional', label: 'Traditional', keywords: 'pinch pleat, damask brocade, swags and jabots, ornate brass rods' },
  { id: 'midcentury', label: 'Mid-Century', keywords: 'retro geometric prints, warm teak rods, simple grommet panels' },
  { id: 'industrial', label: 'Industrial', keywords: 'iron pipe rods, raw linen, matte black hardware, exposed mechanism' },
  { id: 'scandinavian', label: 'Scandinavian', keywords: 'white sheers, light birch, minimalist rod, hygge warmth' },
  { id: 'artdeco', label: 'Art Deco', keywords: 'geometric patterns, gold chrome hardware, luxe velvet, bold contrast' },
  { id: 'transitional', label: 'Transitional', keywords: 'blend of classic and modern, neutral textures, understated elegance' },
  { id: 'maximalist', label: 'Maximalist', keywords: 'bold prints, mixed patterns, layered treatments, statement hardware' },
];

const TREATMENT_OPTIONS = [['ripplefold','Ripplefold'],['pinch-pleat','Pinch Pleat'],['rod-pocket','Rod Pocket'],['grommet','Grommet'],['roman-shade','Roman Shade'],['roller-shade','Roller Shade']];
const LINING_OPTIONS = [['unlined','Unlined'],['standard','Standard'],['blackout','Blackout'],['thermal','Thermal'],['interlining','Interlining']];
const HARDWARE_OPTIONS = [['none','None'],['rod-standard','Rod Std'],['rod-decorative','Rod Deco'],['track-basic','Track Basic'],['track-ripplefold','Track Ripple']];
const MOTOR_OPTIONS = [['none','None'],['somfy','Somfy $285'],['lutron','Lutron $425'],['generic','Generic $185']];
const MOUNT_OPTIONS = [['wall','Wall'],['ceiling','Ceiling'],['inside','Inside']];
const DRAW_OPTIONS = [['center','Center (split)'],['left','Left Draw'],['right','Right Draw'],['one-way-l','One-Way Left'],['one-way-r','One-Way Right'],['stationary','Stationary']];
const HW_COLOR_OPTIONS = [['brushed-nickel','Brushed Nickel'],['matte-black','Matte Black'],['oil-rubbed-bronze','Oil-Rubbed Bronze'],['polished-chrome','Chrome'],['brass','Brass/Gold'],['satin-silver','Satin Silver'],['white','White'],['pewter','Pewter']];
const FURNITURE_TYPES = ['sofa','loveseat','chair','club-chair','wing-chair','recliner','ottoman','bench','chaise','headboard','throw-pillow','bolster-pillow','lumbar-pillow','euro-sham'];

const genId = () => Math.random().toString(36).substr(2, 9);

// Map QuoteBuilder treatment types → deskData TreatmentType for yardage calc
const TREATMENT_MAP: Record<string, TreatmentType> = {
  'ripplefold': 'drapes', 'pinch-pleat': 'drapes', 'rod-pocket': 'drapes',
  'grommet': 'drapes', 'roman-shade': 'shades', 'roller-shade': 'blinds',
};

interface YardageCalc {
  panelsNeeded: number; yardagePerWindow: number; wasteYardage: number; totalYardage: number;
  materialsTotal: number; laborTotal: number; hardwareTotal: number; subtotal: number; tax: number; total: number;
}

const calcYardage = (w: WindowItem): YardageCalc => {
  const treatment = TREATMENT_MAP[w.treatmentType] || 'drapes';
  const base = BASE_PRICES[treatment];
  const gradeInfo = FABRIC_GRADES.find(g => g.grade === w.fabricGrade) || FABRIC_GRADES[0];
  const fullness = w.fullness || 2.5;
  const laborRate = w.laborRate || 65;

  const widthInches = w.width * fullness;
  const heightInches = w.height + 16; // allowance
  const panelsNeeded = Math.ceil(widthInches / 54);
  const yardagePerWindow = (heightInches / 36) * panelsNeeded;
  const wasteYardage = yardagePerWindow * 0.15;
  const totalYardage = (yardagePerWindow + wasteYardage) * (w.quantity || 1);

  const materialsTotal = base.material * gradeInfo.multiplier * (w.quantity || 1);
  const laborTotal = base.labor * (laborRate / 65) * (w.quantity || 1);
  const hardwareTotal = (base.hardware + (PRICING.hardware[w.hardwareType] || 0) + (PRICING.motor[w.motorization] || 0)) * (w.quantity || 1);
  const liningAdd = (PRICING.lining[w.liningType] || 0) * ((w.width * w.height) / 144) * (w.quantity || 1);
  const subtotal = materialsTotal + laborTotal + hardwareTotal + liningAdd;
  const tax = subtotal * 0.0825;
  const total = subtotal + tax;

  return {
    panelsNeeded, yardagePerWindow: Math.ceil(yardagePerWindow * 10) / 10,
    wasteYardage: Math.ceil(wasteYardage * 10) / 10, totalYardage: Math.ceil(totalYardage * 10) / 10,
    materialsTotal: Math.round(materialsTotal), laborTotal: Math.round(laborTotal + liningAdd),
    hardwareTotal: Math.round(hardwareTotal), subtotal: Math.round(subtotal),
    tax: Math.round(tax), total: Math.round(total),
  };
};

const calcWindowPrice = (w: WindowItem): number => calcYardage(w).total;

const calcUpholsteryPrice = (u: UpholsteryItem): number => {
  const yards = u.fabricYards || 0;
  const laborPerYd = UPHOLSTERY_PRICING.labor[u.laborType] || 72;
  const fabricPerYd = UPHOLSTERY_PRICING.fabric[u.fabricType] || 28;
  const isPillow = /pillow|sham|cushion/i.test(u.furnitureType);
  // Pillows: flat rate per piece. Furniture: per-yard pricing + base labor fee.
  if (isPillow) {
    const baseRate = u.fabricType === 'leather' ? 185 : u.fabricType === 'patterned' ? 95 : 65;
    return Math.round(baseRate + yards * fabricPerYd);
  }
  // Base labor fee by complexity (minimum charge)
  const baseFee = u.laborType === 'leather' ? 200 : u.laborType === 'tufted' ? 150 : u.laborType === 'channeled' ? 125 : 85;
  return Math.round(baseFee + yards * (laborPerYd + fabricPerYd));
};

const calcRoomTotal = (room: Room): number =>
  room.windows.reduce((s, w) => s + calcWindowPrice(w), 0) +
  room.upholstery.reduce((s, u) => s + calcUpholsteryPrice(u), 0);

// ═══════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════

interface Props {
  onClose: () => void;
  initialCustomer?: { name: string; email: string; phone: string; address: string; project: string };
  initialRooms?: any[];
  initialMaxAnalysis?: string;
}

function buildInitialRooms(incoming?: any[]): Room[] {
  if (!incoming || incoming.length === 0) {
    return [{ id: genId(), name: 'Room 1', expanded: true, windows: [], upholstery: [] }];
  }
  return incoming.map(r => ({
    id: genId(),
    name: r.name || 'Room',
    expanded: true,
    windows: (r.windows || []).map((w: any) => ({
      id: genId(),
      name: w.name || 'Window',
      width: w.width || 48,
      height: w.height || 60,
      quantity: w.quantity || 1,
      treatmentType: w.treatmentType || 'ripplefold',
      mountType: w.mountType || 'wall',
      liningType: w.liningType || 'standard',
      hardwareType: w.hardwareType || 'track-ripplefold',
      motorization: w.motorization || 'none',
      notes: w.notes || '',
      fabricGrade: (w.fabricGrade || 'Standard') as FabricGrade,
      fullness: w.fullness || 2.5,
      laborRate: w.laborRate || 65,
      sourcePhoto: w.sourcePhoto || undefined,
      photos: w.photos || [],
    })),
    upholstery: (r.upholstery || []).map((u: any) => ({
      id: genId(),
      name: u.name || 'Piece',
      furnitureType: u.furnitureType || 'sofa',
      fabricYards: u.fabricYards || 14,
      fabricType: (u.fabricType || 'plain') as 'plain' | 'patterned' | 'leather',
      laborType: (u.laborType || 'standard') as 'standard' | 'tufted' | 'channeled' | 'leather',
      cushionCount: u.cushionCount || 3,
      width: u.width || 84,
      depth: u.depth || 36,
      height: u.height || 34,
      notes: u.notes || '',
      photos: u.photos || [],
    })),
  }));
}

export default function QuoteBuilder({ onClose, initialCustomer, initialRooms, initialMaxAnalysis }: Props) {
  // Customer
  const [customer, setCustomer] = useState({
    name: initialCustomer?.name || '',
    email: initialCustomer?.email || '',
    phone: initialCustomer?.phone || '',
    address: initialCustomer?.address || '',
  });
  const [projectName, setProjectName] = useState(initialCustomer?.project || '');

  // Rooms
  const [rooms, setRooms] = useState<Room[]>(() => buildInitialRooms(initialRooms));

  // Expanded outline modal
  const [expandedOutline, setExpandedOutline] = useState<WindowItem | null>(null);

  // Photo/AI modal
  const [showPhotoModal, setShowPhotoModal] = useState(false);
  const [photoMode, setPhotoMode] = useState<'window' | 'upholstery' | 'outline' | 'mockup'>('window');
  const [activeRoomId, setActiveRoomId] = useState<string | null>(null);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Save/PDF state
  const [saving, setSaving] = useState(false);
  const [savedQuote, setSavedQuote] = useState<{ id: string; quote_number: string } | null>(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);

  // Collected AI results for PDF
  const [collectedOutlines, setCollectedOutlines] = useState<any[]>([]);
  const [collectedMockups, setCollectedMockups] = useState<any[]>([]);

  // MAX's professional analysis text (from chat)
  const [maxAnalysis] = useState(initialMaxAnalysis || '');

  // Tab
  const [tab, setTab] = useState<'build' | 'customer' | 'summary' | 'preview' | 'history'>('build');
  const [quoteHistory, setQuoteHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // PDF Preview
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(false);

  const grandTotal = rooms.reduce((s, r) => s + calcRoomTotal(r), 0);

  // Auto-generate sequential customer name if none provided
  const ensureCustomerName = () => {
    if (customer.name.trim()) return customer.name.trim();
    const counter = parseInt(localStorage.getItem('empire_customer_counter') || '0', 10) + 1;
    localStorage.setItem('empire_customer_counter', String(counter));
    const autoName = `Customer ${counter}`;
    setCustomer(prev => ({ ...prev, name: autoName }));
    return autoName;
  };

  // ── Room CRUD ──────────────────────────────────────────
  const addRoom = () => setRooms([...rooms, { id: genId(), name: `Room ${rooms.length + 1}`, expanded: true, windows: [], upholstery: [] }]);
  const deleteRoom = (id: string) => { if (rooms.length > 1) setRooms(rooms.filter(r => r.id !== id)); };
  const toggleRoom = (id: string) => setRooms(rooms.map(r => r.id === id ? { ...r, expanded: !r.expanded } : r));
  const updateRoomName = (id: string, name: string) => setRooms(rooms.map(r => r.id === id ? { ...r, name } : r));

  // ── Window CRUD ────────────────────────────────────────
  const addWindow = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: [...r.windows, {
    id: genId(), name: `Window ${r.windows.length + 1}`, width: 48, height: 60, quantity: 1,
    treatmentType: 'ripplefold', mountType: 'wall', liningType: 'standard',
    hardwareType: 'track-ripplefold', hardwareColor: 'brushed-nickel', motorization: 'none', notes: '',
    fabricGrade: 'Standard' as FabricGrade, fullness: 2.5, laborRate: 65, drawDirection: 'center', fabricColor: '',
  }] } : r));
  const updateWindow = (roomId: string, wId: string, updates: Partial<WindowItem>) =>
    setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.map(w => w.id === wId ? { ...w, ...updates } : w) } : r));
  const deleteWindow = (roomId: string, wId: string) =>
    setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: r.windows.filter(w => w.id !== wId) } : r));
  const copyWindow = (roomId: string, wId: string) =>
    setRooms(rooms.map(r => { if (r.id === roomId) { const w = r.windows.find(w => w.id === wId); if (w) return { ...r, windows: [...r.windows, { ...w, id: genId(), name: `${w.name} (Copy)` }] }; } return r; }));

  // ── Upholstery CRUD ────────────────────────────────────
  const addUpholstery = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, upholstery: [...r.upholstery, {
    id: genId(), name: `Piece ${r.upholstery.length + 1}`, furnitureType: 'sofa',
    fabricYards: 14, fabricType: 'plain' as const, laborType: 'standard' as const,
    cushionCount: 3, width: 84, depth: 36, height: 34, notes: '',
  }] } : r));
  const updateUpholstery = (roomId: string, uId: string, updates: Partial<UpholsteryItem>) =>
    setRooms(rooms.map(r => r.id === roomId ? { ...r, upholstery: r.upholstery.map(u => u.id === uId ? { ...u, ...updates } : u) } : r));
  const deleteUpholstery = (roomId: string, uId: string) =>
    setRooms(rooms.map(r => r.id === roomId ? { ...r, upholstery: r.upholstery.filter(u => u.id !== uId) } : r));

  // ── Photo/AI ───────────────────────────────────────────
  const openPhotoModal = (roomId: string, itemId: string, mode: 'window' | 'upholstery' | 'outline' | 'mockup') => {
    setActiveRoomId(roomId); setActiveItemId(itemId); setPhotoMode(mode);
    setShowPhotoModal(true); setAnalysisResult(null);
    // For outline/mockup, reuse existing photo if available
    if (mode === 'outline' || mode === 'mockup') {
      const room = rooms.find(r => r.id === roomId);
      const win = room?.windows.find(w => w.id === itemId);
      const uph = room?.upholstery.find(u => u.id === itemId);
      const existing = win?.sourcePhoto || uph?.sourcePhoto || null;
      setUploadedImage(existing);
    } else {
      setUploadedImage(null);
    }
  };
  const openStandalonePhotoModal = (mode: 'outline' | 'mockup', roomId?: string) => {
    const rid = roomId || rooms[0]?.id || null;
    setActiveRoomId(rid); setActiveItemId(null); setPhotoMode(mode);
    setShowPhotoModal(true); setAnalysisResult(null);
    // For standalone outline/mockup, check if the first window in the room has a photo
    if (rid) {
      const room = rooms.find(r => r.id === rid);
      const firstPhoto = room?.windows.find(w => w.sourcePhoto)?.sourcePhoto
        || room?.upholstery.find(u => u.sourcePhoto)?.sourcePhoto || null;
      setUploadedImage(firstPhoto);
    } else {
      setUploadedImage(null);
    }
  };
  const compressImage = (dataUrl: string, maxWidth = 1600, quality = 0.8): Promise<string> => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let w = img.width, h = img.height;
        if (w > maxWidth) { h = Math.round(h * maxWidth / w); w = maxWidth; }
        canvas.width = w; canvas.height = h;
        canvas.getContext('2d')?.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.src = dataUrl;
    });
  };
  const [uploaded3DFile, setUploaded3DFile] = useState<{ name: string; url: string; size: string } | null>(null);
  const [show3DViewer, setShow3DViewer] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const THREE_D_EXTENSIONS = ['.glb', '.gltf', '.obj', '.usdz', '.ply', '.fbx', '.stl', '.dae'];
  const is3DFile = (name: string) => THREE_D_EXTENSIONS.some(ext => name.toLowerCase().endsWith(ext));

  const processFile = async (file: File) => {
    if (is3DFile(file.name)) {
      // Upload 3D file to backend for storage
      const formData = new FormData();
      formData.append('file', file);
      try {
        const res = await fetch(API_URL + '/files/upload', { method: 'POST', body: formData });
        const result = await res.json();
        // Backend saves to ~/Empire/uploads/{category}/{filename}
        const downloadUrl = `${API_URL}/files/${result.category}/${result.filename}`;
        setUploaded3DFile({ name: result.filename || file.name, url: downloadUrl, size: `${(file.size / 1024 / 1024).toFixed(1)} MB` });
        setShowCamera(false);
      } catch {
        // Fallback: local object URL for preview
        const url = URL.createObjectURL(file);
        setUploaded3DFile({ name: file.name, url, size: `${(file.size / 1024 / 1024).toFixed(1)} MB` });
        setShowCamera(false);
      }
    } else {
      // Image file — compress and set as preview
      const reader = new FileReader();
      reader.onload = async (ev) => {
        const raw = ev.target?.result as string;
        const compressed = await compressImage(raw);
        setUploadedImage(compressed); setShowCamera(false);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handlePaste = useCallback((e: ClipboardEvent) => {
    if (!showPhotoModal) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) { processFile(file); e.preventDefault(); return; }
      }
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file && is3DFile(file.name)) { processFile(file); e.preventDefault(); return; }
      }
    }
  }, [showPhotoModal]);

  useEffect(() => {
    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [handlePaste]);
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } } });
      setCameraStream(stream); setShowCamera(true);
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch { alert('Unable to access camera.'); }
  };
  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const v = videoRef.current, c = canvasRef.current;
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext('2d')?.drawImage(v, 0, 0);
      setUploadedImage(c.toDataURL('image/jpeg', 0.9)); stopCamera();
    }
  };
  const stopCamera = () => { cameraStream?.getTracks().forEach(t => t.stop()); setCameraStream(null); setShowCamera(false); };
  const closePhotoModal = () => { stopCamera(); setShowPhotoModal(false); setUploadedImage(null); setUploaded3DFile(null); setAnalysisResult(null); };

  const [mockupPreferences, setMockupPreferences] = useState('');
  const [designMode, setDesignMode] = useState<'new' | 'update' | 'rearrange' | 'renovate'>('new');
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);

  const analyzeImage = async () => {
    if (!uploadedImage) { console.error('analyzeImage: no uploadedImage'); return; }
    console.log('analyzeImage: starting, photoMode=', photoMode);
    setIsAnalyzing(true);
    try {
      const endpoints: Record<string, string> = {
        window: 'http://localhost:3001/api/measure',
        upholstery: 'http://localhost:3001/api/upholstery',
        outline: 'http://localhost:3001/api/outline',
        mockup: 'http://localhost:3001/api/mockup',
      };
      const body: any = { image: uploadedImage };
      if (photoMode === 'mockup') {
        const modeLabels: Record<string, string> = {
          'new': 'Design completely new window treatments from scratch, ignoring any existing treatments.',
          'update': 'Keep the current treatment style but update fabrics, hardware, and linings for a refresh.',
          'rearrange': 'Rearrange and reposition existing treatments for better functionality and aesthetics.',
          'renovate': 'Full renovation — remove everything and propose a complete redesign of the window area.',
        };
        const styleContext = selectedStyles.map(s => STYLE_PRESETS.find(p => p.id === s))
          .filter(Boolean).map(p => `${p!.label}: ${p!.keywords}`).join('. ');
        body.preferences = [
          modeLabels[designMode] || '',
          styleContext ? `STYLE INSPIRATION — design proposals MUST reflect these aesthetics: ${styleContext}.` : '',
          mockupPreferences,
        ].filter(Boolean).join(' ');
      }

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120000); // 2 min timeout
      const res = await fetch(endpoints[photoMode], { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: controller.signal });
      clearTimeout(timeout);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Analysis failed');

      if (photoMode === 'upholstery') {
        setAnalysisResult({
          mode: 'upholstery', confidence: Math.min(100, Math.max(0, data.confidence || 70)),
          furnitureType: data.furniture_type || 'Unknown', style: data.style || '',
          fabricYardsPlain: data.fabric_yards_plain || 0, fabricYardsPatterned: data.fabric_yards_patterned || 0,
          cushions: data.cushion_count || { seat: 0, back: 0, throw_pillows: 0 },
          hasWelting: data.has_welting || false, hasTufting: data.has_tufting || false,
          suggestedLaborType: data.suggested_labor_type || 'standard',
          laborCostLow: data.estimated_labor_cost_low || 0, laborCostHigh: data.estimated_labor_cost_high || 0,
          newFoamRecommended: data.new_foam_recommended || false, questions: data.questions || [],
          dimensions: data.estimated_dimensions || { width: 0, depth: 0, height: 0 },
          generated_image: data.generated_image || null,
        });
      } else if (photoMode === 'outline') {
        setAnalysisResult({
          mode: 'outline', confidence: Math.min(100, Math.max(0, data.confidence || 70)),
          windowOpening: data.window_opening || { width: 0, height: 0 },
          wallDimensions: data.wall_dimensions || { total_width: 0, ceiling_height: 0 },
          clearances: data.clearances || { above_window: 0, below_window: 0, left_wall: 0, right_wall: 0 },
          obstructions: data.obstructions || [],
          existingTreatments: data.existing_treatments || null,
          mounting: data.mounting_recommendations || {},
          outlineDescription: data.outline_description || '',
          referenceObjects: data.reference_objects_used || [],
          notes: data.notes || '',
        });
      } else if (photoMode === 'mockup') {
        // Attach generated images to matching proposals
        const proposals = data.proposals || [];
        const genImages = data.generated_images || [];
        proposals.forEach((p: any) => {
          const match = genImages.find((gi: any) => gi.tier === p.tier);
          if (match) p.generated_image = match.url;
        });
        setAnalysisResult({
          mode: 'mockup', confidence: Math.min(100, Math.max(0, data.confidence || 70)),
          roomAssessment: data.room_assessment || {},
          windowInfo: data.window_info || {},
          proposals,
          generalRecommendations: data.general_recommendations || [],
          notes: data.notes || '',
        });
      } else {
        setAnalysisResult({
          mode: 'window', confidence: Math.min(100, Math.max(0, data.confidence || 70)),
          suggestedWidth: Math.round(data.width_inches || 36), suggestedHeight: Math.round(data.height_inches || 48),
          windowType: data.window_type || 'Standard',
          recommendations: [
            ...(data.reference_objects_used?.length ? [`Scale: ${data.reference_objects_used.join(', ')}`] : []),
            ...(data.treatment_suggestions || []),
            ...(data.notes ? [data.notes] : []),
          ],
        });
      }
    } catch (err) { console.error('analyzeImage error:', err); alert('AI analysis error: ' + (err instanceof Error ? err.message : 'Failed')); }
    finally { setIsAnalyzing(false); }
  };

  // Auto-analyze when a NEW photo is uploaded (not reused from existing item)
  const prevImageRef = useRef<string | null>(null);
  useEffect(() => {
    if (uploadedImage && uploadedImage !== prevImageRef.current && showPhotoModal && !isAnalyzing && !analysisResult) {
      prevImageRef.current = uploadedImage;
      // Small delay to let UI settle, then auto-analyze
      const timer = setTimeout(() => analyzeImage(), 300);
      return () => clearTimeout(timer);
    }
  }, [uploadedImage, showPhotoModal]); // eslint-disable-line react-hooks/exhaustive-deps

  const applyAnalysis = () => {
    if (!analysisResult || !activeRoomId) return;
    // Helper: demote old sourcePhoto into photos[] when replacing with new one
    const demotePhoto = (item: WindowItem | UpholsteryItem | undefined) => {
      if (!item || !uploadedImage) return item?.photos || [];
      const prev = item.photos || [];
      if (item.sourcePhoto && item.sourcePhoto !== uploadedImage && !prev.includes(item.sourcePhoto)) {
        return [...prev, item.sourcePhoto];
      }
      return prev;
    };
    if (analysisResult.mode === 'upholstery' && activeItemId) {
      const existing = rooms.find(r => r.id === activeRoomId)?.upholstery.find(u => u.id === activeItemId);
      updateUpholstery(activeRoomId, activeItemId, {
        furnitureType: analysisResult.furnitureType, fabricYards: analysisResult.fabricYardsPlain || 0,
        cushionCount: (analysisResult.cushions?.seat || 0) + (analysisResult.cushions?.back || 0),
        laborType: analysisResult.hasTufting ? 'tufted' : 'standard',
        width: analysisResult.dimensions?.width || 0, depth: analysisResult.dimensions?.depth || 0,
        height: analysisResult.dimensions?.height || 0, aiAnalysis: analysisResult,
        sourcePhoto: uploadedImage || existing?.sourcePhoto,
        photos: demotePhoto(existing),
      });
    } else if (analysisResult.mode === 'outline' && activeItemId) {
      const existing = rooms.find(r => r.id === activeRoomId)?.windows.find(w => w.id === activeItemId);
      updateWindow(activeRoomId, activeItemId, {
        width: analysisResult.windowOpening?.width || 0, height: analysisResult.windowOpening?.height || 0,
        mountType: analysisResult.mounting?.mount_type === 'inside' ? 'inside' : analysisResult.mounting?.mount_type === 'ceiling' ? 'ceiling' : 'wall',
        sourcePhoto: uploadedImage || existing?.sourcePhoto,
        photos: demotePhoto(existing),
        aiAnalysis: {
          confidence: analysisResult.confidence,
          suggestedWidth: analysisResult.windowOpening?.width || 0,
          suggestedHeight: analysisResult.windowOpening?.height || 0,
          windowType: 'Outline',
          recommendations: [
            analysisResult.outlineDescription || '',
            ...(analysisResult.obstructions?.map((o: any) => `Obstruction: ${o.type} at ${o.location}`) || []),
            analysisResult.mounting?.notes || '',
          ].filter(Boolean),
        },
      });
    } else if (analysisResult.mode === 'window' && activeItemId) {
      const existing = rooms.find(r => r.id === activeRoomId)?.windows.find(w => w.id === activeItemId);
      updateWindow(activeRoomId, activeItemId, {
        width: analysisResult.suggestedWidth, height: analysisResult.suggestedHeight,
        sourcePhoto: uploadedImage || existing?.sourcePhoto, photos: demotePhoto(existing),
        aiAnalysis: analysisResult,
      });
    }
    // Collect outline/mockup results for PDF (include uploaded photo for embedding)
    if (analysisResult.mode === 'outline') {
      setCollectedOutlines(prev => [...prev, { roomName: rooms.find(r => r.id === activeRoomId)?.name || 'Unknown', photo: uploadedImage || null, ...analysisResult }]);
    } else if (analysisResult.mode === 'mockup') {
      setCollectedMockups(prev => [...prev, { roomName: rooms.find(r => r.id === activeRoomId)?.name || 'Unknown', photo: uploadedImage || null, ...analysisResult }]);
    }
    closePhotoModal();
  };

  // ── Send mockup proposals to QuoteBuilder as line items ─
  const applyMockupToQuote = (tierIndex?: number) => {
    if (!analysisResult || analysisResult.mode !== 'mockup' || !activeRoomId) return;
    const proposals = tierIndex !== undefined
      ? [analysisResult.proposals[tierIndex]]
      : analysisResult.proposals || [];
    const roomId = activeRoomId;
    const winInfo = analysisResult.windowInfo || {};

    const newWindows: WindowItem[] = proposals.map((p: any, i: number) => ({
      id: genId(),
      name: `${p.tier || `Option ${i + 1}`}`,
      width: winInfo.estimated_width || 48,
      height: winInfo.estimated_height || 60,
      quantity: 1,
      treatmentType: 'ripplefold',
      mountType: 'wall',
      liningType: 'standard',
      hardwareType: 'rod-decorative',
      motorization: (p.extras || []).some((e: string) => e.toLowerCase().includes('motor')) ? 'somfy' : 'none',
      notes: `${p.treatment_type || ''} — ${p.fabric || ''}, ${p.style || ''}. ${(p.extras || []).join(', ')}`.trim(),
      fabricGrade: (i === 0 ? 'Standard' : i === 1 ? 'Premium' : 'Luxe') as FabricGrade,
      fullness: 2.5, laborRate: 65,
      sourcePhoto: uploadedImage || undefined,
      photos: [],
      aiAnalysis: {
        confidence: analysisResult.confidence || 80,
        suggestedWidth: winInfo.estimated_width || 48,
        suggestedHeight: winInfo.estimated_height || 60,
        windowType: winInfo.type || 'Standard',
        recommendations: [p.visual_description, p.design_rationale].filter(Boolean),
      },
    }));

    setRooms(prev => prev.map(r => r.id === roomId ? { ...r, windows: [...r.windows, ...newWindows] } : r));
    setCollectedMockups(prev => [...prev, { roomName: rooms.find(r => r.id === roomId)?.name || 'Unknown', photo: uploadedImage || null, ...analysisResult }]);
    closePhotoModal();
    setTab('build');
  };

  // ── Quick PDF from mockup analysis — save + download in one click ─
  // Sends raw AI proposal data to backend; backend uses price_range_low/high, not sqft calc
  const quickPdfFromMockup = async () => {
    if (!analysisResult || analysisResult.mode !== 'mockup') return;
    setSaving(true);
    try {
      const proposals = analysisResult.proposals || [];
      const winInfo = analysisResult.windowInfo || {};
      const roomName = rooms.find(r => r.id === activeRoomId)?.name || 'Room 1';
      const custName = customer.name.trim() || 'Window Treatment Client';

      // Build windows using AI price ranges (midpoint) — not the sqft pricing engine
      const pdfWindows = proposals.map((p: any, i: number) => {
        const priceMid = Math.round(((p.price_range_low || 0) + (p.price_range_high || 0)) / 2);
        return {
          name: p.tier || `Option ${i + 1}`,
          width: winInfo.estimated_width || 48,
          height: winInfo.estimated_height || 60,
          quantity: 1,
          // Store actual AI treatment data for PDF rendering
          treatmentType: p.treatment_type || 'Custom',
          liningType: p.lining || 'standard',
          hardwareType: p.hardware || 'decorative',
          motorization: (p.extras || []).some((e: string) => e.toLowerCase().includes('motor')) ? 'motorized' : 'none',
          mountType: 'wall',
          notes: `${p.fabric || ''} — ${p.style || ''}. ${(p.extras || []).join(', ')}`.trim(),
          price: priceMid,
          price_range_low: p.price_range_low || 0,
          price_range_high: p.price_range_high || 0,
          extras: p.extras || [],
          is_proposal: true,
          aiAnalysis: {
            confidence: analysisResult.confidence || 80,
            suggestedWidth: winInfo.estimated_width || 48,
            suggestedHeight: winInfo.estimated_height || 60,
            windowType: winInfo.type || 'Standard',
            recommendations: [p.visual_description, p.design_rationale].filter(Boolean),
          },
        };
      });

      const lineItems = pdfWindows.map((w: any) => ({
        description: `${roomName} — ${w.name}: ${w.treatmentType}`,
        quantity: 1, unit: 'ea', rate: w.price, amount: w.price, category: 'labor',
      }));
      // Use midpoint of the middle tier as representative total (these are OPTIONS, not cumulative)
      const total = pdfWindows.length > 0 ? pdfWindows[Math.min(1, pdfWindows.length - 1)].price : 0;

      // Generate AI mockup images for each proposal (in parallel)
      const roomInfo = analysisResult.roomAssessment || {};
      const palette = (roomInfo.color_palette || []).join(', ');
      const tierImageStyles: Record<string, string> = {
        'Elegant Essential': 'Simple, clean, minimal design. Single-layer treatment. Standard fabric with solid color. Basic rod or brackets. Bright, airy, budget-friendly elegance.',
        "Designer's Choice": 'Layered, textured, curated design. Multiple elements. Visible fabric texture and weave. Decorative hardware with detailed finials. Rich mid-range materials.',
        'Ultimate Luxury': 'Opulent, grand, multi-layered statement. Floor-to-ceiling panels with sheers behind. Visible fabric sheen and luster. Ornate hardware with crystal or gilded finials. Top treatment (cornice or valance). Tiebacks and trim details. Luxury magazine cover quality.',
      };
      const imagePromises = proposals.slice(0, 3).map(async (p: any, idx: number) => {
        try {
          const tierStyle = tierImageStyles[p.tier] || tierImageStyles['Elegant Essential'];
          const styleInfluence = selectedStyles.map(s => STYLE_PRESETS.find(pr => pr.id === s)?.keywords).filter(Boolean).join(', ');
          const isValance = p.treatment_type?.toLowerCase().includes('valance') || p.treatment_type?.toLowerCase().includes('cornice');
          const hardwareNote = isValance
            ? `The ${p.hardware || 'mounting board'} is HIDDEN BEHIND the valance/cornice — NOT visible in front.`
            : `Hardware: ${p.hardware || 'decorative rod'} mounted 4-6 inches ABOVE the window frame.`;
          const fabricTexture = p.fabric?.toLowerCase().includes('velvet') ? 'deep plush velvet pile with light-catching sheen'
            : p.fabric?.toLowerCase().includes('silk') ? 'smooth lustrous silk with subtle shimmer'
            : p.fabric?.toLowerCase().includes('linen') ? 'natural linen weave with organic texture'
            : 'rich woven textile with visible drape and body';

          const prompt = [
            `PROFESSIONAL interior design photograph of a ${roomInfo.room_type || 'bedroom'} with a ${winInfo.type || 'standard'} window.`,
            `WINDOW TREATMENT ONLY — do NOT change or move any furniture or room decor.`,
            `Installed: ${p.treatment_type || 'custom drapery'} in ${p.fabric || 'elegant fabric'}, ${p.style || 'classic'} style.`,
            tierStyle,
            `The fabric has visible texture: ${fabricTexture}.`,
            hardwareNote,
            p.lining ? `${p.lining} lining for ${p.lining === 'blackout' ? 'complete light blocking' : 'privacy and filtering'}.` : '',
            (p.extras || []).length > 0 ? `Special details: ${p.extras.join(', ')}.` : '',
            styleInfluence ? `Design aesthetic: ${styleInfluence}.` : '',
            `Room: ${palette || 'neutral warm tones'} scheme. ${roomInfo.light_level || 'Natural'} light. All furniture stays exactly as-is.`,
            `Photorealistic, straight-on view, 4K sharp focus, Architectural Digest quality.`,
            idx === 2 ? 'This is the MOST LUXURIOUS option — visually stunning, dramatically different from basic treatments.' : '',
          ].filter(Boolean).join(' ');
          const res = await fetch('http://localhost:3001/api/imagine', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
          });
          if (res.ok) {
            const data = await res.json();
            return { tier: p.tier || 'Option', url: data.url };
          }
        } catch { /* non-blocking */ }
        return null;
      });
      const imageResults = (await Promise.all(imagePromises)).filter(Boolean);

      const mockupData = [{ roomName, photo: uploadedImage || null, ...analysisResult, generated_images: imageResults }];

      const res = await fetch(API_URL + '/quotes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: custName, customer_email: customer.email, customer_phone: customer.phone,
          customer_address: customer.address, project_name: projectName || 'AI Design Consultation',
          line_items: lineItems, subtotal: total, total, tax_rate: 0.08,
          business_name: 'Empire', terms: '50% deposit required. Balance due upon completion.', valid_days: 30,
          rooms: [{ name: roomName, windows: pdfWindows, upholstery: [] }],
          ai_mockups: mockupData,
          ai_outlines: collectedOutlines.length > 0 ? collectedOutlines : null,
          max_analysis: maxAnalysis || null,
        }),
      });
      const result = await res.json();
      if (result.status === 'created') {
        setSavedQuote({ id: result.quote.id, quote_number: result.quote.quote_number });
        // Download the PDF
        const pdfRes = await fetch(API_URL + `/quotes/${result.quote.id}/pdf`, { method: 'POST' });
        if (pdfRes.ok) {
          const blob = await pdfRes.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = `${result.quote.quote_number}.pdf`;
          document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
        }
        // Also apply to QuoteBuilder state
        applyMockupToQuote();
      }
    } catch { alert('Quick PDF failed. Check backend.'); }
    finally { setSaving(false); }
  };

  // ── Quick PDF from outline analysis — dimensional plan PDF ─
  const quickPdfFromOutline = async () => {
    if (!analysisResult || analysisResult.mode !== 'outline') return;
    setSaving(true);
    try {
      const roomName = rooms.find(r => r.id === activeRoomId)?.name || 'Room 1';
      const custName = customer.name.trim() || 'Window Treatment Client';
      const wo = analysisResult.windowOpening || {};
      const mt = analysisResult.mounting || {};

      const outlineData = [{ roomName, photo: uploadedImage || null, ...analysisResult }];

      // Create a quote with just the outline data (no line items needed — it's a dimensional plan)
      const res = await fetch(API_URL + '/quotes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: custName, customer_email: customer.email, customer_phone: customer.phone,
          customer_address: customer.address,
          project_name: projectName || `Window Dimensional Plan — ${roomName}`,
          line_items: [{
            description: `${roomName} — Window ${wo.width || 0}" × ${wo.height || 0}" — ${mt.mount_type || 'wall'} mount`,
            quantity: 1, unit: 'ea', rate: 0, amount: 0, category: 'labor',
          }],
          subtotal: 0, total: 0, tax_rate: 0,
          business_name: 'Empire',
          terms: 'Dimensional plan for reference. Final measurements to be confirmed on-site.',
          valid_days: 60,
          rooms: [{ name: roomName, windows: [{
            name: 'Window', width: wo.width || 0, height: wo.height || 0,
            quantity: 1, treatmentType: 'TBD', mountType: mt.mount_type || 'wall',
            liningType: 'TBD', hardwareType: 'TBD', motorization: 'none', notes: mt.notes || '',
            price: 0,
            aiAnalysis: {
              confidence: analysisResult.confidence || 80,
              suggestedWidth: wo.width || 0, suggestedHeight: wo.height || 0,
              windowType: 'Outline', recommendations: [
                analysisResult.outlineDescription || '',
                ...(analysisResult.obstructions?.map((o: any) => `Obstruction: ${o.type} at ${o.location}`) || []),
                mt.notes || '',
              ].filter(Boolean),
            },
          }], upholstery: [] }],
          ai_outlines: outlineData,
          ai_mockups: collectedMockups.length > 0 ? collectedMockups : null,
          max_analysis: maxAnalysis || null,
        }),
      });
      const result = await res.json();
      if (result.status === 'created') {
        setSavedQuote({ id: result.quote.id, quote_number: result.quote.quote_number });
        setCollectedOutlines(prev => [...prev, ...outlineData]);
        const pdfRes = await fetch(API_URL + `/quotes/${result.quote.id}/pdf`, { method: 'POST' });
        if (pdfRes.ok) {
          const blob = await pdfRes.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url; a.download = `${result.quote.quote_number}.pdf`;
          document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
        }
      }
    } catch { alert('Quick PDF failed. Check backend.'); }
    finally { setSaving(false); }
  };

  // ── Share outline via email ─
  const shareOutlineEmail = () => {
    if (!analysisResult || analysisResult.mode !== 'outline') return;
    const wo = analysisResult.windowOpening || {};
    const mt = analysisResult.mounting || {};
    const cl = analysisResult.clearances || {};
    const roomName = rooms.find(r => r.id === activeRoomId)?.name || 'Room';
    const subject = encodeURIComponent(`Window Dimensions — ${roomName} from Empire`);
    const body = encodeURIComponent(
      `Window Dimensional Plan — ${roomName}\n\n` +
      `Window Opening: ${wo.width || 0}" W × ${wo.height || 0}" H\n` +
      `Clearances: ${cl.above_window || 0}" above, ${cl.below_window || 0}" below, ${cl.left_wall || 0}" left, ${cl.right_wall || 0}" right\n` +
      `Mounting: ${mt.mount_type || 'wall'} mount at ${mt.mounting_height || 0}" height, rod ${mt.rod_width || 0}" wide\n` +
      `${mt.notes ? `Notes: ${mt.notes}\n` : ''}` +
      `${analysisResult.outlineDescription ? `\nDescription: ${analysisResult.outlineDescription}\n` : ''}` +
      `\nConfidence: ${analysisResult.confidence || 0}%\n\n` +
      `— Empire Custom Window Treatments`
    );
    const mailto = `mailto:${customer.email || ''}?subject=${subject}&body=${body}`;
    const a = document.createElement('a'); a.href = mailto; a.click();
  };

  // ── Save & PDF ─────────────────────────────────────────
  const buildLineItems = () => rooms.flatMap(room => [
    ...room.windows.map(w => {
      const y = calcYardage(w);
      return {
        description: `${room.name} — ${w.name} (${w.treatmentType}, ${w.fabricGrade}, ${y.totalYardage}yd)`,
        quantity: w.quantity, unit: 'ea', rate: y.total / (w.quantity || 1),
        amount: y.total, category: 'labor',
      };
    }),
    ...room.upholstery.map(u => ({
      description: `${room.name} — ${u.name} (${u.furnitureType}, ${u.laborType})`,
      quantity: 1, unit: 'ea', rate: calcUpholsteryPrice(u), amount: calcUpholsteryPrice(u), category: 'labor',
    })),
  ]);

  const saveQuote = async () => {
    const custName = ensureCustomerName();
    setSaving(true);
    try {
      const res = await fetch(API_URL + '/quotes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: custName, customer_email: customer.email,
          customer_phone: customer.phone, customer_address: customer.address,
          project_name: projectName, line_items: buildLineItems(),
          subtotal: grandTotal, total: grandTotal, tax_rate: 0.08,
          business_name: 'Empire', terms: '50% deposit required. Balance due upon completion.',
          valid_days: 30,
          // Full structured room data for rich PDF
          rooms: rooms.map(r => ({
            name: r.name,
            windows: r.windows.map(w => {
              const y = calcYardage(w);
              return {
                name: w.name, width: w.width, height: w.height, quantity: w.quantity,
                treatmentType: w.treatmentType, liningType: w.liningType,
                hardwareType: w.hardwareType, hardwareColor: w.hardwareColor || 'brushed-nickel', motorization: w.motorization,
                mountType: w.mountType, notes: w.notes,
                fabricGrade: w.fabricGrade, fullness: w.fullness, laborRate: w.laborRate,
                price: y.total,
                yardage: { panels: y.panelsNeeded, perWindow: y.yardagePerWindow, waste: y.wasteYardage, total: y.totalYardage },
                breakdown: { materials: y.materialsTotal, labor: y.laborTotal, hardware: y.hardwareTotal, tax: y.tax },
                sourcePhoto: w.sourcePhoto || null,
                photos: w.photos || [],
                aiAnalysis: w.aiAnalysis || null,
              };
            }),
            upholstery: r.upholstery.map(u => ({
              name: u.name, furnitureType: u.furnitureType, fabricYards: u.fabricYards,
              fabricType: u.fabricType, laborType: u.laborType, cushionCount: u.cushionCount,
              width: u.width, depth: u.depth, height: u.height, notes: u.notes,
              price: calcUpholsteryPrice(u),
              sourcePhoto: u.sourcePhoto || null,
              photos: u.photos || [],
              aiAnalysis: u.aiAnalysis || null,
            })),
          })),
          ai_outlines: collectedOutlines.length > 0 ? collectedOutlines : null,
          ai_mockups: collectedMockups.length > 0 ? collectedMockups : null,
          max_analysis: maxAnalysis || null,
        }),
      });
      const result = await res.json();
      if (result.status === 'created') setSavedQuote({ id: result.quote.id, quote_number: result.quote.quote_number });
    } catch { alert('Save failed. Check backend.'); }
    finally { setSaving(false); }
  };

  const downloadPdf = async () => {
    if (!savedQuote) { await saveQuote(); return; }
    setGeneratingPdf(true);
    try {
      const res = await fetch(API_URL + `/quotes/${savedQuote.id}/pdf`, { method: 'POST' });
      if (!res.ok) throw new Error('PDF failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `${savedQuote.quote_number}.pdf`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
    } catch { alert('PDF generation failed.'); }
    finally { setGeneratingPdf(false); }
  };

  const printQuote = async () => {
    if (!savedQuote) { await saveQuote(); return; }
    try {
      const res = await fetch(API_URL + `/quotes/${savedQuote.id}/pdf`, { method: 'POST' });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const win = window.open(url, '_blank');
      if (win) { win.onload = () => { win.print(); }; }
    } catch { alert('Print failed.'); }
  };

  // ── Preview / Share ────────────────────────────────────
  const generatePreview = async () => {
    if (!savedQuote) { await saveQuote(); }
    // savedQuote may have just been set by saveQuote, but state update is async
    // We'll rely on the useEffect-like re-trigger via tab switch
  };

  const loadPdfPreview = async (quoteId: string) => {
    setLoadingPreview(true);
    try {
      const res = await fetch(API_URL + `/quotes/${quoteId}/pdf`, { method: 'POST' });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
    } catch { alert('PDF preview failed.'); }
    finally { setLoadingPreview(false); }
  };

  const handlePreviewTab = async () => {
    setTab('preview');
    if (!savedQuote) {
      ensureCustomerName();
      setSaving(true);
      try {
        const lineItems = buildLineItems();
        const res = await fetch(API_URL + '/quotes', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            customer_name: customer.name || 'Customer', customer_email: customer.email,
            customer_phone: customer.phone, customer_address: customer.address,
            project_name: projectName || 'Estimate', line_items: lineItems,
            subtotal: grandTotal, total: grandTotal, tax_rate: 0.08,
            business_name: 'Empire', terms: '50% deposit required. Balance due upon completion.',
            valid_days: 30,
            rooms: rooms.map(r => ({
              name: r.name,
              windows: r.windows.map(w => {
                const y = calcYardage(w);
                return {
                  name: w.name, width: w.width, height: w.height, quantity: w.quantity,
                  treatmentType: w.treatmentType, liningType: w.liningType,
                  hardwareType: w.hardwareType, hardwareColor: w.hardwareColor || 'brushed-nickel', motorization: w.motorization,
                  mountType: w.mountType, notes: w.notes,
                  fabricGrade: w.fabricGrade, fullness: w.fullness, laborRate: w.laborRate,
                  price: y.total,
                  yardage: { panels: y.panelsNeeded, perWindow: y.yardagePerWindow, waste: y.wasteYardage, total: y.totalYardage },
                  breakdown: { materials: y.materialsTotal, labor: y.laborTotal, hardware: y.hardwareTotal, tax: y.tax },
                  sourcePhoto: w.sourcePhoto || null, photos: w.photos || [],
                  aiAnalysis: w.aiAnalysis || null,
                };
              }),
              upholstery: r.upholstery.map(u => ({
                name: u.name, furnitureType: u.furnitureType, fabricYards: u.fabricYards,
                fabricType: u.fabricType, laborType: u.laborType, cushionCount: u.cushionCount,
                width: u.width, depth: u.depth, height: u.height, notes: u.notes,
                price: calcUpholsteryPrice(u), sourcePhoto: u.sourcePhoto || null, photos: u.photos || [], aiAnalysis: u.aiAnalysis || null,
              })),
            })),
            ai_outlines: collectedOutlines.length > 0 ? collectedOutlines : null,
            ai_mockups: collectedMockups.length > 0 ? collectedMockups : null,
            max_analysis: maxAnalysis || null,
          }),
        });
        const result = await res.json();
        if (result.status === 'created') {
          setSavedQuote({ id: result.quote.id, quote_number: result.quote.quote_number });
          await loadPdfPreview(result.quote.id);
        }
      } catch (err) { console.error('Save/Preview error:', err); alert('Save failed — check line items.'); setTab('build'); }
      finally { setSaving(false); }
    } else {
      try { await loadPdfPreview(savedQuote.id); }
      catch (err) { console.error('PDF load error:', err); }
    }
  };

  const printFromPreview = () => {
    if (!pdfUrl) return;
    const win = window.open(pdfUrl, '_blank');
    if (win) { win.onload = () => { win.print(); }; }
  };

  const downloadFromPreview = () => {
    if (!pdfUrl || !savedQuote) return;
    const a = document.createElement('a'); a.href = pdfUrl;
    a.download = `${savedQuote.quote_number}.pdf`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  const shareViaEmail = () => {
    if (!savedQuote) return;
    const subject = encodeURIComponent(`Estimate ${savedQuote.quote_number} from Empire`);
    const body = encodeURIComponent(`Hi ${customer.name},\n\nPlease find attached your estimate ${savedQuote.quote_number} for $${grandTotal.toLocaleString()}.\n\nThank you,\nEmpire`);
    const mailto = `mailto:${customer.email || ''}?subject=${subject}&body=${body}`;
    const a = document.createElement('a'); a.href = mailto; a.click();
    setShowShareMenu(false);
  };

  const copyQuoteLink = () => {
    if (!savedQuote) return;
    const link = `${window.location.origin}/quotes/${savedQuote.id}`;
    navigator.clipboard.writeText(link).then(() => { alert('Link copied!'); });
    setShowShareMenu(false);
  };

  // ── Quote History ─────────────────────────────────────
  const loadQuoteHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(API_URL + '/quotes');
      const data = await res.json();
      setQuoteHistory(Array.isArray(data) ? data : data.quotes || []);
    } catch { setQuoteHistory([]); }
    finally { setLoadingHistory(false); }
  };

  const loadQuoteById = async (id: string) => {
    try {
      const res = await fetch(API_URL + `/quotes/${id}`);
      const q = await res.json();
      // Populate customer fields
      setCustomer({ name: q.customer_name || '', email: q.customer_email || '', phone: q.customer_phone || '', address: q.customer_address || '' });
      setProjectName(q.project_name || '');
      // Populate rooms from structured room data
      if (q.rooms?.length > 0) {
        const loadedRooms: Room[] = q.rooms.map((r: any, ri: number) => ({
          id: `r-${ri}-${Date.now()}`,
          name: r.name || `Room ${ri + 1}`,
          windows: (r.windows || []).map((w: any, wi: number) => ({
            id: `w-${ri}-${wi}-${Date.now()}`, name: w.name || `Window ${wi + 1}`,
            width: w.width || 0, height: w.height || 0, quantity: w.quantity || 1,
            treatmentType: w.treatmentType || 'Drapery', mountType: w.mountType || 'Inside',
            liningType: w.liningType || 'Standard', hardwareType: w.hardwareType || 'Standard Rod',
            motorization: w.motorization || 'None', notes: w.notes || '',
            fabricGrade: w.fabricGrade || 'B', fullness: w.fullness || 2.5, laborRate: w.laborRate || 45,
            drawDirection: w.drawDirection || 'center', fabricColor: w.fabricColor || '',
            sourcePhoto: w.sourcePhoto || undefined, photos: w.photos || [], aiAnalysis: w.aiAnalysis || undefined,
          })),
          upholstery: (r.upholstery || []).map((u: any, ui: number) => ({
            id: `u-${ri}-${ui}-${Date.now()}`, name: u.name || `Piece ${ui + 1}`,
            furnitureType: u.furnitureType || 'Sofa', fabricYards: u.fabricYards || 12,
            fabricType: u.fabricType || 'plain', laborType: u.laborType || 'standard',
            cushionCount: u.cushionCount || 3, width: u.width || 84, depth: u.depth || 36, height: u.height || 34,
            notes: u.notes || '', fabricGrade: (u.fabricGrade as FabricGrade) || 'B',
            sourcePhoto: u.sourcePhoto || undefined, photos: u.photos || [], aiAnalysis: u.aiAnalysis || undefined,
          })),
        }));
        setRooms(loadedRooms);
      }
      setSavedQuote({ id: q.id, quote_number: q.quote_number });
      setTab('build');
    } catch { alert('Failed to load quote'); }
  };

  // ── Auto-save draft (every 60s if customer name exists) ─────
  const autoSaveRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [lastAutoSave, setLastAutoSave] = useState<string | null>(null);

  useEffect(() => {
    if (saving) return;
    // Only auto-save if there's a customer name (manual or auto-generated)
    if (!customer.name.trim() && grandTotal === 0) return;
    if (autoSaveRef.current) clearTimeout(autoSaveRef.current);
    autoSaveRef.current = setTimeout(async () => {
      try {
        const autoName = customer.name.trim() || ensureCustomerName();
        const body = {
          customer_name: autoName, customer_email: customer.email,
          customer_phone: customer.phone, customer_address: customer.address,
          project_name: projectName, line_items: buildLineItems(),
          subtotal: grandTotal, total: grandTotal, tax_rate: 0.08,
          business_name: 'Empire', terms: '50% deposit required. Balance due upon completion.',
          valid_days: 30,
          rooms: rooms.map(r => ({
            name: r.name,
            windows: r.windows.map(w => {
              const y = calcYardage(w);
              return { name: w.name, width: w.width, height: w.height, quantity: w.quantity, treatmentType: w.treatmentType, liningType: w.liningType, hardwareType: w.hardwareType, hardwareColor: w.hardwareColor || 'brushed-nickel', motorization: w.motorization, mountType: w.mountType, notes: w.notes, fabricGrade: w.fabricGrade, fullness: w.fullness, laborRate: w.laborRate, drawDirection: w.drawDirection, fabricColor: w.fabricColor, price: y.total, sourcePhoto: w.sourcePhoto || null, photos: w.photos || [], aiAnalysis: w.aiAnalysis || null };
            }),
            upholstery: r.upholstery.map(u => ({ name: u.name, furnitureType: u.furnitureType, fabricYards: u.fabricYards, fabricType: u.fabricType, laborType: u.laborType, cushionCount: u.cushionCount, width: u.width, depth: u.depth, height: u.height, notes: u.notes, price: calcUpholsteryPrice(u), sourcePhoto: u.sourcePhoto || null, photos: u.photos || [], aiAnalysis: u.aiAnalysis || null })),
          })),
        };
        if (savedQuote) {
          await fetch(API_URL + `/quotes/${savedQuote.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        } else {
          const res = await fetch(API_URL + '/quotes', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
          const result = await res.json();
          if (result.status === 'created') setSavedQuote({ id: result.quote.id, quote_number: result.quote.quote_number });
        }
        setLastAutoSave(new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }));
      } catch { /* silent auto-save failure */ }
    }, 60000);
    return () => { if (autoSaveRef.current) clearTimeout(autoSaveRef.current); };
  }, [customer, rooms, projectName, grandTotal]);

  // ── Draft persistence (sessionStorage) ─────────────────
  const DRAFT_KEY = 'empire_quote_draft';
  const draftSaveRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Save draft to sessionStorage (debounced 2s)
  useEffect(() => {
    if (draftSaveRef.current) clearTimeout(draftSaveRef.current);
    draftSaveRef.current = setTimeout(() => {
      try {
        const draft = {
          customer, projectName,
          rooms: rooms.map(r => ({
            ...r,
            windows: r.windows.map(w => ({ ...w, sourcePhoto: undefined, photos: undefined })), // skip large base64
            upholstery: r.upholstery.map(u => ({ ...u, sourcePhoto: undefined, photos: undefined })),
          })),
          savedQuote, tab,
        };
        sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
      } catch { /* quota exceeded — ignore */ }
    }, 2000);
    return () => { if (draftSaveRef.current) clearTimeout(draftSaveRef.current); };
  }, [customer, projectName, rooms, savedQuote, tab]);

  // Restore draft on mount (only if no initial data provided)
  useEffect(() => {
    if (initialCustomer?.name || initialRooms?.length) return; // skip if opened with data
    try {
      const raw = sessionStorage.getItem(DRAFT_KEY);
      if (!raw) return;
      const draft = JSON.parse(raw);
      if (draft.customer?.name) setCustomer(draft.customer);
      if (draft.projectName) setProjectName(draft.projectName);
      if (draft.rooms?.length) setRooms(draft.rooms);
      if (draft.savedQuote) setSavedQuote(draft.savedQuote);
      if (draft.tab) setTab(draft.tab);
    } catch { /* ignore parse errors */ }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Styles ─────────────────────────────────────────────
  const inputStyle: React.CSSProperties = { background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' };
  const selectStyle: React.CSSProperties = { ...inputStyle, cursor: 'pointer' };

  // ═══════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════

  return (
    <div className="flex flex-col h-full">
      {/* 3D Viewer Modal */}
      {show3DViewer && uploaded3DFile && (
        <Viewer3D
          fileUrl={uploaded3DFile.url}
          fileName={uploaded3DFile.name}
          onClose={() => setShow3DViewer(false)}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4" style={{ color: 'var(--gold)' }} />
          <h2 className="text-sm font-semibold" style={{ color: 'var(--gold)' }}>
            {savedQuote ? savedQuote.quote_number : 'New Estimate'}
          </h2>
          {customer.name && <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(212,175,55,0.1)', color: 'var(--text-secondary)' }}>{customer.name}</span>}
          <span className="text-lg font-bold font-mono" style={{ color: 'var(--gold)' }}>${grandTotal.toLocaleString()}</span>
          {lastAutoSave && <span className="text-[8px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>saved {lastAutoSave}</span>}
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={printQuote} className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition"
            style={{ background: 'var(--surface)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
            <Printer className="w-3 h-3" /> Print
          </button>
          <button onClick={downloadPdf} disabled={generatingPdf}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium transition"
            style={{ background: 'var(--surface)', color: 'var(--purple)', border: '1px solid var(--purple-border)' }}>
            {generatingPdf ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />} PDF
          </button>
          <button onClick={saveQuote} disabled={saving}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition"
            style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
            <Send className="w-3 h-3" /> {saving ? 'Saving…' : savedQuote ? 'Update' : 'Save'}
          </button>
          <button onClick={onClose} className="p-1" style={{ color: 'var(--text-muted)' }}><X className="w-4 h-4" /></button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 px-3 pt-2 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        {([['build', 'Quote Builder'], ['customer', 'Customer'], ['summary', 'Summary']] as const).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className="px-3 py-1.5 text-[11px] font-medium transition"
            style={{
              color: tab === key ? 'var(--gold)' : 'var(--text-muted)',
              borderBottom: tab === key ? '2px solid var(--gold)' : '2px solid transparent',
            }}>
            {label}
          </button>
        ))}
        <button onClick={handlePreviewTab}
          className="px-3 py-1.5 text-[11px] font-medium transition flex items-center gap-1"
          style={{
            color: tab === 'preview' ? 'var(--cyan)' : 'var(--text-muted)',
            borderBottom: tab === 'preview' ? '2px solid var(--cyan)' : '2px solid transparent',
          }}>
          <Eye className="w-3 h-3" /> Preview PDF
        </button>
        <button onClick={() => { setTab('history'); loadQuoteHistory(); }}
          className="px-3 py-1.5 text-[11px] font-medium transition flex items-center gap-1 ml-auto"
          style={{
            color: tab === 'history' ? '#8B5CF6' : 'var(--text-muted)',
            borderBottom: tab === 'history' ? '2px solid #8B5CF6' : '2px solid transparent',
          }}>
          <Clock className="w-3 h-3" /> History
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">

        {/* ── BUILD TAB ──────────────────────────────────── */}
        {tab === 'build' && (
          <>
            {/* AI Banner + Tools */}
            <div className="rounded-xl overflow-hidden" style={{ background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)' }}>
              <div className="flex items-center gap-3 px-3 py-2">
                <Brain className="w-5 h-5 shrink-0" style={{ color: '#8B5CF6' }} />
                <div className="flex-1">
                  <p className="text-[11px] font-semibold" style={{ color: '#8B5CF6' }}>AI Design Studio</p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Camera on any item for measurements, or use the tools below</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 px-3 pb-3">
                <button onClick={() => openStandalonePhotoModal('outline')}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-medium transition hover:opacity-90"
                  style={{ background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)', color: '#3b82f6' }}>
                  <Ruler className="w-3.5 h-3.5" />
                  <div className="text-left">
                    <span className="block font-semibold">Outline Plan</span>
                    <span className="block text-[9px] opacity-70">Extract dimensions from photo</span>
                  </div>
                </button>
                <button onClick={() => openStandalonePhotoModal('mockup')}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-medium transition hover:opacity-90"
                  style={{ background: 'rgba(236,72,153,0.15)', border: '1px solid rgba(236,72,153,0.3)', color: '#ec4899' }}>
                  <Palette className="w-3.5 h-3.5" />
                  <div className="text-left">
                    <span className="block font-semibold">Mockup Studio</span>
                    <span className="block text-[9px] opacity-70">Design treatment proposals</span>
                  </div>
                </button>
              </div>
            </div>

            {/* Rooms */}
            {rooms.map(room => (
              <div key={room.id} className="rounded-xl overflow-hidden" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                {/* Room header */}
                <div className="flex items-center justify-between px-4 py-2.5" style={{ borderBottom: room.expanded ? '1px solid var(--border)' : 'none' }}>
                  <div className="flex items-center gap-2">
                    <button onClick={() => toggleRoom(room.id)} className="p-0.5">
                      {room.expanded ? <ChevronUp className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} /> : <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />}
                    </button>
                    <input type="text" value={room.name} onChange={e => updateRoomName(room.id, e.target.value)}
                      className="bg-transparent text-xs font-semibold outline-none" style={{ color: 'var(--text-primary)' }} />
                    <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                      ({room.windows.length} win{room.upholstery.length > 0 ? `, ${room.upholstery.length} uph` : ''})
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold font-mono" style={{ color: 'var(--gold)' }}>${calcRoomTotal(room).toLocaleString()}</span>
                    <button onClick={() => deleteRoom(room.id)} className="p-1 rounded" style={{ color: 'var(--text-muted)' }}><Trash2 className="w-3 h-3" /></button>
                  </div>
                </div>

                {room.expanded && (
                  <div className="p-3 space-y-2">
                    {/* Windows */}
                    {room.windows.map(w => (
                      <div key={w.id} className="rounded-lg p-3" style={{ background: 'var(--raised)', border: w.aiAnalysis ? '1px solid rgba(139,92,246,0.3)' : '1px solid var(--border)' }}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-1.5">
                            <input type="text" value={w.name} onChange={e => updateWindow(room.id, w.id, { name: e.target.value })}
                              className="bg-transparent text-xs font-medium outline-none" style={{ color: 'var(--text-primary)' }} />
                            {w.aiAnalysis && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded-full flex items-center gap-0.5" style={{ background: 'rgba(139,92,246,0.15)', color: '#8B5CF6' }}>
                                <Sparkles className="w-2 h-2" /> AI {w.aiAnalysis.confidence}%
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-xs font-bold font-mono" style={{ color: '#22c55e' }}>${calcWindowPrice(w).toLocaleString()}</span>
                            <button onClick={() => copyWindow(room.id, w.id)} className="p-1 rounded" style={{ color: 'var(--text-muted)' }}><Copy className="w-3 h-3" /></button>
                            <button onClick={() => deleteWindow(room.id, w.id)} className="p-1 rounded" style={{ color: 'var(--text-muted)' }}><Trash2 className="w-3 h-3" /></button>
                          </div>
                        </div>

                        {/* AI Tools Row */}
                        <div className="flex items-center gap-1.5 mb-2">
                          <button onClick={() => openPhotoModal(room.id, w.id, 'window')}
                            className="h-6 px-2 rounded-lg flex items-center gap-1 text-[10px] transition"
                            style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.3)', color: '#8B5CF6' }}>
                            <Camera className="w-3 h-3" /> Measure
                          </button>
                          <button onClick={() => openPhotoModal(room.id, w.id, 'outline')}
                            className="h-6 px-2 rounded-lg flex items-center gap-1 text-[10px] transition"
                            style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.3)', color: '#3b82f6' }}>
                            <Ruler className="w-3 h-3" /> Outline
                          </button>
                          <button onClick={() => openPhotoModal(room.id, w.id, 'mockup')}
                            className="h-6 px-2 rounded-lg flex items-center gap-1 text-[10px] transition"
                            style={{ background: 'rgba(236,72,153,0.1)', border: '1px solid rgba(236,72,153,0.3)', color: '#ec4899' }}>
                            <Palette className="w-3 h-3" /> Mockup
                          </button>
                        </div>
                        {/* Photo strip */}
                        {(w.sourcePhoto || (w.photos?.length ?? 0) > 0) && (
                          <div className="mb-2 flex items-center gap-1.5 overflow-x-auto pb-1">
                            {w.sourcePhoto && (
                              <button onClick={() => { setUploadedImage(w.sourcePhoto!); setShowPhotoModal(true); setPhotoMode('window'); setActiveRoomId(room.id); setActiveItemId(w.id); setAnalysisResult(w.aiAnalysis || null); }}
                                className="shrink-0 rounded-lg overflow-hidden transition hover:opacity-80"
                                style={{ border: '2px solid rgba(139,92,246,0.4)' }}
                                title="Primary photo (AI analyzed)">
                                <img src={w.sourcePhoto} alt="" className="w-10 h-7 object-cover" />
                              </button>
                            )}
                            {(w.photos || []).map((photo, idx) => (
                              <button key={idx} onClick={() => { setUploadedImage(photo); setShowPhotoModal(true); setPhotoMode('window'); setActiveRoomId(room.id); setActiveItemId(w.id); setAnalysisResult(null); }}
                                className="shrink-0 rounded-lg overflow-hidden transition hover:opacity-80"
                                style={{ border: '1px solid var(--glass-border)' }}>
                                <img src={photo} alt="" className="w-10 h-7 object-cover" />
                              </button>
                            ))}
                            <button onClick={() => openPhotoModal(room.id, w.id, 'window')}
                              className="shrink-0 w-10 h-7 rounded-lg flex items-center justify-center transition hover:opacity-80"
                              style={{ border: '1px dashed rgba(139,92,246,0.3)' }}
                              title="Add photo">
                              <Plus className="w-3 h-3" style={{ color: '#8B5CF6' }} />
                            </button>
                            <span className="shrink-0 text-[9px]" style={{ color: 'var(--text-muted)' }}>
                              {1 + (w.photos?.length || 0)} photo{(w.photos?.length || 0) > 0 ? 's' : ''}
                            </span>
                          </div>
                        )}

                        <div className="grid grid-cols-5 gap-1.5">
                          {/* Width, Height, Qty */}
                          {[{ l: 'Width (in)', k: 'width', v: w.width }, { l: 'Height (in)', k: 'height', v: w.height }, { l: 'Qty', k: 'quantity', v: w.quantity }].map(f => (
                            <div key={f.k}>
                              <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>{f.l}</label>
                              <input type="number" value={f.v} onChange={e => updateWindow(room.id, w.id, { [f.k]: Number(e.target.value) })}
                                className="w-full h-7 rounded-lg px-2 text-[11px] outline-none" style={inputStyle} />
                            </div>
                          ))}
                          {/* Treatment */}
                          <div>
                            <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>Treatment</label>
                            <select value={w.treatmentType} onChange={e => updateWindow(room.id, w.id, { treatmentType: e.target.value })}
                              className="w-full h-7 rounded-lg px-1 text-[10px] outline-none" style={selectStyle}>
                              {TREATMENT_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                            </select>
                          </div>
                          {/* Lining, Hardware, Motor, Mount, Draw */}
                          {[
                            { l: 'Lining', k: 'liningType', v: w.liningType, opts: LINING_OPTIONS },
                            { l: 'Hardware', k: 'hardwareType', v: w.hardwareType, opts: HARDWARE_OPTIONS },
                            { l: 'HW Color', k: 'hardwareColor', v: w.hardwareColor || 'brushed-nickel', opts: HW_COLOR_OPTIONS },
                            { l: 'Motor', k: 'motorization', v: w.motorization, opts: MOTOR_OPTIONS },
                            { l: 'Mount', k: 'mountType', v: w.mountType, opts: MOUNT_OPTIONS },
                            { l: 'Draw', k: 'drawDirection', v: w.drawDirection || 'center', opts: DRAW_OPTIONS },
                          ].map(f => (
                            <div key={f.k}>
                              <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>{f.l}</label>
                              <select value={f.v} onChange={e => updateWindow(room.id, w.id, { [f.k]: e.target.value })}
                                className="w-full h-7 rounded-lg px-1 text-[10px] outline-none" style={selectStyle}>
                                {f.opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                              </select>
                            </div>
                          ))}
                          {/* Fabric Color */}
                          <div>
                            <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>Fabric Color</label>
                            <input type="text" value={w.fabricColor || ''} placeholder="e.g. Ivory" onChange={e => updateWindow(room.id, w.id, { fabricColor: e.target.value })}
                              className="w-full h-7 rounded-lg px-2 text-[10px] outline-none" style={inputStyle} />
                          </div>
                        </div>

                        {/* ── Estimating Controls: Fabric Grade, Fullness, Labor Rate ── */}
                        <div className="mt-2 rounded-lg p-2.5" style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}>
                          <div className="flex items-center gap-1.5 mb-2">
                            <Scissors className="w-3 h-3" style={{ color: '#F59E0B' }} />
                            <span className="text-[10px] font-semibold" style={{ color: '#F59E0B' }}>Estimating</span>
                          </div>
                          {/* Fabric Grade */}
                          <div className="mb-2">
                            <label className="block text-[9px] mb-1" style={{ color: 'var(--text-muted)' }}>Fabric Grade</label>
                            <div className="flex gap-1">
                              {FABRIC_GRADES.map(g => (
                                <button key={g.grade} onClick={() => updateWindow(room.id, w.id, { fabricGrade: g.grade })}
                                  className="flex-1 py-1 rounded-lg text-[9px] font-medium transition text-center"
                                  style={{
                                    background: w.fabricGrade === g.grade ? 'rgba(245,158,11,0.2)' : 'var(--raised)',
                                    border: `1px solid ${w.fabricGrade === g.grade ? '#F59E0B' : 'var(--border)'}`,
                                    color: w.fabricGrade === g.grade ? '#F59E0B' : 'var(--text-secondary)',
                                  }}>
                                  {g.grade}<br/><span className="text-[8px] opacity-70">{g.label}</span>
                                </button>
                              ))}
                            </div>
                          </div>
                          {/* Fullness + Labor sliders */}
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <div className="flex justify-between mb-0.5">
                                <label className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Fullness</label>
                                <span className="text-[9px] font-mono font-bold" style={{ color: '#F59E0B' }}>{(w.fullness || 2.5).toFixed(1)}x</span>
                              </div>
                              <input type="range" min="1.5" max="3.5" step="0.1" value={w.fullness || 2.5}
                                onChange={e => updateWindow(room.id, w.id, { fullness: parseFloat(e.target.value) })}
                                className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                                style={{ accentColor: '#F59E0B' }} />
                            </div>
                            <div>
                              <div className="flex justify-between mb-0.5">
                                <label className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Labor Rate</label>
                                <span className="text-[9px] font-mono font-bold" style={{ color: '#F59E0B' }}>${w.laborRate || 65}/hr</span>
                              </div>
                              <input type="range" min="40" max="120" step="5" value={w.laborRate || 65}
                                onChange={e => updateWindow(room.id, w.id, { laborRate: parseInt(e.target.value) })}
                                className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                                style={{ accentColor: '#F59E0B' }} />
                            </div>
                          </div>
                          {/* Yardage + Price Breakdown */}
                          {(() => {
                            const y = calcYardage(w);
                            return (
                              <div className="grid grid-cols-2 gap-2 mt-2">
                                {/* Yardage Calculator */}
                                <div className="rounded-lg p-2" style={{ background: 'var(--raised)' }}>
                                  <p className="text-[8px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Yardage</p>
                                  <div className="space-y-0.5 text-[9px]">
                                    <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Panels</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>{y.panelsNeeded}</span></div>
                                    <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Per window</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>{y.yardagePerWindow} yd</span></div>
                                    <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Waste (15%)</span><span className="font-mono" style={{ color: 'var(--text-muted)' }}>{y.wasteYardage} yd</span></div>
                                    <div className="flex justify-between font-semibold pt-0.5" style={{ borderTop: '1px solid var(--border)' }}>
                                      <span style={{ color: '#F59E0B' }}>Total</span><span className="font-mono" style={{ color: '#F59E0B' }}>{y.totalYardage} yd</span>
                                    </div>
                                  </div>
                                </div>
                                {/* Price Breakdown */}
                                <div className="rounded-lg p-2" style={{ background: 'var(--raised)' }}>
                                  <p className="text-[8px] font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Breakdown</p>
                                  <div className="space-y-0.5 text-[9px]">
                                    <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Materials</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>${y.materialsTotal}</span></div>
                                    <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Labor</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>${y.laborTotal}</span></div>
                                    <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Hardware</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>${y.hardwareTotal}</span></div>
                                    <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Tax</span><span className="font-mono" style={{ color: 'var(--text-muted)' }}>${y.tax}</span></div>
                                    <div className="flex justify-between font-semibold pt-0.5" style={{ borderTop: '1px solid var(--border)' }}>
                                      <span style={{ color: '#22c55e' }}>Total</span><span className="font-mono" style={{ color: '#22c55e' }}>${y.total}</span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          })()}
                        </div>

                        {/* ── Inline Measurement Outline — clickable, PDF-able, sharable ── */}
                        {w.width > 0 && w.height > 0 && (
                          <div className="mt-2 rounded-lg p-2" style={{ background: 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.12)' }}>
                            <div className="flex items-center justify-between mb-1.5">
                              <div className="flex items-center gap-1.5">
                                <Ruler className="w-3 h-3" style={{ color: '#3b82f6' }} />
                                <span className="text-[9px] font-semibold" style={{ color: '#D4AF37' }}>Window Outline</span>
                              </div>
                              <div className="flex items-center gap-1">
                                {/* Expand outline in popup */}
                                <button onClick={() => setExpandedOutline(w)}
                                  className="text-[8px] px-1.5 py-0.5 rounded flex items-center gap-0.5 transition"
                                  style={{ background: 'rgba(212,175,55,0.1)', color: '#D4AF37', border: '1px solid rgba(212,175,55,0.25)' }}>
                                  <Ruler className="w-2.5 h-2.5" /> Expand
                                </button>
                                {/* Share outline */}
                                <button onClick={() => {
                                  const draw = DRAW_OPTIONS.find(([v]) => v === w.drawDirection)?.[1] || 'Center';
                                  const text = `Window: ${w.name}\n${w.width}" W × ${w.height}" H\nMount: ${w.mountType}\nTreatment: ${w.treatmentType}\nDraw: ${draw}\nFabric: ${w.fabricColor || 'TBD'}\nQty: ${w.quantity}`;
                                  if (navigator.share) { navigator.share({ title: `${w.name} Outline`, text }).catch(() => {}); }
                                  else { navigator.clipboard.writeText(text).then(() => alert('Outline copied!')); }
                                }}
                                  className="text-[8px] px-1.5 py-0.5 rounded flex items-center gap-0.5 transition"
                                  style={{ background: 'rgba(212,175,55,0.1)', color: '#D4AF37', border: '1px solid rgba(212,175,55,0.25)' }}>
                                  <Share2 className="w-2.5 h-2.5" /> Share
                                </button>
                              </div>
                            </div>
                            <svg viewBox="0 0 200 150" className="w-full cursor-pointer" style={{ maxHeight: 110 }}
                              onClick={() => setExpandedOutline(w)}>
                              {/* Window frame */}
                              <rect x="40" y="15" width="120" height="100" rx="2" fill="rgba(212,175,55,0.04)" stroke="#D4AF37" strokeWidth="1.5" />
                              {/* Window panes (cross) */}
                              <line x1="100" y1="15" x2="100" y2="115" stroke="rgba(212,175,55,0.2)" strokeWidth="0.5" />
                              <line x1="40" y1="65" x2="160" y2="65" stroke="rgba(212,175,55,0.2)" strokeWidth="0.5" />
                              {/* Draw direction arrows */}
                              {(w.drawDirection === 'center' || !w.drawDirection) && <>
                                <text x="70" y="72" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="10">←</text>
                                <text x="130" y="72" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="10">→</text>
                              </>}
                              {w.drawDirection === 'left' && <text x="70" y="72" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="12">←</text>}
                              {w.drawDirection === 'right' && <text x="130" y="72" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="12">→</text>}
                              {w.drawDirection === 'one-way-l' && <text x="80" y="72" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="12">⟵</text>}
                              {w.drawDirection === 'one-way-r' && <text x="120" y="72" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="12">⟶</text>}
                              {/* Width dimension */}
                              <line x1="40" y1="128" x2="160" y2="128" stroke="#D4AF37" strokeWidth="0.8" markerEnd={`url(#arR${w.id})`} markerStart={`url(#arL${w.id})`} />
                              <text x="100" y="137" textAnchor="middle" fill="#D4AF37" fontSize="9" fontWeight="bold" fontFamily="monospace">{w.width}"</text>
                              {/* Height dimension */}
                              <line x1="172" y1="15" x2="172" y2="115" stroke="#D4AF37" strokeWidth="0.8" />
                              <text x="185" y="70" textAnchor="middle" fill="#D4AF37" fontSize="9" fontWeight="bold" fontFamily="monospace" transform="rotate(90,185,70)">{w.height}"</text>
                              {/* Mount type label */}
                              <text x="100" y="10" textAnchor="middle" fill="rgba(212,175,55,0.6)" fontSize="7" fontFamily="sans-serif">{w.mountType} mount</text>
                              {/* Treatment + fabric color label */}
                              <text x="100" y="50" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="7" fontFamily="sans-serif">{w.treatmentType}{w.fabricColor ? ` · ${w.fabricColor}` : ''}</text>
                              {/* Qty badge */}
                              {w.quantity > 1 && (
                                <>
                                  <rect x="2" y="2" width="28" height="14" rx="7" fill="rgba(212,175,55,0.15)" />
                                  <text x="16" y="12" textAnchor="middle" fill="#D4AF37" fontSize="8" fontWeight="bold">×{w.quantity}</text>
                                </>
                              )}
                              {/* Arrow markers */}
                              <defs>
                                <marker id={`arR${w.id}`} markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto"><path d="M0,0 L6,2 L0,4" fill="#D4AF37"/></marker>
                                <marker id={`arL${w.id}`} markerWidth="6" markerHeight="4" refX="1" refY="2" orient="auto"><path d="M6,0 L0,2 L6,4" fill="#D4AF37"/></marker>
                              </defs>
                            </svg>
                          </div>
                        )}

                        {/* AI Recommendations */}
                        {w.aiAnalysis && (
                          <div className="mt-2 p-2 rounded-lg" style={{ background: 'rgba(139,92,246,0.05)', border: '1px solid rgba(139,92,246,0.15)' }}>
                            <div className="flex items-center gap-1.5 mb-1">
                              <Lightbulb className="w-3 h-3" style={{ color: '#8B5CF6' }} />
                              <span className="text-[10px] font-medium" style={{ color: '#8B5CF6' }}>AI: {w.aiAnalysis.windowType}</span>
                            </div>
                            {w.aiAnalysis.recommendations.map((r, i) => (
                              <div key={i} className="flex items-start gap-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                                <Check className="w-2.5 h-2.5 shrink-0 mt-0.5" style={{ color: '#8B5CF6' }} /><span>{r}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}

                    {/* Upholstery */}
                    {room.upholstery.map(u => (
                      <div key={u.id} className="rounded-lg p-3" style={{ background: 'var(--raised)', border: u.aiAnalysis ? '1px solid rgba(212,175,55,0.3)' : '1px solid var(--border)' }}>
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-1.5">
                            <input type="text" value={u.name} onChange={e => updateUpholstery(room.id, u.id, { name: e.target.value })}
                              className="bg-transparent text-xs font-medium outline-none" style={{ color: 'var(--text-primary)' }} />
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(212,175,55,0.15)', color: 'var(--gold)' }}>UPHOLSTERY</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <span className="text-xs font-bold font-mono" style={{ color: '#22c55e' }}>${calcUpholsteryPrice(u).toLocaleString()}</span>
                            <button onClick={() => deleteUpholstery(room.id, u.id)} className="p-1 rounded" style={{ color: 'var(--text-muted)' }}><Trash2 className="w-3 h-3" /></button>
                          </div>
                        </div>
                        {/* Photo strip + AI mockup */}
                        {(u.sourcePhoto || (u.photos?.length ?? 0) > 0 || u.aiAnalysis?.generated_image) && (
                          <div className="mb-2 flex items-center gap-1.5 overflow-x-auto pb-1">
                            {u.sourcePhoto && (
                              <button onClick={() => { setUploadedImage(u.sourcePhoto!); setShowPhotoModal(true); setPhotoMode('upholstery'); setActiveRoomId(room.id); setActiveItemId(u.id); setAnalysisResult(u.aiAnalysis || null); }}
                                className="shrink-0 rounded-lg overflow-hidden transition hover:opacity-80"
                                style={{ border: '2px solid rgba(212,175,55,0.4)' }}
                                title="Primary photo (AI analyzed)">
                                <img src={u.sourcePhoto} alt="" className="w-10 h-7 object-cover" />
                              </button>
                            )}
                            {(u.photos || []).map((photo, idx) => (
                              <button key={idx} onClick={() => { setUploadedImage(photo); setShowPhotoModal(true); setPhotoMode('upholstery'); setActiveRoomId(room.id); setActiveItemId(u.id); setAnalysisResult(null); }}
                                className="shrink-0 rounded-lg overflow-hidden transition hover:opacity-80"
                                style={{ border: '1px solid var(--glass-border)' }}>
                                <img src={photo} alt="" className="w-10 h-7 object-cover" />
                              </button>
                            ))}
                            {u.aiAnalysis?.generated_image && (
                              <a href={u.aiAnalysis.generated_image} target="_blank" rel="noreferrer"
                                className="shrink-0 rounded-lg overflow-hidden"
                                style={{ border: '2px solid rgba(139,92,246,0.4)' }}
                                title="AI Generated Mockup">
                                <img src={u.aiAnalysis.generated_image} alt="" className="w-10 h-7 object-cover" />
                              </a>
                            )}
                            <button onClick={() => openPhotoModal(room.id, u.id, 'upholstery')}
                              className="shrink-0 w-10 h-7 rounded-lg flex items-center justify-center transition hover:opacity-80"
                              style={{ border: '1px dashed rgba(212,175,55,0.3)' }}
                              title="Add photo">
                              <Plus className="w-3 h-3" style={{ color: 'var(--gold)' }} />
                            </button>
                            <span className="shrink-0 text-[9px]" style={{ color: 'var(--text-muted)' }}>
                              {(u.sourcePhoto ? 1 : 0) + (u.photos?.length || 0)} photo{((u.sourcePhoto ? 1 : 0) + (u.photos?.length || 0)) !== 1 ? 's' : ''}
                            </span>
                          </div>
                        )}
                        <div className="grid grid-cols-5 gap-1.5">
                          <div>
                            <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>AI Estimate</label>
                            <button onClick={() => openPhotoModal(room.id, u.id, 'upholstery')}
                              className="w-full h-7 rounded-lg flex items-center justify-center gap-1 text-[10px] transition"
                              style={{ background: 'rgba(212,175,55,0.1)', border: '1px solid rgba(212,175,55,0.3)', color: 'var(--gold)' }}>
                              <Camera className="w-3 h-3" /> Photo
                            </button>
                          </div>
                          <div>
                            <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>Type</label>
                            <select value={u.furnitureType} onChange={e => {
                              const ft = e.target.value;
                              const defs = FURNITURE_DEFAULTS[ft] || FURNITURE_DEFAULTS['sofa'];
                              updateUpholstery(room.id, u.id, {
                                furnitureType: ft,
                                fabricYards: defs.yards, cushionCount: defs.cushions,
                                width: defs.width, depth: defs.depth, height: defs.height,
                              });
                            }}
                              className="w-full h-7 rounded-lg px-1 text-[10px] outline-none" style={selectStyle}>
                              {FURNITURE_TYPES.map(t => <option key={t} value={t}>{t.replace('-', ' ')}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>Yards</label>
                            <input type="number" value={u.fabricYards} onChange={e => updateUpholstery(room.id, u.id, { fabricYards: Number(e.target.value) })}
                              className="w-full h-7 rounded-lg px-2 text-[11px] outline-none" style={inputStyle} />
                          </div>
                          <div>
                            <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>Fabric</label>
                            <select value={u.fabricType} onChange={e => updateUpholstery(room.id, u.id, { fabricType: e.target.value as any })}
                              className="w-full h-7 rounded-lg px-1 text-[10px] outline-none" style={selectStyle}>
                              <option value="plain">Plain $22/yd</option>
                              <option value="patterned">Pattern $50/yd</option>
                              <option value="leather">Leather $110/yd</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>Labor</label>
                            <select value={u.laborType} onChange={e => updateUpholstery(room.id, u.id, { laborType: e.target.value as any })}
                              className="w-full h-7 rounded-lg px-1 text-[10px] outline-none" style={selectStyle}>
                              <option value="standard">Standard $62</option>
                              <option value="tufted">Tufted $78</option>
                              <option value="channeled">Channel $72</option>
                              <option value="leather">Leather $100</option>
                            </select>
                          </div>
                        </div>
                        {/* AI Analysis summary (collapsed by default) */}
                        {u.aiAnalysis && (
                          <details className="mt-2">
                            <summary className="text-[10px] font-medium cursor-pointer flex items-center gap-1" style={{ color: 'var(--gold)' }}>
                              <Sparkles className="w-3 h-3" /> AI Analysis — {u.aiAnalysis.style || u.aiAnalysis.furnitureType} ({u.aiAnalysis.confidence || 0}% confidence)
                            </summary>
                            <div className="mt-1.5 p-2 rounded-lg space-y-1" style={{ background: 'rgba(212,175,55,0.05)', border: '1px solid rgba(212,175,55,0.15)' }}>
                              {u.aiAnalysis.style && (
                                <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                                  <span style={{ color: 'var(--text-muted)' }}>Style:</span> {u.aiAnalysis.style}
                                </p>
                              )}
                              {u.aiAnalysis.cushions && (
                                <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                                  <span style={{ color: 'var(--text-muted)' }}>Cushions:</span> {u.aiAnalysis.cushions.seat} seat, {u.aiAnalysis.cushions.back} back{u.aiAnalysis.cushions.throw_pillows ? `, ${u.aiAnalysis.cushions.throw_pillows} throw` : ''}
                                </p>
                              )}
                              <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                                <span style={{ color: 'var(--text-muted)' }}>Fabric:</span> {u.aiAnalysis.fabricYardsPlain || u.fabricYards} yd plain{u.aiAnalysis.fabricYardsPatterned ? `, ${u.aiAnalysis.fabricYardsPatterned} yd patterned` : ''}
                              </p>
                              {u.aiAnalysis.laborCostLow && (
                                <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>
                                  <span style={{ color: 'var(--text-muted)' }}>Est. labor:</span> ${u.aiAnalysis.laborCostLow?.toLocaleString()} — ${u.aiAnalysis.laborCostHigh?.toLocaleString()}
                                </p>
                              )}
                              {u.aiAnalysis.newFoamRecommended && (
                                <p className="text-[10px]" style={{ color: '#f59e0b' }}>New cushion foam recommended</p>
                              )}
                              {u.aiAnalysis.questions && u.aiAnalysis.questions.length > 0 && (
                                <div className="mt-1">
                                  <p className="text-[9px] font-semibold" style={{ color: 'var(--text-muted)' }}>Questions for customer:</p>
                                  {u.aiAnalysis.questions.slice(0, 3).map((q: string, qi: number) => (
                                    <p key={qi} className="text-[10px] pl-2" style={{ color: 'var(--text-secondary)' }}>• {q}</p>
                                  ))}
                                </div>
                              )}
                            </div>
                          </details>
                        )}
                      </div>
                    ))}

                    {/* Add buttons */}
                    <div className="flex gap-2">
                      <button onClick={() => addWindow(room.id)}
                        className="flex-1 py-2 rounded-lg text-[11px] flex items-center justify-center gap-1.5 transition"
                        style={{ border: '1px dashed var(--border)', color: 'var(--text-muted)' }}>
                        <Plus className="w-3 h-3" /> Add Window
                      </button>
                      <button onClick={() => addUpholstery(room.id)}
                        className="flex-1 py-2 rounded-lg text-[11px] flex items-center justify-center gap-1.5 transition"
                        style={{ border: '1px dashed var(--border)', color: 'var(--text-muted)' }}>
                        <Plus className="w-3 h-3" /> Add Upholstery
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Add Room */}
            <button onClick={addRoom}
              className="w-full py-2.5 rounded-xl text-[11px] flex items-center justify-center gap-1.5 transition"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
              <Plus className="w-3.5 h-3.5" /> Add Room
            </button>
          </>
        )}

        {/* ── CUSTOMER TAB ───────────────────────────────── */}
        {tab === 'customer' && (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <input placeholder="Customer name *" value={customer.name} onChange={e => setCustomer({ ...customer, name: e.target.value })}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              <input placeholder="Email" value={customer.email} onChange={e => setCustomer({ ...customer, email: e.target.value })}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              <input placeholder="Phone" value={customer.phone} onChange={e => setCustomer({ ...customer, phone: e.target.value })}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
              <input placeholder="Project name" value={projectName} onChange={e => setProjectName(e.target.value)}
                className="rounded-lg px-3 py-2 text-xs outline-none" style={inputStyle} />
            </div>
            <textarea placeholder="Address" value={customer.address} onChange={e => setCustomer({ ...customer, address: e.target.value })}
              className="w-full rounded-lg px-3 py-2 text-xs outline-none resize-none" style={inputStyle} rows={2} />
          </div>
        )}

        {/* ── SUMMARY TAB ────────────────────────────────── */}
        {tab === 'summary' && (() => {
          // Aggregate price breakdown across all windows
          const allYardages = rooms.flatMap(r => r.windows.map(w => calcYardage(w)));
          const totalMaterials = allYardages.reduce((s, y) => s + y.materialsTotal, 0);
          const totalLabor = allYardages.reduce((s, y) => s + y.laborTotal, 0);
          const totalHardware = allYardages.reduce((s, y) => s + y.hardwareTotal, 0);
          const totalYardageAll = allYardages.reduce((s, y) => s + y.totalYardage, 0);
          const totalTax = allYardages.reduce((s, y) => s + y.tax, 0);
          const uphTotal = rooms.reduce((s, r) => s + r.upholstery.reduce((us, u) => us + calcUpholsteryPrice(u), 0), 0);
          return (
          <div className="space-y-3">
            <div className="rounded-xl p-4 space-y-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <h3 className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>Quote Summary</h3>
              <div className="flex items-center gap-2">
                <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  Customer: <button onClick={() => setTab('customer')} className="font-medium transition hover:underline" style={{ color: 'var(--gold)', cursor: 'pointer' }}>{customer.name || 'Not set'}</button>
                </p>
                {(!customer.name || customer.name.startsWith('Customer ')) && (
                  <button onClick={() => setTab('customer')} className="text-[8px] px-1.5 py-0.5 rounded-full font-medium animate-pulse"
                    style={{ background: 'rgba(245,158,11,0.15)', color: '#F59E0B' }}>
                    Complete Info
                  </button>
                )}
              </div>
              <div className="h-px" style={{ background: 'var(--border)' }} />
              {rooms.map(r => (
                <div key={r.id}>
                  <div className="flex justify-between py-1 text-[11px]">
                    <span style={{ color: 'var(--text-secondary)' }}>{r.name} ({r.windows.length} win{r.upholstery.length > 0 ? `, ${r.upholstery.length} uph` : ''})</span>
                    <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>${calcRoomTotal(r).toLocaleString()}</span>
                  </div>
                  {r.windows.map(w => {
                    const y = calcYardage(w);
                    return (
                      <div key={w.id} className="py-0.5 pl-3">
                        <div className="flex justify-between text-[10px]">
                          <span style={{ color: 'var(--text-muted)' }}>
                            {w.name} — {w.treatmentType} {w.width}"×{w.height}" ×{w.quantity} · {w.fabricGrade}
                            {w.aiAnalysis && <span className="ml-1 px-1 py-0.5 rounded-full text-[8px]" style={{ background: 'rgba(139,92,246,0.12)', color: '#8B5CF6' }}>AI {w.aiAnalysis.confidence}%</span>}
                            {(w.sourcePhoto || (w.photos?.length ?? 0) > 0) && <span className="ml-1 text-[8px]" style={{ color: 'var(--text-muted)' }}>{(w.sourcePhoto ? 1 : 0) + (w.photos?.length || 0)} pic</span>}
                          </span>
                          <span className="font-mono" style={{ color: 'var(--text-muted)' }}>${y.total}</span>
                        </div>
                        <div className="flex gap-3 text-[9px] pl-2" style={{ color: 'var(--text-muted)', opacity: 0.7 }}>
                          <span>{y.totalYardage} yd</span>
                          <span>Mat ${y.materialsTotal}</span>
                          <span>Lab ${y.laborTotal}</span>
                          <span>Hdw ${y.hardwareTotal}</span>
                        </div>
                      </div>
                    );
                  })}
                  {r.upholstery.map(u => (
                    <div key={u.id} className="flex justify-between py-0.5 pl-3 text-[10px]">
                      <span style={{ color: 'var(--text-muted)' }}>
                        {u.name} — {u.furnitureType} ({u.fabricYards}yd)
                        {u.aiAnalysis && <span className="ml-1 px-1 py-0.5 rounded-full text-[8px]" style={{ background: 'rgba(212,175,55,0.12)', color: 'var(--gold)' }}>AI {u.aiAnalysis.confidence}%</span>}
                        {(u.sourcePhoto || (u.photos?.length ?? 0) > 0) && <span className="ml-1 text-[8px]" style={{ color: 'var(--text-muted)' }}>{(u.sourcePhoto ? 1 : 0) + (u.photos?.length || 0)} pic</span>}
                      </span>
                      <span className="font-mono" style={{ color: 'var(--text-muted)' }}>${calcUpholsteryPrice(u).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              ))}
              <div className="h-px" style={{ background: 'var(--gold)', opacity: 0.3 }} />
              <div className="flex justify-between text-sm font-bold pt-1">
                <span style={{ color: 'var(--gold)' }}>Grand Total</span>
                <span className="font-mono" style={{ color: 'var(--gold)' }}>${grandTotal.toLocaleString()}</span>
              </div>
            </div>

            {/* ── Aggregate Price Breakdown ── */}
            <div className="rounded-xl p-4" style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}>
              <div className="flex items-center gap-1.5 mb-2">
                <Calculator className="w-3.5 h-3.5" style={{ color: '#F59E0B' }} />
                <h3 className="text-xs font-semibold" style={{ color: '#F59E0B' }}>Price Breakdown</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1 text-[11px]">
                  <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Total Yardage</span><span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{Math.ceil(totalYardageAll * 10) / 10} yd</span></div>
                  <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Materials</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>${totalMaterials.toLocaleString()}</span></div>
                  <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Labor</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>${totalLabor.toLocaleString()}</span></div>
                </div>
                <div className="space-y-1 text-[11px]">
                  <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Hardware</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>${totalHardware.toLocaleString()}</span></div>
                  {uphTotal > 0 && <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Upholstery</span><span className="font-mono" style={{ color: 'var(--text-primary)' }}>${uphTotal.toLocaleString()}</span></div>}
                  <div className="flex justify-between"><span style={{ color: 'var(--text-muted)' }}>Tax (8.25%)</span><span className="font-mono" style={{ color: 'var(--text-muted)' }}>${totalTax.toLocaleString()}</span></div>
                </div>
              </div>
              <div className="h-px mt-2 mb-1" style={{ background: '#F59E0B', opacity: 0.3 }} />
              <div className="flex justify-between text-sm font-bold">
                <span style={{ color: '#F59E0B' }}>Subtotal (Windows)</span>
                <span className="font-mono" style={{ color: '#F59E0B' }}>${(totalMaterials + totalLabor + totalHardware + totalTax).toLocaleString()}</span>
              </div>
            </div>

            {/* ── AI Analysis Summary ── */}
            {(() => {
              const allAI = rooms.flatMap(r => [
                ...r.windows.filter(w => w.aiAnalysis).map(w => ({ confidence: w.aiAnalysis!.confidence })),
                ...r.upholstery.filter(u => u.aiAnalysis).map(u => ({ confidence: u.aiAnalysis!.confidence })),
              ]);
              const photoCount = rooms.reduce((s, r) => s +
                r.windows.reduce((ws, w) => ws + (w.sourcePhoto ? 1 : 0) + (w.photos?.length || 0), 0) +
                r.upholstery.reduce((us, u) => us + (u.sourcePhoto ? 1 : 0) + (u.photos?.length || 0), 0)
              , 0);
              if (allAI.length === 0 && photoCount === 0) return null;
              const avgConf = allAI.length > 0 ? Math.round(allAI.reduce((s, a) => s + a.confidence, 0) / allAI.length) : 0;
              return (
                <div className="rounded-xl p-3" style={{ background: 'rgba(139,92,246,0.06)', border: '1px solid rgba(139,92,246,0.15)' }}>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Brain className="w-3.5 h-3.5" style={{ color: '#8B5CF6' }} />
                    <span className="text-xs font-semibold" style={{ color: '#8B5CF6' }}>AI Analysis Summary</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
                    <div>
                      <p className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>{avgConf > 0 ? `${avgConf}%` : '—'}</p>
                      <p style={{ color: 'var(--text-muted)' }}>Avg Confidence</p>
                    </div>
                    <div>
                      <p className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>{photoCount}</p>
                      <p style={{ color: 'var(--text-muted)' }}>Photos</p>
                    </div>
                    <div>
                      <p className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>{allAI.length}</p>
                      <p style={{ color: 'var(--text-muted)' }}>AI Estimates</p>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* ── Summary Action Buttons: Save, PDF, Share ── */}
            <div className="flex gap-2 pt-2">
              <button onClick={saveQuote} disabled={saving}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-[11px] font-semibold transition"
                style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
                {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                {savedQuote ? 'Update Quote' : 'Save Quote'}
              </button>
              <button onClick={downloadPdf} disabled={saving || generatingPdf}
                className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-[11px] font-semibold transition"
                style={{ background: 'rgba(139,92,246,0.12)', color: '#8B5CF6', border: '1px solid rgba(139,92,246,0.3)' }}>
                {generatingPdf ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} PDF
              </button>
              <button onClick={() => {
                const lines = rooms.flatMap(r => [
                  `${r.name}:`,
                  ...r.windows.map(w => `  ${w.name} — ${w.treatmentType} ${w.width}"×${w.height}" ×${w.quantity} · $${calcYardage(w).total}`),
                  ...r.upholstery.map(u => `  ${u.name} — ${u.furnitureType} · $${calcUpholsteryPrice(u).toLocaleString()}`),
                ]);
                const text = `Quote${savedQuote ? ` ${savedQuote.quote_number}` : ''} for ${customer.name || 'Customer'}\n${lines.join('\n')}\n\nGrand Total: $${grandTotal.toLocaleString()}`;
                if (navigator.share) { navigator.share({ title: 'Quote Summary', text }).catch(() => {}); }
                else { navigator.clipboard.writeText(text).then(() => alert('Summary copied!')); }
              }}
                className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-[11px] font-semibold transition"
                style={{ background: 'rgba(212,175,55,0.12)', color: '#D4AF37', border: '1px solid rgba(212,175,55,0.3)' }}>
                <Share2 className="w-3.5 h-3.5" /> Share
              </button>
            </div>
          </div>
          );
        })()}

        {/* ── HISTORY TAB ──────────────────────────────── */}
        {tab === 'history' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" style={{ color: '#8B5CF6' }} />
                <h3 className="text-xs font-semibold" style={{ color: '#8B5CF6' }}>Saved Quotes</h3>
              </div>
              <button onClick={loadQuoteHistory} disabled={loadingHistory}
                className="text-[10px] px-2 py-1 rounded-lg transition"
                style={{ color: 'var(--text-muted)' }}>
                {loadingHistory ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Refresh'}
              </button>
            </div>

            {loadingHistory ? (
              <div className="flex items-center justify-center py-10">
                <Loader2 className="w-6 h-6 animate-spin" style={{ color: '#8B5CF6' }} />
              </div>
            ) : quoteHistory.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 gap-2">
                <FileText className="w-8 h-8" style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No saved quotes yet</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {quoteHistory.map((q: any) => {
                  const created = q.created_at ? new Date(q.created_at) : null;
                  const dateStr = created ? created.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
                  const timeStr = created ? created.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : '';
                  const isActive = savedQuote?.id === q.id;
                  const statusColors: Record<string, string> = { draft: 'var(--text-muted)', sent: '#3b82f6', accepted: '#22c55e', rejected: '#ef4444', expired: '#f59e0b', invoiced: '#8B5CF6' };
                  return (
                    <button key={q.id} onClick={() => loadQuoteById(q.id)}
                      className="w-full text-left rounded-xl p-3 transition"
                      style={{
                        background: isActive ? 'rgba(212,175,55,0.08)' : 'var(--surface)',
                        border: `1px solid ${isActive ? 'var(--gold-border)' : 'var(--border)'}`,
                      }}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold font-mono" style={{ color: isActive ? 'var(--gold)' : '#8B5CF6' }}>{q.quote_number}</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded-full capitalize"
                            style={{ background: `${statusColors[q.status] || 'var(--text-muted)'}20`, color: statusColors[q.status] || 'var(--text-muted)' }}>
                            {q.status}
                          </span>
                          {isActive && <span className="text-[8px] px-1 py-0.5 rounded-full" style={{ background: 'var(--gold-pale)', color: 'var(--gold)' }}>Current</span>}
                        </div>
                        <span className="text-xs font-bold font-mono" style={{ color: 'var(--gold)' }}>${(q.total || 0).toLocaleString()}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{q.customer_name || 'No customer'}{q.project_name ? ` — ${q.project_name}` : ''}</span>
                        <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>{dateStr} {timeStr}</span>
                      </div>
                      {q.rooms?.length > 0 && (
                        <div className="flex gap-2 mt-1">
                          {q.rooms.map((r: any, i: number) => (
                            <span key={i} className="text-[8px] px-1.5 py-0.5 rounded-full" style={{ background: 'var(--raised)', color: 'var(--text-muted)' }}>
                              {r.name} ({(r.windows?.length || 0)} win)
                            </span>
                          ))}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            )}

            {/* New Quote button */}
            <button onClick={() => {
              setCustomer({ name: '', email: '', phone: '', address: '' });
              setProjectName('');
              setRooms([{ id: 'room-1', name: 'Room 1', expanded: true, windows: [{ id: 'w-1', name: 'Window 1', width: 0, height: 0, quantity: 1, treatmentType: 'Drapery', mountType: 'Inside', liningType: 'Standard', hardwareType: 'Standard Rod', hardwareColor: 'brushed-nickel', motorization: 'None', notes: '', fabricGrade: 'B' as FabricGrade, fullness: 2.5, laborRate: 45, drawDirection: 'center', fabricColor: '' }], upholstery: [] }]);
              setSavedQuote(null);
              setTab('build');
            }}
              className="w-full flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-[11px] font-semibold transition"
              style={{ background: 'rgba(139,92,246,0.12)', color: '#8B5CF6', border: '1px dashed rgba(139,92,246,0.3)' }}>
              <Plus className="w-3.5 h-3.5" /> New Quote
            </button>
          </div>
        )}

        {/* ── PREVIEW TAB ──────────────────────────────── */}
        {tab === 'preview' && (
          <div className="flex flex-col h-full min-h-0 -m-3">
            {/* Preview toolbar */}
            <div className="flex items-center justify-between px-4 py-2 shrink-0" style={{ borderBottom: '1px solid var(--glass-border)', background: 'var(--raised)' }}>
              <div className="flex items-center gap-2">
                <Eye className="w-3.5 h-3.5" style={{ color: 'var(--cyan)' }} />
                <span className="text-[11px] font-semibold" style={{ color: 'var(--cyan)' }}>
                  {savedQuote ? savedQuote.quote_number : 'Preview'}
                </span>
                {savedQuote && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(34,197,94,0.12)', color: '#22c55e' }}>Saved</span>
                )}
              </div>
              <div className="flex items-center gap-1.5">
                {/* Refresh */}
                <button onClick={() => savedQuote && loadPdfPreview(savedQuote.id)} disabled={loadingPreview}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium transition"
                  style={{ color: 'var(--text-secondary)' }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
                  <Loader2 className={`w-3 h-3 ${loadingPreview ? 'animate-spin' : ''}`} /> Refresh
                </button>
                {/* Print */}
                <button onClick={printFromPreview} disabled={!pdfUrl}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-medium transition"
                  style={{ background: 'var(--surface)', color: pdfUrl ? 'var(--text-primary)' : 'var(--text-muted)', border: '1px solid var(--border)' }}>
                  <Printer className="w-3 h-3" /> Print
                </button>
                {/* Download */}
                <button onClick={downloadFromPreview} disabled={!pdfUrl}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-medium transition"
                  style={{ background: 'var(--surface)', color: pdfUrl ? 'var(--purple)' : 'var(--text-muted)', border: '1px solid var(--purple-border)' }}>
                  <Download className="w-3 h-3" /> Download
                </button>
                {/* Share */}
                <div className="relative">
                  <button onClick={() => setShowShareMenu(!showShareMenu)} disabled={!savedQuote}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold transition"
                    style={{ background: savedQuote ? 'var(--cyan)' : 'var(--elevated)', color: savedQuote ? '#0a0a0a' : 'var(--text-muted)' }}>
                    <Share2 className="w-3 h-3" /> Share
                  </button>
                  {showShareMenu && (
                    <div className="absolute right-0 top-full mt-1 w-44 rounded-xl py-1 z-10 shadow-xl"
                      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                      <button onClick={shareViaEmail}
                        className="w-full flex items-center gap-2 px-3 py-2 text-[11px] transition"
                        style={{ color: 'var(--text-primary)' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
                        <Mail className="w-3.5 h-3.5" style={{ color: 'var(--cyan)' }} /> Email to Customer
                      </button>
                      <button onClick={copyQuoteLink}
                        className="w-full flex items-center gap-2 px-3 py-2 text-[11px] transition"
                        style={{ color: 'var(--text-primary)' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
                        <Link className="w-3.5 h-3.5" style={{ color: 'var(--purple)' }} /> Copy Link
                      </button>
                      <button onClick={() => { if (pdfUrl) window.open(pdfUrl, '_blank'); setShowShareMenu(false); }}
                        className="w-full flex items-center gap-2 px-3 py-2 text-[11px] transition"
                        style={{ color: 'var(--text-primary)' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}>
                        <ExternalLink className="w-3.5 h-3.5" style={{ color: 'var(--gold)' }} /> Open in New Tab
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* PDF iframe or loading */}
            <div className="flex-1 min-h-0">
              {loadingPreview ? (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--cyan)' }} />
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Generating PDF preview...</p>
                </div>
              ) : pdfUrl ? (
                <iframe src={pdfUrl} className="w-full h-full" style={{ border: 'none', minHeight: '500px' }} />
              ) : (
                <div className="flex flex-col items-center justify-center h-full gap-3">
                  <Eye className="w-8 h-8" style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>PDF preview will appear here</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ═══ EXPANDED OUTLINE MODAL ═══ */}
      {expandedOutline && (() => {
        const w = expandedOutline;
        const draw = DRAW_OPTIONS.find(([v]) => v === w.drawDirection)?.[1] || 'Center (split)';
        return (
          <div className="fixed inset-0 flex items-center justify-center p-4" style={{ zIndex: 110 }}>
            <div className="absolute inset-0 bg-black/85" onClick={() => setExpandedOutline(null)} />
            <div className="relative rounded-2xl w-full max-w-2xl flex flex-col" style={{ background: 'var(--surface)', border: '1px solid var(--gold-border)', maxHeight: '90vh' }}>
              {/* Header */}
              <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)', background: 'rgba(212,175,55,0.06)' }}>
                <div className="flex items-center gap-2">
                  <Ruler className="w-4 h-4" style={{ color: '#D4AF37' }} />
                  <span className="text-sm font-bold" style={{ color: '#D4AF37' }}>{w.name} — Window Outline</span>
                </div>
                <div className="flex items-center gap-2">
                  {/* PDF Export */}
                  <button onClick={() => {
                    const el = document.getElementById('expanded-outline-print');
                    if (!el) return;
                    const win = window.open('', '_blank', 'width=800,height=600');
                    if (!win) return;
                    win.document.write(`<html><head><title>${w.name} Outline</title><style>body{margin:20px;font-family:sans-serif;background:#fff}svg{width:100%;max-width:700px;display:block;margin:0 auto}.info{max-width:700px;margin:20px auto;font-size:13px;color:#333}.info h2{font-size:18px;color:#D4AF37;margin-bottom:8px}.info table{width:100%;border-collapse:collapse}.info td{padding:4px 8px;border-bottom:1px solid #eee}.info td:first-child{color:#888;width:140px}@media print{body{margin:10px}}</style></head><body>`);
                    win.document.write(el.innerHTML);
                    win.document.write('</body></html>');
                    win.document.close();
                    setTimeout(() => { win.print(); }, 300);
                  }}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition"
                    style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
                    <Download className="w-3 h-3" /> PDF
                  </button>
                  {/* Share */}
                  <button onClick={() => {
                    const text = `${w.name}\n${w.width}" W × ${w.height}" H\nMount: ${w.mountType}\nTreatment: ${w.treatmentType}\nDraw: ${draw}\nFabric: ${w.fabricColor || 'TBD'}\nLining: ${w.liningType}\nHardware: ${w.hardwareType}\nQty: ${w.quantity}${w.notes ? `\nNotes: ${w.notes}` : ''}`;
                    if (navigator.share) { navigator.share({ title: `${w.name} Outline`, text }).catch(() => {}); }
                    else { navigator.clipboard.writeText(text).then(() => alert('Outline copied!')); }
                  }}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition"
                    style={{ background: 'rgba(212,175,55,0.12)', color: '#D4AF37', border: '1px solid rgba(212,175,55,0.3)' }}>
                    <Share2 className="w-3 h-3" /> Share
                  </button>
                  {/* Close */}
                  <button onClick={() => setExpandedOutline(null)}
                    className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-white/10 transition">
                    <X className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} />
                  </button>
                </div>
              </div>
              {/* Body */}
              <div className="flex-1 overflow-y-auto p-6" id="expanded-outline-print">
                {/* Large SVG Diagram */}
                <svg viewBox="0 0 400 320" className="w-full" style={{ maxHeight: 360 }}>
                  {/* Window frame */}
                  <rect x="60" y="30" width="260" height="210" rx="3" fill="rgba(212,175,55,0.04)" stroke="#D4AF37" strokeWidth="2" />
                  {/* Panes */}
                  <line x1="190" y1="30" x2="190" y2="240" stroke="rgba(212,175,55,0.2)" strokeWidth="0.8" />
                  <line x1="60" y1="135" x2="320" y2="135" stroke="rgba(212,175,55,0.2)" strokeWidth="0.8" />
                  {/* Draw direction arrows */}
                  {(w.drawDirection === 'center' || !w.drawDirection) && <>
                    <text x="130" y="142" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="16">←</text>
                    <text x="250" y="142" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="16">→</text>
                  </>}
                  {w.drawDirection === 'left' && <text x="130" y="142" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="18">←</text>}
                  {w.drawDirection === 'right' && <text x="250" y="142" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="18">→</text>}
                  {w.drawDirection === 'one-way-l' && <text x="150" y="142" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="18">⟵</text>}
                  {w.drawDirection === 'one-way-r' && <text x="230" y="142" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="18">⟶</text>}
                  {/* Treatment + fabric label */}
                  <text x="190" y="90" textAnchor="middle" fill="rgba(212,175,55,0.5)" fontSize="11" fontFamily="sans-serif">{w.treatmentType}{w.fabricColor ? ` · ${w.fabricColor}` : ''}</text>
                  {/* Draw label */}
                  <text x="190" y="160" textAnchor="middle" fill="rgba(212,175,55,0.35)" fontSize="9" fontFamily="sans-serif">{draw}</text>
                  {/* Mount type label */}
                  <text x="190" y="22" textAnchor="middle" fill="rgba(212,175,55,0.6)" fontSize="10" fontFamily="sans-serif">{w.mountType} mount</text>
                  {/* Width dimension line */}
                  <line x1="60" y1="265" x2="320" y2="265" stroke="#D4AF37" strokeWidth="1" markerEnd="url(#exArR)" markerStart="url(#exArL)" />
                  <text x="190" y="280" textAnchor="middle" fill="#D4AF37" fontSize="14" fontWeight="bold" fontFamily="monospace">{w.width}"</text>
                  {/* Height dimension line */}
                  <line x1="350" y1="30" x2="350" y2="240" stroke="#D4AF37" strokeWidth="1" />
                  <line x1="345" y1="30" x2="355" y2="30" stroke="#D4AF37" strokeWidth="1" />
                  <line x1="345" y1="240" x2="355" y2="240" stroke="#D4AF37" strokeWidth="1" />
                  <text x="370" y="140" textAnchor="middle" fill="#D4AF37" fontSize="14" fontWeight="bold" fontFamily="monospace" transform="rotate(90,370,140)">{w.height}"</text>
                  {/* Qty badge */}
                  {w.quantity > 1 && <>
                    <rect x="4" y="4" width="42" height="22" rx="11" fill="rgba(212,175,55,0.15)" />
                    <text x="25" y="19" textAnchor="middle" fill="#D4AF37" fontSize="12" fontWeight="bold">×{w.quantity}</text>
                  </>}
                  <defs>
                    <marker id="exArR" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6" fill="#D4AF37"/></marker>
                    <marker id="exArL" markerWidth="8" markerHeight="6" refX="1" refY="3" orient="auto"><path d="M8,0 L0,3 L8,6" fill="#D4AF37"/></marker>
                  </defs>
                </svg>

                {/* Info Table */}
                <div className="info mt-4">
                  <h2 className="text-sm font-bold mb-3" style={{ color: '#D4AF37' }}>{w.name} — Specifications</h2>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1">
                    {[
                      ['Width', `${w.width}"`],
                      ['Height', `${w.height}"`],
                      ['Quantity', `${w.quantity}`],
                      ['Mount Type', w.mountType],
                      ['Treatment', w.treatmentType],
                      ['Draw Direction', draw],
                      ['Fabric Color', w.fabricColor || 'TBD'],
                      ['Fabric Grade', w.fabricGrade],
                      ['Lining', w.liningType],
                      ['Hardware', w.hardwareType],
                      ['Motorization', w.motorization],
                    ].map(([label, val]) => (
                      <div key={label} className="flex justify-between py-1 text-[11px]" style={{ borderBottom: '1px solid var(--border)' }}>
                        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{val}</span>
                      </div>
                    ))}
                  </div>
                  {w.notes && (
                    <div className="mt-3 p-2 rounded-lg text-[11px]" style={{ background: 'rgba(212,175,55,0.06)', border: '1px solid rgba(212,175,55,0.15)', color: 'var(--text-secondary)' }}>
                      <strong style={{ color: '#D4AF37' }}>Notes:</strong> {w.notes}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ═══ PHOTO/AI MODAL ═══ */}
      {showPhotoModal && (
        <div className="fixed inset-0 flex items-center justify-center p-4" style={{ zIndex: 100 }}>
          <div className="absolute inset-0 bg-black/80" />
          <div className="relative rounded-2xl w-full max-w-lg flex flex-col" style={{ background: 'var(--surface)', border: '1px solid var(--border)', maxHeight: '85vh' }}>
            {/* Modal header */}
            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)', background:
              photoMode === 'upholstery' ? 'rgba(212,175,55,0.08)' :
              photoMode === 'outline' ? 'rgba(59,130,246,0.08)' :
              photoMode === 'mockup' ? 'rgba(236,72,153,0.08)' : 'rgba(139,92,246,0.08)' }}>
              <div className="flex items-center gap-2">
                {photoMode === 'outline' ? <Ruler className="w-4 h-4" style={{ color: '#3b82f6' }} /> :
                 photoMode === 'mockup' ? <Palette className="w-4 h-4" style={{ color: '#ec4899' }} /> :
                 <Brain className="w-4 h-4" style={{ color: photoMode === 'upholstery' ? 'var(--gold)' : '#8B5CF6' }} />}
                <span className="text-xs font-semibold" style={{ color:
                  photoMode === 'outline' ? '#3b82f6' :
                  photoMode === 'mockup' ? '#ec4899' :
                  photoMode === 'upholstery' ? 'var(--gold)' : '#8B5CF6' }}>
                  {photoMode === 'outline' ? 'AI Outline & Dimensions Plan' :
                   photoMode === 'mockup' ? 'AI Mockup Studio' :
                   photoMode === 'upholstery' ? 'AI Upholstery Estimation' : 'AI Window Measurement'}
                </span>
              </div>
              <button onClick={closePhotoModal} className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-white/10 transition"><X className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {/* Camera view */}
              {showCamera && (
                <div className="relative mb-3">
                  <video ref={videoRef} autoPlay playsInline className="w-full rounded-xl" />
                  <canvas ref={canvasRef} className="hidden" />
                  <button onClick={capturePhoto} className="absolute bottom-3 left-1/2 -translate-x-1/2 w-12 h-12 bg-white rounded-full flex items-center justify-center">
                    <div className="w-10 h-10 border-4 border-gray-300 rounded-full" />
                  </button>
                </div>
              )}

              {/* Mockup design mode + preferences */}
              {photoMode === 'mockup' && !uploadedImage && !showCamera && (
                <div className="mb-3 space-y-2">
                  <label className="block text-[10px] font-semibold" style={{ color: '#ec4899' }}>Design Approach</label>
                  <div className="grid grid-cols-2 gap-1.5">
                    {([
                      ['new', 'New Design', 'Fresh treatments from scratch'],
                      ['update', 'Update Existing', 'Keep style, refresh materials'],
                      ['rearrange', 'Rearrange', 'Reposition for better flow'],
                      ['renovate', 'Full Renovation', 'Complete window redesign'],
                    ] as const).map(([key, label, desc]) => (
                      <button key={key} onClick={() => setDesignMode(key as any)}
                        className="flex flex-col items-start p-2 rounded-lg text-left transition"
                        style={{
                          background: designMode === key ? 'rgba(236,72,153,0.12)' : 'var(--raised)',
                          border: `1px solid ${designMode === key ? 'rgba(236,72,153,0.4)' : 'var(--border)'}`,
                        }}>
                        <span className="text-[10px] font-semibold" style={{ color: designMode === key ? '#ec4899' : 'var(--text-primary)' }}>{label}</span>
                        <span className="text-[8px]" style={{ color: 'var(--text-muted)' }}>{desc}</span>
                      </button>
                    ))}
                  </div>
                  <input type="text" value={mockupPreferences} onChange={e => setMockupPreferences(e.target.value)}
                    placeholder="Additional preferences: modern minimalist, warm tones, motorized..."
                    className="w-full h-8 rounded-lg px-3 text-[11px] outline-none"
                    style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} />

                  {/* ── Style Inspiration ─────────── */}
                  <div className="mt-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                      Style Inspiration {selectedStyles.length > 0 && <span style={{ color: 'var(--gold)' }}>({selectedStyles.length})</span>}
                    </p>
                    <div className="grid grid-cols-3 gap-1.5">
                      {STYLE_PRESETS.map(s => {
                        const active = selectedStyles.includes(s.id);
                        return (
                          <button key={s.id}
                            onClick={() => setSelectedStyles(prev =>
                              active ? prev.filter(x => x !== s.id) : prev.length < 3 ? [...prev, s.id] : prev
                            )}
                            className="px-2 py-1.5 rounded-lg text-[10px] font-medium transition text-left"
                            style={{
                              background: active ? 'rgba(212,175,55,0.15)' : 'rgba(255,255,255,0.03)',
                              border: `1.5px solid ${active ? 'var(--gold)' : 'var(--glass-border)'}`,
                              color: active ? 'var(--gold)' : 'var(--text-secondary)',
                            }}
                          >
                            {s.label}
                          </button>
                        );
                      })}
                    </div>
                    {selectedStyles.length > 0 && (
                      <p className="text-[9px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
                        AI will design proposals in: {selectedStyles.map(s => STYLE_PRESETS.find(p => p.id === s)?.label).filter(Boolean).join(', ')} style
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Upload options — with drag-and-drop zone */}
              {!showCamera && !uploadedImage && !uploaded3DFile && (
                <div
                  onDragOver={e => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
                  onDragLeave={e => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
                  onDrop={handleDrop}
                  className="mb-3"
                >
                  {/* Drag overlay */}
                  {isDragging && (
                    <div className="rounded-xl p-8 flex flex-col items-center justify-center gap-2 mb-3"
                      style={{ background: 'rgba(212,175,55,0.08)', border: '2px dashed var(--gold)', minHeight: 120 }}>
                      <Upload className="w-8 h-8" style={{ color: 'var(--gold)' }} />
                      <p className="text-xs font-semibold" style={{ color: 'var(--gold)' }}>Drop file here — images, 3D scans, documents</p>
                    </div>
                  )}
                  {!isDragging && (
                    <>
                      <div className="grid grid-cols-3 gap-2">
                        <button onClick={startCamera} className="flex flex-col items-center gap-2 p-4 rounded-xl transition"
                          style={{ background: 'var(--raised)', border: '1px dashed var(--border)' }}>
                          <Camera className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
                          <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Take Photo</span>
                        </button>
                        <button onClick={() => fileInputRef.current?.click()} className="flex flex-col items-center gap-2 p-4 rounded-xl transition"
                          style={{ background: 'var(--raised)', border: '1px dashed var(--border)' }}>
                          <Upload className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
                          <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Gallery / Files</span>
                        </button>
                        <button onClick={() => {
                          const inp = document.createElement('input');
                          inp.type = 'file';
                          inp.accept = '*/*';
                          inp.onchange = (e: any) => {
                            const file = e.target?.files?.[0];
                            if (file) processFile(file);
                          };
                          inp.click();
                        }} className="flex flex-col items-center gap-2 p-4 rounded-xl transition"
                          style={{ background: 'var(--raised)', border: '1px dashed var(--border)' }}>
                          <ImageIcon className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
                          <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Polycam / 3D</span>
                        </button>
                        <input ref={fileInputRef} type="file" accept="image/*,.jpg,.jpeg,.png,.heic,.webp,.glb,.gltf,.obj,.usdz,.ply,.fbx,.stl" onChange={handleFileUpload} className="hidden" />
                      </div>
                      <p className="text-center text-[9px] mt-2" style={{ color: 'var(--text-muted)' }}>
                        Drag & drop or paste (Ctrl+V) — images, 3D scans (.glb, .obj, .usdz), documents
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* 3D File preview card */}
              {uploaded3DFile && !showCamera && (
                <div className="relative mb-3 rounded-xl p-4" style={{ background: 'var(--raised)', border: '1px solid rgba(139,92,246,0.3)' }}>
                  <div className="flex items-center gap-3">
                    <div className="w-14 h-14 rounded-lg flex items-center justify-center" style={{ background: 'rgba(139,92,246,0.12)' }}>
                      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="none" stroke="#8B5CF6" strokeWidth="1.5">
                        <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{uploaded3DFile.name}</p>
                      <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>3D Scan — {uploaded3DFile.size}</p>
                      <div className="flex gap-2 mt-1.5">
                        <button onClick={() => setShow3DViewer(true)}
                          className="text-[9px] px-2 py-0.5 rounded-full font-medium"
                          style={{ background: 'rgba(139,92,246,0.15)', color: '#8B5CF6' }}>
                          Open 3D Viewer
                        </button>
                        <button onClick={() => {
                          if (navigator.share) { navigator.share({ title: uploaded3DFile.name, url: uploaded3DFile.url }).catch(() => {}); }
                          else { navigator.clipboard.writeText(uploaded3DFile.url).then(() => alert('Link copied!')); }
                        }}
                          className="text-[9px] px-2 py-0.5 rounded-full font-medium"
                          style={{ background: 'rgba(212,175,55,0.15)', color: 'var(--gold)' }}>
                          Share
                        </button>
                      </div>
                    </div>
                    <button onClick={() => setUploaded3DFile(null)} className="p-1 rounded" style={{ color: 'var(--text-muted)' }}>
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  {isAnalyzing && (
                    <div className="absolute inset-0 bg-black/60 rounded-xl flex flex-col items-center justify-center">
                      <Loader2 className="w-8 h-8 animate-spin mb-2" style={{ color: '#8B5CF6' }} />
                      <p className="text-xs font-medium">Processing 3D scan...</p>
                    </div>
                  )}
                </div>
              )}

              {/* Image preview */}
              {uploadedImage && !showCamera && (
                <div className="relative mb-3">
                  <img src={uploadedImage} alt="Analysis" className="w-full rounded-xl" style={{ maxHeight: '40vh', objectFit: 'contain' }} />
                  {isAnalyzing && (
                    <div className="absolute inset-0 bg-black/60 rounded-xl flex flex-col items-center justify-center">
                      <Loader2 className="w-8 h-8 animate-spin mb-2" style={{ color: '#8B5CF6' }} />
                      <p className="text-xs font-medium">Analyzing with AI...</p>
                    </div>
                  )}
                </div>
              )}

              {/* Window analysis results */}
              {analysisResult?.mode === 'window' && (
                <div className="rounded-xl p-3 mb-3" style={{ background: 'var(--raised)', border: '1px solid rgba(139,92,246,0.2)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold flex items-center gap-1" style={{ color: '#8B5CF6' }}><Sparkles className="w-3 h-3" /> Results</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>{analysisResult.confidence}%</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 mb-2">
                    <div className="rounded-lg p-2 text-center" style={{ background: 'var(--surface)' }}>
                      <p className="text-lg font-bold">{analysisResult.suggestedWidth}"</p>
                      <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Width</p>
                    </div>
                    <div className="rounded-lg p-2 text-center" style={{ background: 'var(--surface)' }}>
                      <p className="text-lg font-bold">{analysisResult.suggestedHeight}"</p>
                      <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Height</p>
                    </div>
                  </div>
                  {analysisResult.recommendations.map((r: string, i: number) => (
                    <div key={i} className="flex items-start gap-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                      <Check className="w-2.5 h-2.5 shrink-0 mt-0.5" style={{ color: '#8B5CF6' }} /><span>{r}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Upholstery analysis results */}
              {analysisResult?.mode === 'upholstery' && (
                <div className="rounded-xl p-3 mb-3" style={{ background: 'var(--raised)', border: '1px solid rgba(212,175,55,0.2)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold flex items-center gap-1" style={{ color: 'var(--gold)' }}><Sparkles className="w-3 h-3" /> Upholstery Estimate</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>{analysisResult.confidence}%</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mb-2">
                    <div className="rounded-lg p-2 text-center" style={{ background: 'var(--surface)' }}>
                      <p className="text-sm font-bold">{analysisResult.fabricYardsPlain} yd</p>
                      <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Fabric</p>
                    </div>
                    <div className="rounded-lg p-2 text-center" style={{ background: 'var(--surface)' }}>
                      <p className="text-sm font-bold">{(analysisResult.cushions?.seat || 0) + (analysisResult.cushions?.back || 0)}</p>
                      <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Cushions</p>
                    </div>
                    <div className="rounded-lg p-2 text-center" style={{ background: 'var(--surface)' }}>
                      <p className="text-sm font-bold" style={{ color: 'var(--gold)' }}>${analysisResult.laborCostLow}-{analysisResult.laborCostHigh}</p>
                      <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Labor Est.</p>
                    </div>
                  </div>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{analysisResult.furnitureType} — {analysisResult.style}</p>
                  {/* AI-Generated Upholstery Illustration */}
                  {analysisResult.generated_image && (
                    <div className="mt-2">
                      <p className="text-[10px] font-semibold mb-1 flex items-center gap-1" style={{ color: 'var(--gold)' }}>
                        <Sparkles className="w-3 h-3" /> AI Before/After Illustration
                      </p>
                      <a href={analysisResult.generated_image} target="_blank" rel="noreferrer" className="block">
                        <div className="relative rounded-lg overflow-hidden" style={{ border: '1px solid rgba(212,175,55,0.2)' }}>
                          <img src={analysisResult.generated_image} alt="Upholstery illustration" className="w-full rounded-lg" style={{ maxHeight: 200, objectFit: 'cover' }} />
                          <span className="absolute bottom-1.5 right-1.5 text-[8px] px-1.5 py-0.5 rounded-full"
                            style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                            AI Generated — Click to enlarge
                          </span>
                        </div>
                      </a>
                    </div>
                  )}
                </div>
              )}

              {/* Outline analysis results */}
              {analysisResult?.mode === 'outline' && (
                <div className="rounded-xl p-3 mb-3 max-h-[300px] overflow-y-auto" style={{ background: 'var(--raised)', border: '1px solid rgba(59,130,246,0.2)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold flex items-center gap-1" style={{ color: '#3b82f6' }}><Ruler className="w-3 h-3" /> Dimensional Plan</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>{analysisResult.confidence}%</span>
                  </div>
                  {/* Window Opening */}
                  <div className="grid grid-cols-2 gap-2 mb-2">
                    <div className="rounded-lg p-2 text-center" style={{ background: 'var(--surface)' }}>
                      <p className="text-lg font-bold">{analysisResult.windowOpening?.width}"</p>
                      <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Window Width</p>
                    </div>
                    <div className="rounded-lg p-2 text-center" style={{ background: 'var(--surface)' }}>
                      <p className="text-lg font-bold">{analysisResult.windowOpening?.height}"</p>
                      <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Window Height</p>
                    </div>
                  </div>
                  {/* Clearances */}
                  <p className="text-[10px] font-semibold mb-1" style={{ color: '#3b82f6' }}>Clearances</p>
                  <div className="grid grid-cols-4 gap-1 mb-2">
                    {[['Above', analysisResult.clearances?.above_window], ['Below', analysisResult.clearances?.below_window],
                      ['Left', analysisResult.clearances?.left_wall], ['Right', analysisResult.clearances?.right_wall]].map(([label, val]) => (
                      <div key={label as string} className="rounded-lg p-1.5 text-center" style={{ background: 'var(--surface)' }}>
                        <p className="text-xs font-bold">{val}"</p>
                        <p className="text-[8px]" style={{ color: 'var(--text-muted)' }}>{label}</p>
                      </div>
                    ))}
                  </div>
                  {/* Mounting */}
                  {analysisResult.mounting && (
                    <div className="rounded-lg p-2 mb-2" style={{ background: 'var(--surface)' }}>
                      <p className="text-[10px] font-semibold mb-1" style={{ color: '#3b82f6' }}>Mounting Recommendation</p>
                      <p className="text-[10px]" style={{ color: 'var(--text-primary)' }}>
                        Rod: {analysisResult.mounting.rod_width}" wide at {analysisResult.mounting.mounting_height}" height — {analysisResult.mounting.mount_type}
                      </p>
                      {analysisResult.mounting.notes && <p className="text-[9px] mt-1" style={{ color: 'var(--text-muted)' }}>{analysisResult.mounting.notes}</p>}
                    </div>
                  )}
                  {/* Obstructions */}
                  {analysisResult.obstructions?.length > 0 && (
                    <div className="mb-2">
                      <p className="text-[10px] font-semibold mb-1" style={{ color: '#ef4444' }}>Obstructions</p>
                      {analysisResult.obstructions.map((o: any, i: number) => (
                        <div key={i} className="text-[10px] flex items-start gap-1" style={{ color: 'var(--text-muted)' }}>
                          <span style={{ color: '#ef4444' }}>!</span> {o.type} — {o.location} ({o.distance_from_window}" from window)
                        </div>
                      ))}
                    </div>
                  )}
                  {/* Description */}
                  {analysisResult.outlineDescription && (
                    <p className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>{analysisResult.outlineDescription}</p>
                  )}
                </div>
              )}

              {/* Mockup Studio results — FULL PAGE LAYOUT */}
              {analysisResult?.mode === 'mockup' && (
                <div className="space-y-3 mb-3">
                  {/* Header + Room Assessment */}
                  <div className="rounded-xl p-3" style={{ background: 'var(--raised)', border: '1px solid rgba(236,72,153,0.2)' }}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[12px] font-bold flex items-center gap-1.5" style={{ color: '#ec4899' }}><Palette className="w-4 h-4" /> Design Proposals</span>
                      <span className="text-[9px] px-2 py-0.5 rounded-full" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>{analysisResult.confidence}% confidence</span>
                    </div>
                    {analysisResult.roomAssessment && (
                      <div className="rounded-lg p-2" style={{ background: 'var(--surface)' }}>
                        <p className="text-[11px]" style={{ color: 'var(--text-primary)' }}>
                          <strong>{analysisResult.roomAssessment.room_type}</strong> — {analysisResult.roomAssessment.style} style,
                          {' '}{analysisResult.roomAssessment.light_level} light, {analysisResult.roomAssessment.privacy_need} privacy
                        </p>
                        {analysisResult.roomAssessment.color_palette && (
                          <div className="flex items-center gap-1 mt-1">
                            <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>Palette:</span>
                            {analysisResult.roomAssessment.color_palette.map((c: string, i: number) => (
                              <span key={i} className="text-[9px] px-1 rounded" style={{ background: 'var(--elevated)', color: 'var(--text-secondary)' }}>{c}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Original Photo — full width */}
                  {uploadedImage && (
                    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
                      <div className="px-3 py-1.5" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
                        <span className="text-[10px] font-semibold" style={{ color: 'var(--text-muted)' }}>Original Photo</span>
                      </div>
                      <img src={uploadedImage} alt="Original room" className="w-full" />
                    </div>
                  )}

                  {/* Each proposal as its own full-width card with AI image beside notes */}
                  {analysisResult.proposals?.map((p: any, i: number) => {
                    const tierColor = i === 0 ? '#22c55e' : i === 1 ? 'var(--gold)' : '#8B5CF6';
                    const tierBg = i === 0 ? 'rgba(34,197,94,0.08)' : i === 1 ? 'rgba(212,175,55,0.08)' : 'rgba(139,92,246,0.08)';
                    const tierBorder = i === 0 ? 'rgba(34,197,94,0.3)' : i === 1 ? 'rgba(212,175,55,0.3)' : 'rgba(139,92,246,0.3)';
                    const generatedImg = p.generated_image ? { url: p.generated_image, tier: p.tier } : analysisResult.generated_images?.find((img: any) => img.tier === p.tier);
                    return (
                      <div key={i} className="rounded-xl overflow-hidden" style={{ background: tierBg, border: `1.5px solid ${tierBorder}` }}>
                        {/* Tier header */}
                        <div className="flex items-center justify-between px-4 py-2" style={{ borderBottom: `1px solid ${tierBorder}` }}>
                          <span className="text-[12px] font-bold" style={{ color: tierColor }}>{p.tier || `Option ${i + 1}`}</span>
                          <span className="text-[11px] font-bold font-mono" style={{ color: 'var(--gold)' }}>
                            ${(p.price_range_low || 0).toLocaleString()} — ${(p.price_range_high || 0).toLocaleString()}
                          </span>
                        </div>
                        {/* Content: image left, details right */}
                        <div className={`${generatedImg ? 'grid grid-cols-2 gap-0' : ''}`}>
                          {/* AI Generated image — large */}
                          {generatedImg && (
                            <a href={generatedImg.url} target="_blank" rel="noreferrer" className="block">
                              <div className="relative">
                                <img src={generatedImg.url} alt={`${p.tier} mockup`} className="w-full object-cover" style={{ minHeight: 200 }} />
                                <span className="absolute bottom-2 right-2 text-[8px] px-1.5 py-0.5 rounded-full"
                                  style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>Click to enlarge</span>
                              </div>
                            </a>
                          )}
                          {/* Details panel — beside the image */}
                          <div className="p-3 space-y-1.5">
                            <p className="text-[11px] font-semibold" style={{ color: 'var(--text-primary)' }}>{p.treatment_type} — {p.style}</p>
                            <div className="space-y-0.5 text-[10px]">
                              <p style={{ color: 'var(--text-secondary)' }}><strong>Fabric:</strong> {p.fabric}</p>
                              <p style={{ color: 'var(--text-secondary)' }}><strong>Lining:</strong> {p.lining}</p>
                              <p style={{ color: 'var(--text-secondary)' }}><strong>Hardware:</strong> {p.hardware}</p>
                              {p.extras?.length > 0 && (
                                <p style={{ color: 'var(--text-secondary)' }}><strong>Extras:</strong> {p.extras.join(', ')}</p>
                              )}
                            </div>
                            <p className="text-[10px] italic leading-relaxed pt-1" style={{ color: 'var(--text-muted)', borderTop: `1px solid ${tierBorder}` }}>
                              {p.visual_description}
                            </p>
                            {p.design_rationale && (
                              <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                                <Lightbulb className="w-2.5 h-2.5 inline mr-1" style={{ color: tierColor }} />
                                {p.design_rationale}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {/* General Recommendations */}
                  {analysisResult.generalRecommendations?.length > 0 && (
                    <div className="rounded-xl p-3" style={{ background: 'var(--raised)', border: '1px solid rgba(236,72,153,0.15)' }}>
                      <p className="text-[10px] font-semibold mb-1.5" style={{ color: '#ec4899' }}>Recommendations</p>
                      {analysisResult.generalRecommendations.map((r: string, i: number) => (
                        <div key={i} className="flex items-start gap-1.5 text-[10px] mb-0.5" style={{ color: 'var(--text-muted)' }}>
                          <Lightbulb className="w-3 h-3 shrink-0 mt-0.5" style={{ color: '#ec4899' }} /><span>{r}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Action buttons */}
              <div className="flex flex-wrap gap-2">
                {uploadedImage && !analysisResult && !isAnalyzing && (
                  <>
                    <button onClick={() => setUploadedImage(null)} className="flex-1 py-2 rounded-lg text-[11px]" style={{ background: 'var(--raised)', color: 'var(--text-secondary)' }}>New Photo</button>
                    <button onClick={() => {
                      if (!activeRoomId || !activeItemId || !uploadedImage) return;
                      const room = rooms.find(r => r.id === activeRoomId);
                      if (photoMode === 'upholstery') {
                        const item = room?.upholstery.find(u => u.id === activeItemId);
                        if (item?.sourcePhoto === uploadedImage || (item?.photos || []).includes(uploadedImage)) { closePhotoModal(); return; }
                        updateUpholstery(activeRoomId, activeItemId, { photos: [...(item?.photos || []), uploadedImage] });
                      } else {
                        const item = room?.windows.find(w => w.id === activeItemId);
                        if (item?.sourcePhoto === uploadedImage || (item?.photos || []).includes(uploadedImage)) { closePhotoModal(); return; }
                        updateWindow(activeRoomId, activeItemId, { photos: [...(item?.photos || []), uploadedImage] });
                      }
                      closePhotoModal();
                    }} className="py-2 px-3 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                      style={{ background: 'rgba(34,197,94,0.12)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)' }}>
                      <ImageIcon className="w-3 h-3" /> Save Photo
                    </button>
                    <button onClick={analyzeImage} className="flex-1 py-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                      style={{ background:
                        photoMode === 'upholstery' ? 'var(--gold)' :
                        photoMode === 'outline' ? '#3b82f6' :
                        photoMode === 'mockup' ? '#ec4899' : '#8B5CF6', color: '#fff' }}>
                      <Sparkles className="w-3 h-3" /> {photoMode === 'mockup' ? 'Generate Proposals' : photoMode === 'outline' ? 'Extract Outline' : 'Analyze'}
                    </button>
                  </>
                )}
                {analysisResult && (
                  <>
                    <button onClick={() => { setAnalysisResult(null); setUploadedImage(null); }} className="py-2 px-3 rounded-lg text-[11px]" style={{ background: 'var(--raised)', color: 'var(--text-secondary)' }}>Retry</button>
                    {(analysisResult.mode === 'window' || analysisResult.mode === 'upholstery' || (analysisResult.mode === 'outline' && activeItemId)) && (
                      <button onClick={applyAnalysis} className="flex-1 py-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                        style={{ background: '#22c55e', color: '#fff' }}>
                        <Check className="w-3 h-3" /> Apply
                      </button>
                    )}
                    {/* Outline → PDF + Share actions */}
                    {analysisResult.mode === 'outline' && (
                      <>
                        <button onClick={quickPdfFromOutline} disabled={saving}
                          className="flex-1 py-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                          style={{ background: '#3b82f6', color: '#fff' }}>
                          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />} Quick PDF
                        </button>
                        <button onClick={shareOutlineEmail}
                          className="py-2 px-3 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                          style={{ background: 'rgba(59,130,246,0.15)', color: '#3b82f6', border: '1px solid rgba(59,130,246,0.3)' }}>
                          <Mail className="w-3 h-3" /> Email
                        </button>
                      </>
                    )}
                    {/* Mockup → Quote actions */}
                    {analysisResult.mode === 'mockup' && analysisResult.proposals?.length > 0 && (
                      <>
                        <button onClick={() => applyMockupToQuote()} className="flex-1 py-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                          style={{ background: '#22c55e', color: '#fff' }}>
                          <Send className="w-3 h-3" /> Add to Quote
                        </button>
                        <button onClick={quickPdfFromMockup} disabled={saving}
                          className="py-2 px-3 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                          style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
                          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Download className="w-3 h-3" />} Quick PDF
                        </button>
                      </>
                    )}
                    {/* View standalone page — Empire branded, print/PDF/share */}
                    <button
                      onClick={() => {
                        const isUpholstery = analysisResult.mode === 'upholstery';
                        const isMockup = analysisResult.mode === 'mockup';
                        const isOutline = analysisResult.mode === 'outline';
                        const title = isUpholstery ? 'Upholstery Analysis' : isMockup ? 'Design Proposals' : 'Dimensional Plan';
                        const custName = customer.name || 'Customer';
                        const roomName = rooms.find(r => r.id === activeRoomId)?.name || 'Room';
                        const win0 = rooms.find(r => r.id === activeRoomId)?.windows.find(w => w.id === activeItemId);

                        // Build photo comparison section
                        let photoSection = '';
                        if (uploadedImage) {
                          const mockImg = analysisResult.generated_images?.[0]?.url || analysisResult.generated_image || '';
                          if (mockImg) {
                            photoSection = `<div class="photo-compare"><div class="photo-card"><div class="photo-label">Original Photo</div><img src="${uploadedImage}" /></div><div class="photo-card"><div class="photo-label">AI Visualization</div><img src="${mockImg}" /></div></div>`;
                          } else {
                            photoSection = `<div class="photo-single"><div class="photo-label">Site Photo</div><img src="${uploadedImage}" /></div>`;
                          }
                        }

                        // Build details by mode
                        let details = '';
                        if (isOutline || analysisResult.mode === 'window') {
                          const wo = analysisResult.windowOpening || {};
                          const mt = analysisResult.mounting || {};
                          const cl = analysisResult.clearances || {};
                          const obs = analysisResult.obstructions || [];
                          details = `
                          <div class="section"><h2>Window Dimensions</h2>
                            <div class="stat-grid">
                              <div class="stat"><span class="stat-val">${wo.width || analysisResult.suggestedWidth || 0}"</span><span class="stat-lbl">Width</span></div>
                              <div class="stat"><span class="stat-val">${wo.height || analysisResult.suggestedHeight || 0}"</span><span class="stat-lbl">Height</span></div>
                              <div class="stat"><span class="stat-val">${analysisResult.windowType || 'Standard'}</span><span class="stat-lbl">Type</span></div>
                              <div class="stat accent"><span class="stat-val">${analysisResult.confidence || 0}%</span><span class="stat-lbl">AI Confidence</span></div>
                            </div>
                          </div>
                          <div class="section"><h2>Clearances</h2>
                            <div class="stat-grid four">
                              <div class="stat"><span class="stat-val">${cl.above_window || 0}"</span><span class="stat-lbl">Above</span></div>
                              <div class="stat"><span class="stat-val">${cl.below_window || 0}"</span><span class="stat-lbl">Below</span></div>
                              <div class="stat"><span class="stat-val">${cl.left_wall || 0}"</span><span class="stat-lbl">Left</span></div>
                              <div class="stat"><span class="stat-val">${cl.right_wall || 0}"</span><span class="stat-lbl">Right</span></div>
                            </div>
                          </div>
                          ${mt.mount_type ? `<div class="highlight-box"><h3>Mounting Recommendation</h3><p>Rod: ${mt.rod_width || 0}" wide at ${mt.mounting_height || 0}" height — ${mt.mount_type} mount</p>${mt.notes ? `<p class="muted">${mt.notes}</p>` : ''}</div>` : ''}
                          ${obs.length > 0 ? `<div class="section"><h2>Obstructions</h2>${obs.map((o: any) => `<div class="obs-item">${typeof o === 'string' ? o : `${o.type || 'Item'} — ${o.location || ''} (${o.distance || ''})`}</div>`).join('')}</div>` : ''}
                          ${analysisResult.outlineDescription ? `<div class="section"><h2>AI Description</h2><p>${analysisResult.outlineDescription}</p></div>` : ''}
                          ${(analysisResult.recommendations || []).length > 0 ? `<div class="section"><h2>Recommendations</h2>${analysisResult.recommendations.map((r: string) => `<p class="rec-item">${r}</p>`).join('')}</div>` : ''}`;
                        } else if (isMockup) {
                          details = `<div class="section"><h2>Design Proposals — ${roomName}</h2></div>` +
                          (analysisResult.proposals || []).map((p: any, i: number) => {
                            const colors = ['#22c55e','#D4AF37','#8B5CF6'];
                            const labels = ['Budget Friendly',"Designer's Choice",'Premium Luxe'];
                            const tc = colors[i % 3];
                            const isRec = i === 1;
                            const imgHtml = p.generated_image ? `<div class="proposal-img"><img src="${p.generated_image}" /></div>` : '';
                            return `<div class="proposal${isRec ? ' recommended' : ''}" style="--tc:${tc}">
                              <div class="proposal-header"><span class="tier-badge" style="background:${tc}">${p.tier || labels[i]}</span>${isRec ? '<span class="rec-badge">RECOMMENDED</span>' : ''}<span class="price">$${(p.price_range_low||0).toLocaleString()} — $${(p.price_range_high||0).toLocaleString()}</span></div>
                              <p class="proposal-title">${p.treatment_type || ''} — ${p.style || ''}</p>
                              ${imgHtml}
                              <div class="spec-grid"><div class="spec"><strong>Fabric</strong>${p.fabric || 'TBD'}</div><div class="spec"><strong>Lining</strong>${p.lining || 'Standard'}</div><div class="spec"><strong>Hardware</strong>${p.hardware || 'Rod'}</div>${(p.extras||[]).length > 0 ? `<div class="spec"><strong>Extras</strong>${p.extras.join(', ')}</div>` : ''}</div>
                              ${p.visual_description ? `<p class="vis-desc">${p.visual_description}</p>` : ''}
                              ${p.design_rationale ? `<p class="rationale">${p.design_rationale}</p>` : ''}
                            </div>`;
                          }).join('');
                          if (analysisResult.generalRecommendations?.length > 0) {
                            details += `<div class="section"><h2>Design Recommendations</h2>${analysisResult.generalRecommendations.map((r: string) => `<p class="rec-item">${r}</p>`).join('')}</div>`;
                          }
                        } else if (isUpholstery) {
                          details = `
                          <div class="section"><h2>Upholstery Assessment</h2>
                            <div class="stat-grid">
                              <div class="stat"><span class="stat-val">${analysisResult.furnitureType || 'N/A'}</span><span class="stat-lbl">Type</span></div>
                              <div class="stat"><span class="stat-val">${analysisResult.fabricYardsPlain || 0} yd</span><span class="stat-lbl">Fabric</span></div>
                              <div class="stat"><span class="stat-val">${(analysisResult.cushions?.seat||0)+(analysisResult.cushions?.back||0)}</span><span class="stat-lbl">Cushions</span></div>
                              <div class="stat accent"><span class="stat-val">$${(analysisResult.laborCostLow||0).toLocaleString()}–$${(analysisResult.laborCostHigh||0).toLocaleString()}</span><span class="stat-lbl">Est. Labor</span></div>
                            </div>
                          </div>
                          ${analysisResult.newFoamRecommended ? '<div class="highlight-box"><h3>New Foam Recommended</h3><p>Existing foam should be replaced for best results.</p></div>' : ''}
                          ${(analysisResult.questions||[]).length > 0 ? `<div class="section"><h2>Questions for Client</h2>${analysisResult.questions.map((q: string) => `<p class="rec-item">${q}</p>`).join('')}</div>` : ''}`;
                        }

                        const printHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title} — Empire</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#05050d;color:#e4e4e8;min-height:100vh}
.wrap{max-width:900px;margin:0 auto;padding:32px 24px}
.header{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:20px;margin-bottom:28px;border-bottom:2px solid #D4AF37}
.brand{font-size:28px;font-weight:800;color:#D4AF37;letter-spacing:1px}
.brand-sub{font-size:12px;color:#888;margin-top:2px}
.badge{background:#1a1a2e;color:#D4AF37;padding:6px 16px;border-radius:8px;font-weight:700;font-size:13px;letter-spacing:1.5px;border:1px solid rgba(212,175,55,0.3)}
.meta{text-align:right;font-size:12px;color:#888;margin-top:6px}
.actions{display:flex;gap:10px;margin:20px 0 28px}
.btn{padding:10px 22px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;border:none;display:inline-flex;align-items:center;gap:6px;transition:all 0.2s}
.btn-gold{background:#D4AF37;color:#0a0a0a}.btn-gold:hover{background:#e8c547}
.btn-purple{background:#8B5CF6;color:#fff}.btn-purple:hover{background:#9d78f7}
.btn-dim{background:rgba(255,255,255,0.06);color:#aaa;border:1px solid rgba(255,255,255,0.1)}.btn-dim:hover{background:rgba(255,255,255,0.1)}
.photo-compare{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:24px 0}
.photo-single{margin:24px 0}
.photo-card{border-radius:12px;overflow:hidden;border:1px solid rgba(255,255,255,0.1)}
.photo-card img,.photo-single img{width:100%;display:block;max-height:400px;object-fit:contain;background:#0a0a1a}
.photo-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;padding:8px 14px;color:#888;background:rgba(255,255,255,0.03)}
.section{margin:28px 0}
.section h2{font-size:14px;font-weight:700;color:#8B5CF6;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:14px}
.section p{font-size:14px;line-height:1.7;color:#ccc}
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.stat-grid.four{grid-template-columns:repeat(4,1fr)}
.stat{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:16px;text-align:center}
.stat-val{display:block;font-size:22px;font-weight:800;color:#e4e4e8}
.stat-lbl{display:block;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-top:4px}
.stat.accent{border-color:rgba(212,175,55,0.3);background:rgba(212,175,55,0.06)}
.stat.accent .stat-val{color:#D4AF37}
.highlight-box{background:linear-gradient(135deg,rgba(212,175,55,0.08),rgba(139,92,246,0.08));border:1px solid rgba(212,175,55,0.25);border-radius:12px;padding:20px;margin:20px 0}
.highlight-box h3{color:#D4AF37;font-size:13px;font-weight:700;margin-bottom:8px}
.highlight-box p{font-size:13px;color:#ccc;line-height:1.6}
.highlight-box .muted{color:#888;font-style:italic;margin-top:6px}
.obs-item{padding:8px 14px;margin:4px 0;background:rgba(239,68,68,0.06);border-left:3px solid #ef4444;border-radius:0 8px 8px 0;font-size:13px;color:#f87171}
.rec-item{padding:8px 14px;margin:4px 0;background:rgba(139,92,246,0.06);border-left:3px solid #8B5CF6;border-radius:0 8px 8px 0;font-size:13px;color:#c4b5fd}
.proposal{border:2px solid var(--tc,#444);border-radius:14px;padding:20px;margin:16px 0;background:rgba(255,255,255,0.02);page-break-inside:avoid}
.proposal.recommended{border-width:3px;background:rgba(212,175,55,0.04);box-shadow:0 4px 24px rgba(212,175,55,0.1)}
.proposal-header{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.tier-badge{color:#fff;padding:4px 14px;border-radius:6px;font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px}
.rec-badge{background:rgba(212,175,55,0.15);border:1px solid #D4AF37;color:#D4AF37;padding:3px 12px;border-radius:20px;font-size:10px;font-weight:800}
.price{margin-left:auto;font-size:15px;font-weight:800;color:#D4AF37;font-family:'SF Mono',monospace}
.proposal-title{font-size:16px;font-weight:700;color:#e4e4e8;margin:6px 0 12px}
.proposal-img{border-radius:10px;overflow:hidden;margin:12px 0;border:1px solid rgba(255,255,255,0.08)}
.proposal-img img{width:100%;display:block}
.spec-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:14px 0}
.spec{background:rgba(255,255,255,0.04);border-radius:8px;padding:10px 14px;font-size:12px;color:#ccc}
.spec strong{display:block;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px}
.vis-desc{font-style:italic;color:#999;font-size:13px;line-height:1.6;margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06)}
.rationale{color:#a78bfa;font-size:12px;margin-top:8px}
.footer{text-align:center;padding:28px 0 8px;margin-top:32px;border-top:1px solid rgba(255,255,255,0.06);font-size:11px;color:#555}
@media print{
  body{background:#fff;color:#1a1a2e;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .actions{display:none !important}
  .wrap{padding:20px}
  .stat{border-color:#ddd;background:#f9f9f9}
  .stat-val{color:#1a1a2e}
  .stat.accent{background:#fffcf0;border-color:#D4AF37}
  .section h2{color:#8B5CF6}
  .section p,.spec{color:#333}
  .highlight-box{background:#fffcf0;border-color:#D4AF37}
  .highlight-box p,.highlight-box .muted{color:#444}
  .proposal{background:#fafafa;border-color:#ddd}
  .proposal.recommended{background:#fffcf0;border-color:#D4AF37}
  .proposal-title{color:#1a1a2e}
  .vis-desc{color:#666;border-color:#eee}
  .rec-item{background:#f3f0ff;color:#5b21b6}
  .obs-item{background:#fef2f2;color:#b91c1c}
  .photo-card{border-color:#ddd}
  .photo-label{color:#666;background:#f5f5f5}
  .footer{color:#999}
}
</style></head><body>
<div class="wrap">
  <div class="header">
    <div><div class="brand">EMPIRE</div><div class="brand-sub">Custom Window Treatments & Upholstery</div></div>
    <div style="text-align:right"><div class="badge">${title.toUpperCase()}</div><div class="meta">${new Date().toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'})}${custName !== 'Customer' ? ` · ${custName}` : ''}${roomName ? ` · ${roomName}` : ''}</div></div>
  </div>
  <div class="actions">
    <button class="btn btn-gold" onclick="window.print()">Print / Save PDF</button>
    <button class="btn btn-purple" onclick="if(navigator.share){navigator.share({title:'Empire — ${title}',text:document.body.innerText.substring(0,500)}).catch(()=>{})}else{navigator.clipboard.writeText(window.location.href).then(()=>alert('Copied!'))}">Share</button>
    <button class="btn btn-dim" onclick="window.close()">Close</button>
  </div>
  ${photoSection}
  ${details}
  <div class="footer">Empire · Custom Window Treatments & Upholstery · Generated ${new Date().toLocaleDateString()}</div>
</div>
</body></html>`;
                        const blob = new Blob([printHtml], { type: 'text/html' });
                        const blobUrl = URL.createObjectURL(blob);
                        const win = window.open(blobUrl, '_blank');
                        if (!win) { alert('Popup blocked — please allow popups for localhost:3009'); }
                        else { setTimeout(() => URL.revokeObjectURL(blobUrl), 60000); }
                      }}
                      className="py-2 px-3 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                      style={{ background: 'var(--gold)', color: '#0a0a0a' }}
                    >
                      <ExternalLink className="w-3 h-3" /> View
                    </button>
                    <button onClick={closePhotoModal} className="py-2 px-3 rounded-lg text-[11px] font-semibold"
                      style={{ background: 'var(--elevated)', color: 'var(--text-primary)' }}>
                      Done
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
