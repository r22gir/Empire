'use client';
import { useState, useRef, useCallback } from 'react';
import { API_URL } from '@/lib/api';
import {
  Plus, Trash2, Copy, ChevronDown, ChevronUp, Camera, Upload, X,
  Sparkles, Check, Loader2, Send, Download, Printer,
  Brain, Eye, Lightbulb, Calculator, Ruler, Palette, PenTool,
  Share2, Mail, Link, ExternalLink,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════

interface WindowItem {
  id: string; name: string; width: number; height: number; quantity: number;
  treatmentType: string; mountType: string; liningType: string;
  hardwareType: string; motorization: string; notes: string;
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
  };
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
  labor: { 'standard': 62, 'tufted': 78, 'channeled': 72, 'leather': 100 } as Record<string, number>,
  fabric: { 'plain': 22, 'patterned': 50, 'leather': 110 } as Record<string, number>,
};

const TREATMENT_OPTIONS = [['ripplefold','Ripplefold'],['pinch-pleat','Pinch Pleat'],['rod-pocket','Rod Pocket'],['grommet','Grommet'],['roman-shade','Roman Shade'],['roller-shade','Roller Shade']];
const LINING_OPTIONS = [['unlined','Unlined'],['standard','Standard'],['blackout','Blackout'],['thermal','Thermal'],['interlining','Interlining']];
const HARDWARE_OPTIONS = [['none','None'],['rod-standard','Rod Std'],['rod-decorative','Rod Deco'],['track-basic','Track Basic'],['track-ripplefold','Track Ripple']];
const MOTOR_OPTIONS = [['none','None'],['somfy','Somfy $285'],['lutron','Lutron $425'],['generic','Generic $185']];
const MOUNT_OPTIONS = [['wall','Wall'],['ceiling','Ceiling'],['inside','Inside']];
const FURNITURE_TYPES = ['sofa','loveseat','chair','club-chair','wing-chair','recliner','ottoman','bench','chaise','headboard'];

const genId = () => Math.random().toString(36).substr(2, 9);

const calcWindowPrice = (w: WindowItem): number => {
  const sqft = (w.width * w.height) / 144;
  const base = (PRICING.base[w.treatmentType] || 40) * sqft;
  const lining = (PRICING.lining[w.liningType] || 0) * sqft;
  return Math.round((base + lining + (PRICING.hardware[w.hardwareType] || 0) + (PRICING.motor[w.motorization] || 0)) * (w.quantity || 1));
};

const calcUpholsteryPrice = (u: UpholsteryItem): number => {
  const yards = u.fabricYards || 0;
  return Math.round(yards * ((UPHOLSTERY_PRICING.labor[u.laborType] || 62) + (UPHOLSTERY_PRICING.fabric[u.fabricType] || 22)));
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
  const [tab, setTab] = useState<'build' | 'customer' | 'summary' | 'preview'>('build');

  // PDF Preview
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(false);

  const grandTotal = rooms.reduce((s, r) => s + calcRoomTotal(r), 0);

  // ── Room CRUD ──────────────────────────────────────────
  const addRoom = () => setRooms([...rooms, { id: genId(), name: `Room ${rooms.length + 1}`, expanded: true, windows: [], upholstery: [] }]);
  const deleteRoom = (id: string) => { if (rooms.length > 1) setRooms(rooms.filter(r => r.id !== id)); };
  const toggleRoom = (id: string) => setRooms(rooms.map(r => r.id === id ? { ...r, expanded: !r.expanded } : r));
  const updateRoomName = (id: string, name: string) => setRooms(rooms.map(r => r.id === id ? { ...r, name } : r));

  // ── Window CRUD ────────────────────────────────────────
  const addWindow = (roomId: string) => setRooms(rooms.map(r => r.id === roomId ? { ...r, windows: [...r.windows, {
    id: genId(), name: `Window ${r.windows.length + 1}`, width: 48, height: 60, quantity: 1,
    treatmentType: 'ripplefold', mountType: 'wall', liningType: 'standard',
    hardwareType: 'track-ripplefold', motorization: 'none', notes: '',
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
    setShowPhotoModal(true); setUploadedImage(null); setAnalysisResult(null);
  };
  const openStandalonePhotoModal = (mode: 'outline' | 'mockup', roomId?: string) => {
    setActiveRoomId(roomId || rooms[0]?.id || null); setActiveItemId(null); setPhotoMode(mode);
    setShowPhotoModal(true); setUploadedImage(null); setAnalysisResult(null);
  };
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { const reader = new FileReader(); reader.onload = (ev) => { setUploadedImage(ev.target?.result as string); setShowCamera(false); }; reader.readAsDataURL(file); }
  };
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
  const closePhotoModal = () => { stopCamera(); setShowPhotoModal(false); setUploadedImage(null); setAnalysisResult(null); };

  const [mockupPreferences, setMockupPreferences] = useState('');

  const analyzeImage = async () => {
    if (!uploadedImage) return;
    setIsAnalyzing(true);
    try {
      const endpoints: Record<string, string> = {
        window: 'http://localhost:3001/api/measure',
        upholstery: 'http://localhost:3001/api/upholstery',
        outline: 'http://localhost:3001/api/outline',
        mockup: 'http://localhost:3001/api/mockup',
      };
      const body: any = { image: uploadedImage };
      if (photoMode === 'mockup' && mockupPreferences) body.preferences = mockupPreferences;

      const res = await fetch(endpoints[photoMode], { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
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
        setAnalysisResult({
          mode: 'mockup', confidence: Math.min(100, Math.max(0, data.confidence || 70)),
          roomAssessment: data.room_assessment || {},
          windowInfo: data.window_info || {},
          proposals: data.proposals || [],
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
    } catch (err) { alert('AI analysis error: ' + (err instanceof Error ? err.message : 'Failed')); }
    finally { setIsAnalyzing(false); }
  };

  const applyAnalysis = () => {
    if (!analysisResult || !activeRoomId) return;
    if (analysisResult.mode === 'upholstery' && activeItemId) {
      updateUpholstery(activeRoomId, activeItemId, {
        furnitureType: analysisResult.furnitureType, fabricYards: analysisResult.fabricYardsPlain || 0,
        cushionCount: (analysisResult.cushions?.seat || 0) + (analysisResult.cushions?.back || 0),
        laborType: analysisResult.hasTufting ? 'tufted' : 'standard',
        width: analysisResult.dimensions?.width || 0, depth: analysisResult.dimensions?.depth || 0,
        height: analysisResult.dimensions?.height || 0, aiAnalysis: analysisResult,
      });
    } else if (analysisResult.mode === 'outline' && activeItemId) {
      updateWindow(activeRoomId, activeItemId, {
        width: analysisResult.windowOpening?.width || 0, height: analysisResult.windowOpening?.height || 0,
        mountType: analysisResult.mounting?.mount_type === 'inside' ? 'inside' : analysisResult.mounting?.mount_type === 'ceiling' ? 'ceiling' : 'wall',
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
      updateWindow(activeRoomId, activeItemId, {
        width: analysisResult.suggestedWidth, height: analysisResult.suggestedHeight, aiAnalysis: analysisResult,
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

  // ── Save & PDF ─────────────────────────────────────────
  const buildLineItems = () => rooms.flatMap(room => [
    ...room.windows.map(w => ({
      description: `${room.name} — ${w.name} (${w.treatmentType}, ${w.liningType}, ${w.hardwareType})`,
      quantity: w.quantity, unit: 'ea', rate: calcWindowPrice(w) / (w.quantity || 1),
      amount: calcWindowPrice(w), category: 'labor',
    })),
    ...room.upholstery.map(u => ({
      description: `${room.name} — ${u.name} (${u.furnitureType}, ${u.laborType})`,
      quantity: 1, unit: 'ea', rate: calcUpholsteryPrice(u), amount: calcUpholsteryPrice(u), category: 'labor',
    })),
  ]);

  const saveQuote = async () => {
    if (!customer.name.trim()) { alert('Customer name required'); return; }
    setSaving(true);
    try {
      const res = await fetch(API_URL + '/quotes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: customer.name, customer_email: customer.email,
          customer_phone: customer.phone, customer_address: customer.address,
          project_name: projectName, line_items: buildLineItems(),
          subtotal: grandTotal, total: grandTotal, tax_rate: 0.08,
          business_name: 'Empire', terms: '50% deposit required. Balance due upon completion.',
          valid_days: 30,
          // Full structured room data for rich PDF
          rooms: rooms.map(r => ({
            name: r.name,
            windows: r.windows.map(w => ({
              name: w.name, width: w.width, height: w.height, quantity: w.quantity,
              treatmentType: w.treatmentType, liningType: w.liningType,
              hardwareType: w.hardwareType, motorization: w.motorization,
              mountType: w.mountType, notes: w.notes,
              price: calcWindowPrice(w),
              aiAnalysis: w.aiAnalysis || null,
            })),
            upholstery: r.upholstery.map(u => ({
              name: u.name, furnitureType: u.furnitureType, fabricYards: u.fabricYards,
              fabricType: u.fabricType, laborType: u.laborType, cushionCount: u.cushionCount,
              width: u.width, depth: u.depth, height: u.height, notes: u.notes,
              price: calcUpholsteryPrice(u),
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
      if (!customer.name.trim()) { alert('Customer name required to preview PDF'); setTab('customer'); return; }
      setSaving(true);
      try {
        const res = await fetch(API_URL + '/quotes', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            customer_name: customer.name, customer_email: customer.email,
            customer_phone: customer.phone, customer_address: customer.address,
            project_name: projectName, line_items: buildLineItems(),
            subtotal: grandTotal, total: grandTotal, tax_rate: 0.08,
            business_name: 'Empire', terms: '50% deposit required. Balance due upon completion.',
            valid_days: 30,
            rooms: rooms.map(r => ({
              name: r.name,
              windows: r.windows.map(w => ({
                name: w.name, width: w.width, height: w.height, quantity: w.quantity,
                treatmentType: w.treatmentType, liningType: w.liningType,
                hardwareType: w.hardwareType, motorization: w.motorization,
                mountType: w.mountType, notes: w.notes,
                price: calcWindowPrice(w), aiAnalysis: w.aiAnalysis || null,
              })),
              upholstery: r.upholstery.map(u => ({
                name: u.name, furnitureType: u.furnitureType, fabricYards: u.fabricYards,
                fabricType: u.fabricType, laborType: u.laborType, cushionCount: u.cushionCount,
                width: u.width, depth: u.depth, height: u.height, notes: u.notes,
                price: calcUpholsteryPrice(u), aiAnalysis: u.aiAnalysis || null,
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
      } catch { alert('Save failed.'); setTab('build'); }
      finally { setSaving(false); }
    } else {
      await loadPdfPreview(savedQuote.id);
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
    window.open(`mailto:${customer.email || ''}?subject=${subject}&body=${body}`, '_self');
    setShowShareMenu(false);
  };

  const copyQuoteLink = () => {
    if (!savedQuote) return;
    const link = `${window.location.origin}/quotes/${savedQuote.id}`;
    navigator.clipboard.writeText(link).then(() => { alert('Link copied!'); });
    setShowShareMenu(false);
  };

  // ── Styles ─────────────────────────────────────────────
  const inputStyle: React.CSSProperties = { background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' };
  const selectStyle: React.CSSProperties = { ...inputStyle, cursor: 'pointer' };

  // ═══════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4" style={{ color: 'var(--gold)' }} />
          <h2 className="text-sm font-semibold" style={{ color: 'var(--gold)' }}>
            {savedQuote ? savedQuote.quote_number : 'New Estimate'}
          </h2>
          <span className="text-lg font-bold font-mono" style={{ color: 'var(--gold)' }}>${grandTotal.toLocaleString()}</span>
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
            style={{ background: customer.name.trim() ? 'var(--gold)' : 'var(--elevated)', color: customer.name.trim() ? '#0a0a0a' : 'var(--text-muted)' }}>
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
                          {/* Lining, Hardware, Motor, Mount */}
                          {[
                            { l: 'Lining', k: 'liningType', v: w.liningType, opts: LINING_OPTIONS },
                            { l: 'Hardware', k: 'hardwareType', v: w.hardwareType, opts: HARDWARE_OPTIONS },
                            { l: 'Motor', k: 'motorization', v: w.motorization, opts: MOTOR_OPTIONS },
                            { l: 'Mount', k: 'mountType', v: w.mountType, opts: MOUNT_OPTIONS },
                          ].map(f => (
                            <div key={f.k}>
                              <label className="block text-[9px] mb-0.5" style={{ color: 'var(--text-muted)' }}>{f.l}</label>
                              <select value={f.v} onChange={e => updateWindow(room.id, w.id, { [f.k]: e.target.value })}
                                className="w-full h-7 rounded-lg px-1 text-[10px] outline-none" style={selectStyle}>
                                {f.opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                              </select>
                            </div>
                          ))}
                        </div>

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
                            <select value={u.furnitureType} onChange={e => updateUpholstery(room.id, u.id, { furnitureType: e.target.value })}
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
        {tab === 'summary' && (
          <div className="rounded-xl p-4 space-y-2" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <h3 className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>Quote Summary</h3>
            {customer.name && <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>Customer: <span style={{ color: 'var(--text-primary)' }}>{customer.name}</span></p>}
            <div className="h-px" style={{ background: 'var(--border)' }} />
            {rooms.map(r => (
              <div key={r.id}>
                <div className="flex justify-between py-1 text-[11px]">
                  <span style={{ color: 'var(--text-secondary)' }}>{r.name} ({r.windows.length} win{r.upholstery.length > 0 ? `, ${r.upholstery.length} uph` : ''})</span>
                  <span className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>${calcRoomTotal(r).toLocaleString()}</span>
                </div>
                {r.windows.map(w => (
                  <div key={w.id} className="flex justify-between py-0.5 pl-3 text-[10px]">
                    <span style={{ color: 'var(--text-muted)' }}>{w.name} — {w.treatmentType} {w.width}"×{w.height}" ×{w.quantity}</span>
                    <span className="font-mono" style={{ color: 'var(--text-muted)' }}>${calcWindowPrice(w).toLocaleString()}</span>
                  </div>
                ))}
                {r.upholstery.map(u => (
                  <div key={u.id} className="flex justify-between py-0.5 pl-3 text-[10px]">
                    <span style={{ color: 'var(--text-muted)' }}>{u.name} — {u.furnitureType} ({u.fabricYards}yd)</span>
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

              {/* Mockup preferences input */}
              {photoMode === 'mockup' && !uploadedImage && !showCamera && (
                <div className="mb-3">
                  <label className="block text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>Style Preferences (optional)</label>
                  <input type="text" value={mockupPreferences} onChange={e => setMockupPreferences(e.target.value)}
                    placeholder="e.g. Modern minimalist, warm tones, motorized..."
                    className="w-full h-8 rounded-lg px-3 text-[11px] outline-none"
                    style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }} />
                </div>
              )}

              {/* Upload options */}
              {!showCamera && !uploadedImage && (
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <button onClick={startCamera} className="flex flex-col items-center gap-2 p-5 rounded-xl transition"
                    style={{ background: 'var(--raised)', border: '1px dashed var(--border)' }}>
                    <Camera className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
                    <span className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>Take Photo</span>
                  </button>
                  <button onClick={() => fileInputRef.current?.click()} className="flex flex-col items-center gap-2 p-5 rounded-xl transition"
                    style={{ background: 'var(--raised)', border: '1px dashed var(--border)' }}>
                    <Upload className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
                    <span className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>Upload Photo</span>
                  </button>
                  <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
                </div>
              )}

              {/* Image preview */}
              {uploadedImage && !showCamera && (
                <div className="relative mb-3">
                  <img src={uploadedImage} alt="Analysis" className="w-full rounded-xl" />
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

              {/* Mockup Studio results */}
              {analysisResult?.mode === 'mockup' && (
                <div className="rounded-xl p-3 mb-3 max-h-[350px] overflow-y-auto" style={{ background: 'var(--raised)', border: '1px solid rgba(236,72,153,0.2)' }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold flex items-center gap-1" style={{ color: '#ec4899' }}><Palette className="w-3 h-3" /> Design Proposals</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>{analysisResult.confidence}%</span>
                  </div>
                  {/* Room Assessment */}
                  {analysisResult.roomAssessment && (
                    <div className="rounded-lg p-2 mb-2" style={{ background: 'var(--surface)' }}>
                      <p className="text-[10px]" style={{ color: 'var(--text-primary)' }}>
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
                  {/* Proposals */}
                  {analysisResult.proposals?.map((p: any, i: number) => (
                    <div key={i} className="rounded-lg p-2.5 mb-2" style={{
                      background: 'var(--surface)',
                      border: `1px solid ${i === 0 ? 'rgba(34,197,94,0.3)' : i === 1 ? 'rgba(212,175,55,0.3)' : 'rgba(139,92,246,0.3)'}`,
                    }}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold" style={{ color: i === 0 ? '#22c55e' : i === 1 ? 'var(--gold)' : '#8B5CF6' }}>
                          {p.tier || `Option ${i + 1}`}
                        </span>
                        <span className="text-[10px] font-bold font-mono" style={{ color: 'var(--gold)' }}>
                          ${(p.price_range_low || 0).toLocaleString()} — ${(p.price_range_high || 0).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-[10px] font-semibold mb-0.5" style={{ color: 'var(--text-primary)' }}>{p.treatment_type} — {p.style}</p>
                      <p className="text-[9px] mb-1" style={{ color: 'var(--text-muted)' }}>
                        Fabric: {p.fabric} | Lining: {p.lining} | Hardware: {p.hardware}
                      </p>
                      {p.extras?.length > 0 && (
                        <p className="text-[9px] mb-1" style={{ color: 'var(--text-muted)' }}>Extras: {p.extras.join(', ')}</p>
                      )}
                      <p className="text-[10px] italic" style={{ color: 'var(--text-secondary)' }}>{p.visual_description}</p>
                    </div>
                  ))}
                  {/* Mockup Overlay — Before/After with SVG retracted panels + hardware */}
                  {uploadedImage && analysisResult.proposals?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-[10px] font-semibold mb-1.5" style={{ color: '#ec4899' }}>Visual Mockup Preview</p>
                      <div className="grid grid-cols-2 gap-2">
                        {/* Before (grayscale original) */}
                        <div className="relative rounded-lg overflow-hidden">
                          <img src={uploadedImage} alt="Before" className="w-full rounded-lg" style={{ filter: 'grayscale(100%) opacity(0.4)' }} />
                          <span className="absolute top-1 left-1 text-[8px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>Before</span>
                        </div>
                        {/* After (original + SVG overlay) */}
                        <div className="relative rounded-lg overflow-hidden">
                          <img src={uploadedImage} alt="After" className="w-full rounded-lg" />
                          <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 300" preserveAspectRatio="none">
                            {(() => {
                              const p = analysisResult.proposals[0];
                              const isRipplefold = p.treatment_type?.toLowerCase().includes('ripplefold');
                              const isLeftDraw = p.style?.toLowerCase().includes('left');
                              const isRightDraw = p.style?.toLowerCase().includes('right');
                              const fabricColor = p.fabric?.toLowerCase().includes('white') ? 'rgba(245,245,245,0.35)' :
                                p.fabric?.toLowerCase().includes('cream') ? 'rgba(255,253,230,0.35)' :
                                p.fabric?.toLowerCase().includes('navy') ? 'rgba(30,58,138,0.35)' :
                                p.fabric?.toLowerCase().includes('gray') || p.fabric?.toLowerCase().includes('grey') ? 'rgba(156,163,175,0.35)' :
                                'rgba(212,175,55,0.25)';
                              return (
                                <>
                                  {/* Hardware */}
                                  {isRipplefold ? (
                                    /* Ripplefold track bar */
                                    <rect x="20" y="18" width="360" height="6" rx="3" fill="rgba(180,180,180,0.7)" stroke="rgba(100,100,100,0.5)" strokeWidth="0.5" />
                                  ) : (
                                    <>
                                      {/* Decorative rod */}
                                      <rect x="15" y="20" width="370" height="4" rx="2" fill="rgba(180,160,120,0.8)" />
                                      {/* Rod finials */}
                                      <circle cx="15" cy="22" r="6" fill="rgba(180,160,120,0.8)" />
                                      <circle cx="385" cy="22" r="6" fill="rgba(180,160,120,0.8)" />
                                      {/* Brackets */}
                                      <rect x="130" y="14" width="4" height="16" rx="1" fill="rgba(150,140,110,0.7)" />
                                      <rect x="266" y="14" width="4" height="16" rx="1" fill="rgba(150,140,110,0.7)" />
                                    </>
                                  )}
                                  {/* Retracted panels */}
                                  {isLeftDraw ? (
                                    /* Single left panel */
                                    <rect x="20" y="24" width="80" height="265" rx="2" fill={fabricColor} />
                                  ) : isRightDraw ? (
                                    /* Single right panel */
                                    <rect x="300" y="24" width="80" height="265" rx="2" fill={fabricColor} />
                                  ) : (
                                    <>
                                      {/* Two panels, one each side */}
                                      <rect x="20" y="24" width="65" height="265" rx="2" fill={fabricColor} />
                                      <rect x="315" y="24" width="65" height="265" rx="2" fill={fabricColor} />
                                    </>
                                  )}
                                  {/* Fold lines on panels */}
                                  {!isLeftDraw && !isRightDraw && (
                                    <>
                                      <line x1="40" y1="24" x2="40" y2="289" stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
                                      <line x1="58" y1="24" x2="58" y2="289" stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
                                      <line x1="335" y1="24" x2="335" y2="289" stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
                                      <line x1="358" y1="24" x2="358" y2="289" stroke="rgba(0,0,0,0.08)" strokeWidth="1" />
                                    </>
                                  )}
                                  {/* Tier label */}
                                  <rect x="150" y="270" width="100" height="20" rx="10" fill="rgba(0,0,0,0.5)" />
                                  <text x="200" y="284" textAnchor="middle" fill="white" fontSize="10" fontWeight="bold">{p.tier || 'Proposal'}</text>
                                </>
                              );
                            })()}
                          </svg>
                          <span className="absolute top-1 left-1 text-[8px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(236,72,153,0.8)', color: '#fff' }}>After</span>
                        </div>
                      </div>
                    </div>
                  )}
                  {/* AI-Generated Mockup Images */}
                  {analysisResult.generated_images?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-[10px] font-semibold mb-1.5 flex items-center gap-1" style={{ color: '#ec4899' }}>
                        <Sparkles className="w-3 h-3" /> AI-Generated Treatment Mockups
                      </p>
                      <div className="grid grid-cols-1 gap-2">
                        {analysisResult.generated_images.map((img: any, i: number) => (
                          <div key={i} className="relative rounded-lg overflow-hidden" style={{ border: '1px solid rgba(236,72,153,0.2)' }}>
                            <a href={img.url} target="_blank" rel="noreferrer">
                              <img src={img.url} alt={`${img.tier} mockup`} className="w-full rounded-lg" style={{ maxHeight: 200, objectFit: 'cover' }} />
                            </a>
                            <span className="absolute top-1.5 left-1.5 text-[9px] px-2 py-0.5 rounded-full font-semibold"
                              style={{ background: i === 0 ? 'rgba(34,197,94,0.85)' : i === 1 ? 'rgba(212,175,55,0.85)' : 'rgba(139,92,246,0.85)', color: '#fff' }}>
                              {img.tier}
                            </span>
                            <span className="absolute bottom-1.5 right-1.5 text-[8px] px-1.5 py-0.5 rounded-full"
                              style={{ background: 'rgba(0,0,0,0.6)', color: '#fff' }}>
                              AI Generated — Click to enlarge
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {/* General Recommendations */}
                  {analysisResult.generalRecommendations?.length > 0 && (
                    <div className="mt-2">
                      <p className="text-[10px] font-semibold mb-1" style={{ color: '#ec4899' }}>Recommendations</p>
                      {analysisResult.generalRecommendations.map((r: string, i: number) => (
                        <div key={i} className="flex items-start gap-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                          <Lightbulb className="w-2.5 h-2.5 shrink-0 mt-0.5" style={{ color: '#ec4899' }} /><span>{r}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-2">
                {uploadedImage && !analysisResult && !isAnalyzing && (
                  <>
                    <button onClick={() => setUploadedImage(null)} className="flex-1 py-2 rounded-lg text-[11px]" style={{ background: 'var(--raised)', color: 'var(--text-secondary)' }}>Retake</button>
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
                    <button onClick={() => { setAnalysisResult(null); setUploadedImage(null); }} className="flex-1 py-2 rounded-lg text-[11px]" style={{ background: 'var(--raised)', color: 'var(--text-secondary)' }}>Retry</button>
                    {(analysisResult.mode === 'window' || analysisResult.mode === 'upholstery' || (analysisResult.mode === 'outline' && activeItemId)) && (
                      <button onClick={applyAnalysis} className="flex-1 py-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1"
                        style={{ background: '#22c55e', color: '#fff' }}>
                        <Check className="w-3 h-3" /> Apply
                      </button>
                    )}
                    <button onClick={closePhotoModal} className="flex-1 py-2 rounded-lg text-[11px] font-semibold"
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
