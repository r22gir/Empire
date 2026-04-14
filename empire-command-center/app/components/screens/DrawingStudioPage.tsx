'use client';
import { useState, useCallback, useRef, lazy, Suspense, useEffect } from 'react';
import { API } from '../../lib/api';
const ProductCatalogPage = lazy(() => import('./ProductCatalogPage'));

const ITEM_TYPES: { id: string; label: string; icon: string }[] = [
  { id: 'bench', label: 'Bench / Banquette', icon: '🪑' },
  { id: 'window', label: 'Window Treatment', icon: '🪟' },
  { id: 'cushion', label: 'Cushion / Pillow', icon: '🛋' },
  { id: 'chair', label: 'Chair', icon: '💺' },
  { id: 'sofa', label: 'Sofa / Sectional', icon: '🛋' },
  { id: 'headboard', label: 'Headboard', icon: '🛏' },
  { id: 'ottoman', label: 'Ottoman', icon: '🟫' },
  { id: 'millwork', label: 'Cabinet / Millwork', icon: '🪵' },
  { id: 'table', label: 'Table / Desk', icon: '🪵' },
  { id: 'generic', label: 'Other', icon: '📐' },
];

const TYPE_ICONS: Record<string, string> = {
  bench: '🪑', window: '🪟', cushion: '🛋', chair: '💺', sofa: '🛋',
  headboard: '🛏', ottoman: '🟫', millwork: '🪵', table: '🪵', generic: '📐',
};

interface AnalyzedItem {
  id: number;
  item_type: string;
  name: string;
  confidence: number;
  dimensions: Record<string, string>;
  notes: string;
  condition: string;
  work_needed: string;
}

interface AnalyzedDrawing {
  item_id: number;
  name: string;
  svg: string;
  item_type: string;
}

interface DrawingRequest {
  previewUrl: string;
  pdfUrl: string;
  body: Record<string, unknown>;
  filenameType: string;
}

interface CatalogStyle {
  style_key: string;
  style_name: string;
  business_unit: string;
}

interface CatalogCategory {
  key: string;
  name: string;
}

interface CatalogTemplateState {
  styleKey: string;
  styleName: string;
  categoryKey: string;
  categoryName: string;
  mode: string;
}

const CATALOG_TEMPLATE_DEFAULTS: Record<string, Record<string, string>> = {
  window: { width: '108"', height: '108"', drop: '108"', return: '4.5"', panels: '2', fullness: '2.5', hem: '4"', mount_type: 'outside', stack_direction: 'split' },
  banquette: { width: '120"', depth: '22"', height: '36"', seat_height: '18"', back_height: '18"', arm_configuration: 'none', base_type: 'toe_kick', cushion_segments: '4' },
  chair: { width: '32"', depth: '34"', height: '36"', seat_height: '18"', back_height: '18"', arm_height: '24"', seat_thickness: '5"', back_profile: 'straight', leg_type: 'tapered', leg_taper: '1.5"', arm_profile: 'track' },
  shelving: { width: '54"', depth: '14"', height: '84"', shelves: '5', shelf_spacing: '15"', material_thickness: '0.75"', bay_spacing: '24"', door_style: 'open', base_style: 'toe_kick' },
};

function stableSerialize(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableSerialize).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    return `{${Object.keys(value as Record<string, unknown>).sort().map((key) => (
      `${JSON.stringify(key)}:${stableSerialize((value as Record<string, unknown>)[key])}`
    )).join(',')}}`;
  }
  return JSON.stringify(value);
}

export default function DrawingStudioPage({ initialView = 'studio' }: { initialView?: 'studio' | 'catalog' } = {}) {
  const [view, setView] = useState<'studio' | 'catalog'>(initialView);
  const [itemType, setItemType] = useState('generic');
  const [name, setName] = useState('');
  const [quoteNum, setQuoteNum] = useState('');
  const [notes, setNotes] = useState('');
  const [dimensions, setDimensions] = useState<Record<string, string>>({});
  const [newDimLabel, setNewDimLabel] = useState('');
  const [newDimValue, setNewDimValue] = useState('');
  const [svgPreview, setSvgPreview] = useState('');
  const [loading, setLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [sketchLoading, setSketchLoading] = useState(false);
  const [sketchPreview, setSketchPreview] = useState('');
  const [previewSignature, setPreviewSignature] = useState('');
  const [catalogTemplate, setCatalogTemplate] = useState<CatalogTemplateState | null>(null);

  // Multi-item analysis results
  const [analyzedItems, setAnalyzedItems] = useState<AnalyzedItem[]>([]);
  const [analyzedDrawings, setAnalyzedDrawings] = useState<AnalyzedDrawing[]>([]);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [multiMode, setMultiMode] = useState(false);

  // Bench-specific
  const [benchType, setBenchType] = useState('straight');
  const [lf, setLf] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setView(initialView);
  }, [initialView]);

  const showStatus = (msg: string, duration = 4000) => {
    setStatusMsg(msg);
    if (duration > 0) setTimeout(() => setStatusMsg(''), duration);
  };

  const addDimension = () => {
    if (!newDimLabel.trim() || !newDimValue.trim()) return;
    setDimensions(prev => ({ ...prev, [newDimLabel.trim()]: newDimValue.trim() }));
    setNewDimLabel('');
    setNewDimValue('');
  };

  const removeDimension = (key: string) => {
    setDimensions(prev => {
      const copy = { ...prev };
      delete copy[key];
      return copy;
    });
  };

  const updateDimension = (key: string, value: string) => {
    setDimensions(prev => ({ ...prev, [key]: value }));
  };

  const handleSketchUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSketchLoading(true);
    setStatusMsg('');
    setAnalyzedItems([]);
    setAnalyzedDrawings([]);
    setSelectedItemId(null);
    setMultiMode(false);
    setPreviewSignature('');
    setCatalogTemplate(null);
    try {
      const reader = new FileReader();
      const b64 = await new Promise<string>((resolve) => {
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(file);
      });
      setSketchPreview(b64);

      // Try multi-item furniture analyzer first
      let multiSuccess = false;
      try {
        const mRes = await fetch(`${API}/drawings/analyze-furniture`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: b64, generate_drawings: true }),
        });
        if (mRes.ok) {
          const mData = await mRes.json();
          const items: AnalyzedItem[] = mData.items || [];
          const drawings: AnalyzedDrawing[] = (mData.drawings || []).filter((d: AnalyzedDrawing) => d.svg);

          if (items.length > 0) {
            multiSuccess = true;
            setAnalyzedItems(items);
            setAnalyzedDrawings(drawings);

            if (items.length > 1) {
              // Multi-item mode: show item cards, first drawing in preview
              setMultiMode(true);
              setSelectedItemId(items[0].id);
              const firstDrawing = drawings.find(d => d.item_id === items[0].id) || drawings.find(d => d.item_id === 0) || drawings[0];
              if (firstDrawing?.svg) {
                setSvgPreview(firstDrawing.svg);
                setPreviewSignature('');
              }
              showStatus(`Detected ${items.length} items — tap any item card to view its drawing`, 8000);
            } else {
              // Single item from multi-analyzer — populate form like before
              const item = items[0];
              const typeMap: Record<string, string> = { pillow: 'cushion', upholstery: 'chair' };
              setItemType(typeMap[item.item_type] || item.item_type);
              if (item.name) setName(item.name);
              if (item.notes) setNotes(item.notes);
              if (item.dimensions && Object.keys(item.dimensions).length > 0) {
                setDimensions(item.dimensions);
              }
              if (drawings[0]?.svg) {
                setSvgPreview(drawings[0].svg);
                setPreviewSignature('');
              }

              const typeLabel = ITEM_TYPES.find(t => t.id === item.item_type)?.label || item.item_type;
              const dimCount = Object.keys(item.dimensions || {}).length;
              showStatus(`Detected: ${typeLabel} — ${dimCount} dimensions extracted`, 6000);
            }
          }
        }
      } catch { /* fall through to legacy analyzer */ }

      // Fallback: legacy single-item analyzer
      if (!multiSuccess) {
        const res = await fetch(`${API}/drawings/analyze-sketch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: b64 }),
        });
        if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
        const data = await res.json();

        const typeMap: Record<string, string> = { pillow: 'cushion', upholstery: 'chair' };
        if (data.item_type) setItemType(typeMap[data.item_type] || data.item_type);
        if (data.name) setName(data.name);
        if (data.quote_num) setQuoteNum(data.quote_num);
        if (data.notes) setNotes(data.notes);
        if (data.dimensions && Object.keys(data.dimensions).length > 0) {
          setDimensions(data.dimensions);
        }

        if (data.item_type === 'bench' && data.bench_details) {
          const bd = data.bench_details;
          if (bd.bench_type) setBenchType(bd.bench_type);
          if (bd.total_length_ft) setLf(bd.total_length_ft);
          else if (bd.leg1_length_ft && bd.leg2_length_ft) setLf(bd.leg1_length_ft + bd.leg2_length_ft);
          else if (bd.back_length_ft) setLf(bd.back_length_ft + (bd.left_depth_ft || 0) + (bd.right_depth_ft || 0));
        }

        const typeLabel = ITEM_TYPES.find(t => t.id === data.item_type)?.label || data.item_type;
        showStatus(`Detected: ${typeLabel} — ${Object.keys(data.dimensions || {}).length} dimensions extracted. Generating drawing...`, 6000);

        try {
          let genData;
          if (data.item_type === 'bench') {
            const bd = data.bench_details || {};
            const parseDim = (key: string, def: number) => {
              const raw = (data.dimensions || {})[key];
              if (raw) { const n = parseFloat(String(raw).replace(/[^0-9.]/g, '')); if (!isNaN(n)) return n; }
              return (bd as Record<string, number>)[key] || def;
            };
            const genRes = await fetch(`${API}/drawings/bench`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                bench_type: bd.bench_type || 'straight',
                name: data.name || 'Bench',
                lf: bd.total_length_ft || 10,
                seat_depth: parseDim('seat_depth_in', 20),
                seat_height: parseDim('seat_height_in', 18),
                back_height: parseDim('back_height_in', 18),
                panel_style: bd.panel_style || 'vertical_channels',
                quote_num: data.quote_num || '',
                leg1_length: bd.leg1_length_ft || 0,
                leg2_length: bd.leg2_length_ft || 0,
                back_length: bd.back_length_ft || 0,
                left_depth: bd.left_depth_ft || 0,
                right_depth: bd.right_depth_ft || 0,
              }),
            });
            genData = await genRes.json();
          } else {
            const genRes = await fetch(`${API}/drawings/general`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                name: data.name || 'Drawing', item_type: data.item_type || 'generic',
                dimensions: data.dimensions || {}, notes: data.notes || '',
                bench_type: data.bench_details?.bench_type || 'straight',
                lf: data.bench_details?.total_length_ft || 0, quote_num: data.quote_num || '',
              }),
            });
            genData = await genRes.json();
          }
          if (genData.svg) {
            setSvgPreview(genData.svg);
            setPreviewSignature('');
          }
        } catch { /* user can still click Generate manually */ }
      }
    } catch {
      showStatus('Failed to analyze sketch');
    } finally {
      setSketchLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }, []);

  // Select an analyzed item — show its drawing and populate form
  const selectAnalyzedItem = useCallback((itemId: number) => {
    setSelectedItemId(itemId);
    const item = analyzedItems.find(i => i.id === itemId);
    const drawing = analyzedDrawings.find(d => d.item_id === itemId);
    if (drawing?.svg) {
      setSvgPreview(drawing.svg);
      setPreviewSignature('');
    }
    if (item) {
      setItemType(item.item_type);
      setName(item.name);
      setNotes(item.notes || '');
      if (item.dimensions && Object.keys(item.dimensions).length > 0) {
        setDimensions(item.dimensions);
      }
    }
  }, [analyzedItems, analyzedDrawings]);

  const hasDimensions = Object.keys(dimensions).length > 0 || (itemType === 'bench' && lf > 0);

  // Parse a dimension value from the dimensions dict
  const parseDimVal = useCallback((key: string, def: number): number => {
    for (const [k, v] of Object.entries(dimensions)) {
      if (k.toLowerCase().replace(/\s+/g, '_').includes(key)) {
        const n = parseFloat(String(v).replace(/[^0-9.]/g, ''));
        if (!isNaN(n)) return n;
      }
    }
    return def;
  }, [dimensions]);

  const buildDrawingRequest = useCallback((): DrawingRequest => {
    if (catalogTemplate) {
      const drawingMode = catalogTemplate.mode === 'shop' ? 'shop_drawing' : catalogTemplate.mode;
      const isWindow = catalogTemplate.categoryKey === 'window';
      const catalogNotes = notes || (drawingMode === 'shop_drawing'
        ? 'Shop drawing generated from Product Catalog. Verify final field measurements before fabrication.'
        : 'Presentation drawing generated from Product Catalog.');

      return {
        previewUrl: `${API}/drawings/generate`,
        pdfUrl: `${API}/drawings/generate/pdf`,
        filenameType: catalogTemplate.styleKey,
        body: {
          user_text: `${catalogTemplate.styleName} ${catalogTemplate.categoryName} ${drawingMode}`,
          params: {
            name: name || `${catalogTemplate.styleName} ${catalogTemplate.categoryName}`,
            item_type: isWindow ? 'window' : catalogTemplate.categoryKey,
            style_key: catalogTemplate.styleKey,
            drawing_mode: drawingMode,
            dimensions,
            notes: catalogNotes,
            treatment_type: isWindow ? catalogTemplate.styleKey : undefined,
            pleat_style: isWindow ? catalogTemplate.styleKey : undefined,
            mount_type: isWindow ? 'outside' : undefined,
            panels: isWindow ? 2 : undefined,
            fullness: isWindow ? 2.5 : undefined,
            stack_direction: isWindow ? 'split' : undefined,
          },
        },
      };
    }

    if (itemType === 'bench') {
      return {
        previewUrl: `${API}/drawings/bench`,
        pdfUrl: `${API}/drawings/bench/pdf`,
        filenameType: 'bench',
        body: {
          bench_type: benchType,
          name: name || 'Bench',
          lf: lf || 10,
          seat_depth: parseDimVal('seat_depth', parseDimVal('depth', 20)),
          seat_height: parseDimVal('seat_height', 18),
          back_height: parseDimVal('back_height', 18),
          panel_style: 'vertical_channels',
          quote_num: quoteNum,
        },
      };
    }

    return {
      previewUrl: `${API}/drawings/general`,
      pdfUrl: `${API}/drawings/general/pdf`,
      filenameType: itemType,
      body: {
        name: name || 'Drawing',
        item_type: itemType,
        dimensions,
        notes,
        bench_type: benchType,
        lf,
        quote_num: quoteNum,
      },
    };
  }, [benchType, catalogTemplate, dimensions, itemType, lf, name, notes, parseDimVal, quoteNum]);

  const currentPreviewSignature = stableSerialize(buildDrawingRequest().body);
  const previewIsCurrent = Boolean(svgPreview && previewSignature === currentPreviewSignature);

  const generatePreview = useCallback(async () => {
    if (!hasDimensions) return;
    setLoading(true);
    try {
      const drawingRequest = buildDrawingRequest();
      setStatusMsg('Generating professional drawing...');
      const res = await fetch(drawingRequest.previewUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(drawingRequest.body),
      });
      if (!res.ok) throw new Error(`Preview failed: ${res.status}`);
      const data = await res.json();
      setSvgPreview(data.svg || '');
      if (data.svg) {
        setPreviewSignature(stableSerialize(drawingRequest.body));
        setStatusMsg('');
      }
    } catch {
      showStatus('Preview generation failed');
    } finally {
      setLoading(false);
    }
  }, [buildDrawingRequest, hasDimensions]);

  const generateCatalogDrawing = useCallback(async (style: CatalogStyle, category: CatalogCategory, mode: string) => {
    const drawingMode = mode === 'shop' ? 'shop_drawing' : mode;
    const isWindow = category.key === 'window';
    const defaultDimensions: Record<string, string> = CATALOG_TEMPLATE_DEFAULTS[category.key] || { width: '48"', depth: '24"', height: '36"' };
    const catalogNotes = drawingMode === 'shop_drawing'
      ? 'Shop drawing generated from Product Catalog. Verify final field measurements before fabrication.'
      : 'Presentation drawing generated from Product Catalog.';
    const nextName = `${style.style_name} ${category.name}`;
    const nextDimensions = defaultDimensions;
    const nextItemType = isWindow ? 'window' : category.key;

    setView('studio');
    setItemType(nextItemType);
    setName(nextName);
    setQuoteNum('');
    setNotes(catalogNotes);
    setDimensions(nextDimensions);
    setCatalogTemplate({
      styleKey: style.style_key,
      styleName: style.style_name,
      categoryKey: category.key,
      categoryName: category.name,
      mode,
    });
    setSvgPreview('');
    setPreviewSignature('');
    setMultiMode(false);
    setAnalyzedItems([]);
    setAnalyzedDrawings([]);
    setSelectedItemId(null);
    setLoading(true);
    setStatusMsg(`Generating ${drawingMode === 'shop_drawing' ? 'shop drawing' : 'presentation drawing'} for ${style.style_name}...`);

    try {
      const res = await fetch(`${API}/drawings/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_text: `${style.style_name} ${category.name} ${drawingMode}`,
          params: {
            name: nextName,
            item_type: nextItemType,
            style_key: style.style_key,
            drawing_mode: drawingMode,
            dimensions: nextDimensions,
            notes: catalogNotes,
            treatment_type: isWindow ? style.style_key : undefined,
            pleat_style: isWindow ? style.style_key : undefined,
            mount_type: isWindow ? 'outside' : undefined,
            panels: isWindow ? 2 : undefined,
            fullness: isWindow ? 2.5 : undefined,
            stack_direction: isWindow ? 'split' : undefined,
          },
        }),
      });
      if (!res.ok) throw new Error(`Catalog drawing failed: ${res.status}`);
      const data = await res.json();
      if (!data.svg) throw new Error('Catalog drawing response did not include SVG');
      setSvgPreview(data.svg);
      setPreviewSignature(stableSerialize({
        user_text: `${style.style_name} ${category.name} ${drawingMode}`,
        params: {
          name: nextName,
          item_type: nextItemType,
          style_key: style.style_key,
          drawing_mode: drawingMode,
          dimensions: nextDimensions,
          notes: catalogNotes,
          treatment_type: isWindow ? style.style_key : undefined,
          pleat_style: isWindow ? style.style_key : undefined,
          mount_type: isWindow ? 'outside' : undefined,
          panels: isWindow ? 2 : undefined,
          fullness: isWindow ? 2.5 : undefined,
          stack_direction: isWindow ? 'split' : undefined,
        },
      }));
      setStatusMsg('');
    } catch {
      showStatus('Catalog drawing generation failed');
    } finally {
      setLoading(false);
    }
  }, [benchType, lf]);

  const downloadPdf = useCallback(async () => {
    if (!hasDimensions) return;
    setPdfLoading(true);
    try {
      const drawingRequest = buildDrawingRequest();
      const drawingSignature = stableSerialize(drawingRequest.body);
      if (previewSignature !== drawingSignature) {
        setStatusMsg('Updating drawing from current dimensions...');
        const previewRes = await fetch(drawingRequest.previewUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(drawingRequest.body),
        });
        if (!previewRes.ok) throw new Error(`Preview refresh failed: ${previewRes.status}`);
        const previewData = await previewRes.json();
        setSvgPreview(previewData.svg || '');
        setPreviewSignature(drawingSignature);
      }
      setStatusMsg('Generating PDF...');
      const res = await fetch(drawingRequest.pdfUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(drawingRequest.body),
      });
      if (!res.ok) throw new Error(`PDF failed: ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `drawing_${drawingRequest.filenameType}_${(name || 'item').replace(/\s+/g, '_')}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setStatusMsg('');
    } catch {
      showStatus('PDF download failed');
    } finally {
      setPdfLoading(false);
    }
  }, [buildDrawingRequest, hasDimensions, name, previewSignature]);

  const emailPdf = useCallback(async () => {
    setEmailLoading(true);
    try {
      const dimStr = Object.entries(dimensions).map(([k, v]) => `${k}: ${v}`).join(', ');
      const res = await fetch(`${API}/max/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Generate a ${itemType} drawing for "${name || 'Item'}" with dimensions: ${dimStr}. Email the PDF to empirebox2026@gmail.com`,
          channel: 'web_cc',
        }),
      });
      showStatus(res.ok ? 'Email sent!' : 'Failed to send');
    } catch {
      showStatus('Error sending email');
    } finally {
      setEmailLoading(false);
    }
  }, [itemType, name, dimensions]);

  const sendToDesk = useCallback(async (desk: string) => {
    const dimStr = Object.entries(dimensions).map(([k, v]) => `${k}: ${v}`).join(', ');
    try {
      const res = await fetch(`${API}/max/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Create a task for ${desk} desk: ${itemType} "${name || 'Item'}" — dimensions: ${dimStr}. ${notes}. Generate the architectural drawing PDF and attach it to the task.`,
          channel: 'web_cc',
        }),
      });
      showStatus(res.ok ? `Sent to ${desk}!` : 'Failed');
    } catch {
      showStatus('Error sending to desk');
    }
  }, [itemType, name, dimensions, notes]);

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '12px 14px', borderRadius: 10,
    border: '1.5px solid #e5e0d8', fontSize: 15, background: '#fff', color: '#333', outline: 'none', minHeight: 44,
  };
  const labelStyle: React.CSSProperties = {
    fontSize: 12, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4, display: 'block',
  };
  const btnBase: React.CSSProperties = {
    padding: '14px 24px', borderRadius: 12, border: 'none', fontSize: 15, fontWeight: 700,
    cursor: 'pointer', minHeight: 48, minWidth: 48, transition: 'all 0.15s',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
  };

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: 'inline-block', background: 'linear-gradient(135deg, #b8960c, #d4af37)',
          color: '#1a1a2e', padding: '4px 14px', borderRadius: 16, fontSize: 11,
          fontWeight: 700, letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 10,
        }}>Drawing Studio</div>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1a2e', margin: 0, lineHeight: 1.2 }}>
          Professional Drawings
        </h1>
        <p style={{ color: '#888', fontSize: 14, margin: '6px 0 0' }}>
          Upload any sketch or photo — AI identifies the item and generates a pro drawing with dimensions
        </p>
        {/* Tab toggle: Studio | Product Catalog */}
        <div style={{ marginTop: 14, display: 'flex', gap: 6 }}>
          <button onClick={() => setView('studio')} style={{
            padding: '7px 16px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer',
            background: view === 'studio' ? '#b8960c' : '#faf9f7',
            color: view === 'studio' ? '#fff' : '#888',
            border: view === 'studio' ? '1.5px solid #b8960c' : '1px solid #e5e2dc',
          }}>Drawing Studio</button>
          <button onClick={() => setView('catalog')} style={{
            padding: '7px 16px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer',
            background: view === 'catalog' ? '#b8960c' : '#faf9f7',
            color: view === 'catalog' ? '#fff' : '#888',
            border: view === 'catalog' ? '1.5px solid #b8960c' : '1px solid #e5e2dc',
          }}>📋 Product Catalog (204 styles)</button>
        </div>
      </div>

      {/* Catalog view */}
      {view === 'catalog' && (
        <Suspense fallback={<div style={{ padding: 40, textAlign: 'center', color: '#999' }}>Loading catalog...</div>}>
          <ProductCatalogPage onDrawStyle={generateCatalogDrawing} />
        </Suspense>
      )}

      {/* Studio view */}
      {view === 'studio' && <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 24, alignItems: 'start' }}>
        {/* ── Left: Controls ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Upload */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 20, border: '1.5px dashed #b8960c' }}>
            <label style={labelStyle}>Upload Sketch or Photo</label>
            <p style={{ fontSize: 12, color: '#999', margin: '4px 0 12px' }}>
              Hand drawing, measurement sketch, or photo of the item — AI extracts everything
            </p>
            <input ref={fileInputRef} type="file" accept="image/*"
              onChange={handleSketchUpload} style={{ display: 'none' }} />
            <button onClick={() => fileInputRef.current?.click()} disabled={sketchLoading} style={{
              ...btnBase, width: '100%', padding: '12px 16px', fontSize: 14,
              background: sketchLoading ? '#eee' : 'linear-gradient(135deg, #b8960c, #d4af37)',
              color: sketchLoading ? '#999' : '#1a1a2e',
            }}>
              {sketchLoading ? 'Analyzing...' : sketchPreview ? 'Upload New' : 'Upload Sketch / Photo'}
            </button>
            {sketchPreview && (
              <img src={sketchPreview} alt="Sketch" style={{
                marginTop: 10, width: '100%', maxHeight: 160, objectFit: 'contain',
                borderRadius: 8, border: '1px solid #ece8e0',
              }} />
            )}
          </div>

          {/* Multi-item cards (shown when photo has multiple items) */}
          {multiMode && analyzedItems.length > 1 && (
            <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1.5px solid #b8960c' }}>
              <label style={labelStyle}>Detected Items ({analyzedItems.length})</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                {analyzedItems.map(item => (
                  <button key={item.id} onClick={() => selectAnalyzedItem(item.id)} style={{
                    ...btnBase, width: '100%', padding: '10px 14px', fontSize: 13,
                    flexDirection: 'row', justifyContent: 'flex-start', gap: 10,
                    background: selectedItemId === item.id ? '#fdf8eb' : '#f8f6f2',
                    border: selectedItemId === item.id ? '2px solid #b8960c' : '2px solid transparent',
                    color: '#333', fontWeight: selectedItemId === item.id ? 700 : 500,
                    borderRadius: 10,
                  }}>
                    <span style={{ fontSize: 20 }}>{TYPE_ICONS[item.item_type] || '📐'}</span>
                    <span style={{ flex: 1, textAlign: 'left' }}>
                      <span style={{ display: 'block', fontSize: 13, fontWeight: 600 }}>{item.name || item.item_type}</span>
                      <span style={{ display: 'block', fontSize: 11, color: '#888' }}>
                        {item.item_type.replace(/_/g, ' ')} — {Object.keys(item.dimensions || {}).length} dims
                        {item.condition ? ` — ${item.condition}` : ''}
                      </span>
                    </span>
                    <span style={{ fontSize: 10, color: '#b8960c', fontWeight: 700 }}>
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Item Type */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Item Type</label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 5, marginTop: 6 }}>
              {ITEM_TYPES.map(t => (
                <button key={t.id} onClick={() => { setCatalogTemplate(null); setItemType(t.id); }} style={{
                  ...btnBase, padding: '8px 6px', fontSize: 11, flexDirection: 'column', gap: 1,
                  background: itemType === t.id ? '#fdf8eb' : '#f8f6f2',
                  border: itemType === t.id ? '2px solid #b8960c' : '2px solid transparent',
                  color: itemType === t.id ? '#96750a' : '#888',
                }}>
                  <span style={{ fontSize: 18 }}>{t.icon}</span>
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Name + Quote */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <div style={{ display: 'flex', gap: 10 }}>
              <div style={{ flex: 2 }}>
                <label style={labelStyle}>Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Office Windows" style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={labelStyle}>Quote #</label>
                <input value={quoteNum} onChange={e => setQuoteNum(e.target.value)} placeholder="EST-..." style={inputStyle} />
              </div>
            </div>
          </div>

          {/* Bench-specific: LF */}
          {itemType === 'bench' && (
            <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
              <label style={labelStyle}>Bench Details</label>
              <div style={{ display: 'flex', gap: 8, marginTop: 6, marginBottom: 10 }}>
                {['straight', 'l_shape', 'u_shape'].map(bt => (
                  <button key={bt} onClick={() => setBenchType(bt)} style={{
                    ...btnBase, flex: 1, padding: '8px', fontSize: 12,
                    background: benchType === bt ? '#fdf8eb' : '#f8f6f2',
                    border: benchType === bt ? '2px solid #b8960c' : '2px solid #e5e0d8',
                    color: benchType === bt ? '#96750a' : '#666',
                  }}>
                    {bt.replace('_', '-').replace(/\b\w/g, c => c.toUpperCase())}
                  </button>
                ))}
              </div>
              <label style={labelStyle}>Total Linear Feet</label>
              <input type="number" value={lf || ''} onChange={e => setLf(Number(e.target.value))} placeholder="0" style={inputStyle} />
            </div>
          )}

          {/* Dimensions */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Dimensions</label>
            {Object.keys(dimensions).length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 6, marginBottom: 10 }}>
                {Object.entries(dimensions).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, background: '#f8f6f2', padding: '8px 10px', borderRadius: 8 }}>
                    <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: '#555' }}>{k}</span>
                    <input aria-label={`${k} value`} value={v} onChange={e => updateDimension(k, e.target.value)}
                      style={{ width: 82, padding: '4px 6px', border: '1px solid #e5e0d8', borderRadius: 6, fontSize: 13, fontWeight: 700, color: '#b8960c', background: '#fff' }} />
                    <button onClick={() => removeDimension(k)} style={{
                      background: 'none', border: 'none', color: '#ccc', cursor: 'pointer', fontSize: 16, padding: '0 4px',
                    }}>×</button>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
              <input value={newDimLabel} onChange={e => setNewDimLabel(e.target.value)} placeholder="Label (e.g. Width)"
                style={{ ...inputStyle, flex: 1, fontSize: 13 }} onKeyDown={e => e.key === 'Enter' && addDimension()} />
              <input value={newDimValue} onChange={e => setNewDimValue(e.target.value)} placeholder='Value (e.g. 72")'
                style={{ ...inputStyle, flex: 1, fontSize: 13 }} onKeyDown={e => e.key === 'Enter' && addDimension()} />
              <button onClick={addDimension} style={{
                ...btnBase, padding: '8px 14px', fontSize: 18, background: '#f8f6f2', border: '1.5px solid #e5e0d8', color: '#b8960c',
              }}>+</button>
            </div>
          </div>

          {/* Notes */}
          <div style={{ background: '#fff', borderRadius: 14, padding: 16, border: '1px solid #ece8e0' }}>
            <label style={labelStyle}>Notes</label>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Additional notes..."
              style={{ ...inputStyle, minHeight: 60, resize: 'vertical', fontFamily: 'inherit' }} />
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button onClick={generatePreview} disabled={loading || !hasDimensions} style={{
              ...btnBase, width: '100%',
              background: hasDimensions ? 'linear-gradient(135deg, #b8960c, #d4af37)' : '#ddd',
              color: hasDimensions ? '#1a1a2e' : '#999',
            }}>
              {loading ? 'Generating...' : previewIsCurrent ? 'Regenerate Drawing' : svgPreview ? 'Update Drawing' : 'Generate Drawing'}
            </button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={downloadPdf} disabled={pdfLoading || !hasDimensions} style={{
                ...btnBase, flex: 1, background: hasDimensions ? '#1a1a2e' : '#eee', color: hasDimensions ? '#d4af37' : '#bbb',
              }}>
                {pdfLoading ? '...' : svgPreview && !previewIsCurrent ? 'Update + PDF' : 'Download PDF'}
              </button>
              <button onClick={emailPdf} disabled={emailLoading || !svgPreview} style={{
                ...btnBase, flex: 1, background: svgPreview ? '#16a34a' : '#eee', color: svgPreview ? '#fff' : '#bbb',
              }}>
                {emailLoading ? '...' : 'Email PDF'}
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={() => sendToDesk('Workroom')} disabled={!svgPreview} style={{
                ...btnBase, flex: 1, padding: '10px', fontSize: 12,
                background: svgPreview ? '#1a1a2e' : '#eee', color: svgPreview ? '#fff' : '#bbb',
              }}>Workroom</button>
              <button onClick={() => sendToDesk('WoodCraft')} disabled={!svgPreview} style={{
                ...btnBase, flex: 1, padding: '10px', fontSize: 12,
                background: svgPreview ? '#ca8a04' : '#eee', color: svgPreview ? '#fff' : '#bbb',
              }}>WoodCraft</button>
            </div>
            {statusMsg && (
              <div style={{
                textAlign: 'center', fontSize: 13, fontWeight: 600, padding: '8px', borderRadius: 8,
                background: statusMsg.includes('Detected') ? '#fdf8eb' : statusMsg.includes('sent') || statusMsg.includes('Sent') ? '#f0fdf4' : '#fef2f2',
                color: statusMsg.includes('Detected') ? '#b8960c' : statusMsg.includes('sent') || statusMsg.includes('Sent') ? '#16a34a' : '#ef4444',
              }}>
                {statusMsg}
              </div>
            )}
            {svgPreview && !previewIsCurrent && !statusMsg && (
              <div style={{
                textAlign: 'center', fontSize: 12, fontWeight: 600, padding: '8px', borderRadius: 8,
                background: '#fff7ed', color: '#c2410c', border: '1px solid #fed7aa',
              }}>
                Preview needs updating from the current dimensions.
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Preview ── */}
        <div style={{
          background: '#fff', borderRadius: 14, border: '1px solid #ece8e0',
          minHeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden',
        }}>
          {svgPreview ? (
            <div dangerouslySetInnerHTML={{ __html: svgPreview }} style={{ width: '100%', padding: 16 }} />
          ) : (
            <div style={{ textAlign: 'center', color: '#ccc', padding: 40 }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>&#9998;</div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Upload a sketch or enter dimensions</div>
              <div style={{ fontSize: 13, marginTop: 6 }}>AI generates professional drawings for any item type</div>
            </div>
          )}
        </div>
      </div>}

      <style>{`
        @media (max-width: 768px) {
          div[style*="grid-template-columns: 380px"] { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </div>
  );
}
