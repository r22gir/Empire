'use client';

import React, { useState, useRef, useCallback } from 'react';
import MeasurementDiagram from './MeasurementDiagram';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ExtractedCustomer {
  name: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
}

interface ExtractedMeasurements {
  width_inches: number | null;
  height_inches: number | null;
  depth_inches: number | null;
  additional: Record<string, number>;
}

interface ExtractedItem {
  room: string;
  type: string;
  subtype: string | null;
  description: string;
  measurements: ExtractedMeasurements;
  fabric: { name: string | null; color: string | null; notes: string };
  hardware: string | null;
  quantity: number;
  lining: string | null;
  price_noted: number | null;
  special_instructions: string | null;
  confidence: number;
  fabric_match?: {
    matched_id: string;
    item_name: string;
    price: number;
    quantity_in_stock: number;
    unit: string;
    confidence: number;
  };
  diagram_svg?: string;
  diagram_summary?: string;
}

interface ExtractionResult {
  customer: ExtractedCustomer;
  project: { location: string; date: string | null; general_notes: string };
  items: ExtractedItem[];
  customer_match: {
    matched_id: string;
    matched_name: string;
    matched_email: string | null;
    matched_phone: string | null;
    matched_address: string | null;
    match_type: string;
    confidence: number;
  } | null;
  sketches_detected: boolean;
  handwriting_quality: string;
  pages_analyzed: number;
  uploaded_files: string[];
  error?: string;
}

interface NotesImporterProps {
  onQuoteCreated?: (quoteId: string, quoteNumber: string) => void;
  onClose?: () => void;
}

type Stage = 'upload' | 'extracting' | 'review' | 'creating';

export default function NotesImporter({ onQuoteCreated, onClose }: NotesImporterProps) {
  const [stage, setStage] = useState<Stage>('upload');
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approvedItems, setApprovedItems] = useState<Set<number>>(new Set());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const arr = Array.from(newFiles).filter(f => f.type.startsWith('image/'));
    if (files.length + arr.length > 5) {
      setError('Maximum 5 images allowed');
      return;
    }
    setError(null);
    const updated = [...files, ...arr];
    setFiles(updated);
    // Generate previews
    arr.forEach(f => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviews(prev => [...prev, e.target?.result as string]);
      };
      reader.readAsDataURL(f);
    });
  }, [files]);

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
    setPreviews(prev => prev.filter((_, i) => i !== index));
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleExtract = async () => {
    if (!files.length) return;
    setStage('extracting');
    setError(null);

    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    try {
      const res = await fetch(`${API}/quotes/from-notes`, { method: 'POST', body: formData });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      const data: ExtractionResult = await res.json();
      if (data.error) throw new Error(data.error);
      setResult(data);
      setStage('review');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Extraction failed');
      setStage('upload');
    }
  };

  const updateItem = (index: number, field: string, value: unknown) => {
    if (!result) return;
    const items = [...result.items];
    const item = { ...items[index] };

    if (field.startsWith('measurements.')) {
      const mField = field.split('.')[1];
      item.measurements = { ...item.measurements, [mField]: value };
    } else if (field.startsWith('fabric.')) {
      const fField = field.split('.')[1];
      item.fabric = { ...item.fabric, [fField]: value };
    } else {
      (item as Record<string, unknown>)[field] = value;
    }
    items[index] = item;
    setResult({ ...result, items });
  };

  const updateCustomer = (field: string, value: string) => {
    if (!result) return;
    setResult({ ...result, customer: { ...result.customer, [field]: value } });
  };

  const toggleApproved = (index: number) => {
    const next = new Set(approvedItems);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setApprovedItems(next);
  };

  const handleCreateDraft = async () => {
    if (!result) return;
    setStage('creating');
    setError(null);

    try {
      const res = await fetch(`${API}/quotes/from-notes/create-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: result.customer,
          project: result.project,
          items: result.items,
          customer_match: result.customer_match,
          tax_rate: 0.06,
          notes: `Extracted from ${result.pages_analyzed} page(s) of field notes`,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      onQuoteCreated?.(data.quote_id, data.quote_number);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create draft');
      setStage('review');
    }
  };

  const confidenceColor = (c: number) => {
    if (c >= 0.85) return '#16a34a';
    if (c >= 0.65) return '#ca8a04';
    return '#dc2626';
  };

  const confidenceBg = (c: number) => {
    if (c >= 0.85) return '#f0fdf4';
    if (c >= 0.65) return '#fefce8';
    return '#fef2f2';
  };

  // === UPLOAD STAGE ===
  if (stage === 'upload' || stage === 'extracting') {
    return (
      <div style={{ background: '#f5f3ef', borderRadius: 12, padding: 24, maxWidth: 700 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Import from Field Notes</h3>
          {onClose && (
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#666' }}>×</button>
          )}
        </div>

        {/* Drop zone */}
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          style={{
            border: '2px dashed #ccc', borderRadius: 8, padding: 24, textAlign: 'center',
            marginBottom: 16, background: '#fff', minHeight: 120,
          }}
        >
          {previews.length > 0 ? (
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
              {previews.map((src, i) => (
                <div key={i} style={{ position: 'relative', width: 100, height: 100 }}>
                  <img src={src} alt={`Page ${i+1}`} style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 6, border: '1px solid #ddd' }} />
                  <button
                    onClick={() => removeFile(i)}
                    style={{
                      position: 'absolute', top: -6, right: -6, width: 22, height: 22, borderRadius: '50%',
                      background: '#dc2626', color: '#fff', border: 'none', fontSize: 12, cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >×</button>
                </div>
              ))}
              {files.length < 5 && (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  style={{
                    width: 100, height: 100, borderRadius: 6, border: '2px dashed #ccc',
                    background: '#fafafa', cursor: 'pointer', fontSize: 28, color: '#999',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >+</button>
              )}
            </div>
          ) : (
            <div style={{ color: '#888' }}>
              <div style={{ fontSize: 36, marginBottom: 8 }}>📋</div>
              <p style={{ margin: 0 }}>Upload photos of your handwritten notes, measurement sketches, or client info sheets.</p>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#aaa' }}>MAX will extract everything automatically.</p>
            </div>
          )}
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <input ref={cameraInputRef} type="file" accept="image/*" multiple
            style={{ display: 'none' }} onChange={e => e.target.files && addFiles(e.target.files)} />
          <input ref={fileInputRef} type="file" accept="image/*" multiple
            style={{ display: 'none' }} onChange={e => e.target.files && addFiles(e.target.files)} />

          <button onClick={() => cameraInputRef.current?.click()} style={{
            padding: '10px 20px', borderRadius: 8, border: '1px solid #ddd', background: '#fff',
            cursor: 'pointer', fontSize: 14, minHeight: 44, flex: 1,
          }}>
            📷 Take Photo
          </button>
          <button onClick={() => fileInputRef.current?.click()} style={{
            padding: '10px 20px', borderRadius: 8, border: '1px solid #ddd', background: '#fff',
            cursor: 'pointer', fontSize: 14, minHeight: 44, flex: 1,
          }}>
            📁 Upload Files
          </button>
        </div>

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626', fontSize: 13 }}>
            {error}
          </div>
        )}

        <button
          onClick={handleExtract}
          disabled={!files.length || stage === 'extracting'}
          style={{
            width: '100%', padding: '14px 24px', borderRadius: 8, border: 'none',
            background: files.length ? '#b8960c' : '#ccc', color: '#fff',
            fontSize: 16, fontWeight: 600, cursor: files.length ? 'pointer' : 'default',
            minHeight: 48, opacity: stage === 'extracting' ? 0.7 : 1,
          }}
        >
          {stage === 'extracting' ? '⏳ Extracting... (analyzing with Grok Vision)' : 'Extract Quote Data'}
        </button>
      </div>
    );
  }

  // === REVIEW STAGE ===
  if ((stage === 'review' || stage === 'creating') && result) {
    return (
      <div style={{ background: '#f5f3ef', borderRadius: 12, padding: 24, maxWidth: 900 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>Extracted Data — Review &amp; Edit</h3>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: '#888' }}>
              {result.pages_analyzed} page(s) · {result.handwriting_quality}
            </span>
            <button onClick={() => { setStage('upload'); setResult(null); }} style={{
              padding: '6px 12px', borderRadius: 6, border: '1px solid #ddd', background: '#fff',
              cursor: 'pointer', fontSize: 13,
            }}>← Back</button>
          </div>
        </div>

        {/* Customer section */}
        <div style={{ background: '#fff', borderRadius: 8, padding: 16, marginBottom: 16, border: '1px solid #e5e5e5' }}>
          <h4 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 600, textTransform: 'uppercase', color: '#666' }}>Customer</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {(['name', 'phone', 'email', 'address'] as const).map(f => (
              <label key={f} style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 13 }}>
                <span style={{ color: '#888', textTransform: 'capitalize' }}>{f}</span>
                <input
                  value={result.customer[f] || ''}
                  onChange={e => updateCustomer(f, e.target.value)}
                  style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid #ddd', fontSize: 14 }}
                />
              </label>
            ))}
          </div>
          {result.customer_match && (
            <div style={{
              marginTop: 10, padding: '8px 12px', borderRadius: 6,
              background: result.customer_match.confidence >= 0.8 ? '#f0fdf4' : '#fefce8',
              border: `1px solid ${result.customer_match.confidence >= 0.8 ? '#bbf7d0' : '#fef08a'}`,
              fontSize: 13,
            }}>
              {result.customer_match.confidence >= 0.8 ? '✅' : '🟡'} Matched: &quot;{result.customer_match.matched_name}&quot;
              <span style={{ color: '#888', marginLeft: 8 }}>
                (DB: {result.customer_match.matched_id?.slice(0, 8)}, {Math.round(result.customer_match.confidence * 100)}% via {result.customer_match.match_type})
              </span>
            </div>
          )}
        </div>

        {/* Items */}
        {result.items.map((item, i) => (
          <div key={i} style={{
            background: '#fff', borderRadius: 8, padding: 16, marginBottom: 16, border: '1px solid #e5e5e5',
            borderLeft: `4px solid ${confidenceColor(item.confidence)}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
                ITEM {i + 1} — {item.room} {item.description && `(${item.description.slice(0, 40)})`}
              </h4>
              <span style={{
                padding: '3px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600,
                background: confidenceBg(item.confidence), color: confidenceColor(item.confidence),
              }}>
                {item.confidence.toFixed(2)}
              </span>
            </div>

            {item.confidence < 0.7 && (
              <div style={{ padding: '6px 10px', borderRadius: 6, background: '#fefce8', border: '1px solid #fef08a', fontSize: 12, marginBottom: 12, color: '#92400e' }}>
                ⚠️ Lower confidence — please verify these values
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {/* Left: editable fields */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Type</span>
                    <select
                      value={item.type}
                      onChange={e => updateItem(i, 'type', e.target.value)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }}
                    >
                      {['drapery', 'upholstery', 'cushions', 'pillows', 'cornices', 'valance', 'roman_shade', 'other'].map(t => (
                        <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                      ))}
                    </select>
                  </label>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Subtype</span>
                    <select
                      value={item.subtype || ''}
                      onChange={e => updateItem(i, 'subtype', e.target.value)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }}
                    >
                      <option value="">—</option>
                      {['pinch_pleat', 'rod_pocket', 'grommet', 'tab_top', 'ripplefold', 'eyelet', 'goblet'].map(t => (
                        <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Width (in)</span>
                    <input type="number" value={item.measurements.width_inches ?? ''}
                      onChange={e => updateItem(i, 'measurements.width_inches', e.target.value ? parseFloat(e.target.value) : null)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }} />
                  </label>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Height (in)</span>
                    <input type="number" value={item.measurements.height_inches ?? ''}
                      onChange={e => updateItem(i, 'measurements.height_inches', e.target.value ? parseFloat(e.target.value) : null)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }} />
                  </label>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Depth (in)</span>
                    <input type="number" value={item.measurements.depth_inches ?? ''}
                      onChange={e => updateItem(i, 'measurements.depth_inches', e.target.value ? parseFloat(e.target.value) : null)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }} />
                  </label>
                </div>

                <label style={{ fontSize: 13 }}>
                  <span style={{ color: '#888' }}>Fabric</span>
                  <input value={item.fabric?.name || ''}
                    onChange={e => updateItem(i, 'fabric.name', e.target.value)}
                    style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }} />
                </label>
                {item.fabric_match && (
                  <div style={{ fontSize: 12, color: '#16a34a', padding: '4px 8px', background: '#f0fdf4', borderRadius: 4 }}>
                    🔗 In stock: {item.fabric_match.quantity_in_stock} {item.fabric_match.unit} — ${item.fabric_match.price}/{item.fabric_match.unit}
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Hardware</span>
                    <input value={item.hardware || ''}
                      onChange={e => updateItem(i, 'hardware', e.target.value)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }} />
                  </label>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Lining</span>
                    <select value={item.lining || ''}
                      onChange={e => updateItem(i, 'lining', e.target.value)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }}>
                      <option value="">None</option>
                      <option value="standard">Standard</option>
                      <option value="blackout">Blackout</option>
                      <option value="thermal">Thermal</option>
                    </select>
                  </label>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Qty</span>
                    <input type="number" value={item.quantity}
                      onChange={e => updateItem(i, 'quantity', parseInt(e.target.value) || 1)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }} />
                  </label>
                  <label style={{ fontSize: 13 }}>
                    <span style={{ color: '#888' }}>Price ($)</span>
                    <input type="number" value={item.price_noted ?? ''}
                      onChange={e => updateItem(i, 'price_noted', e.target.value ? parseFloat(e.target.value) : null)}
                      style={{ width: '100%', padding: '6px 8px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, marginTop: 2 }} />
                  </label>
                </div>

                <button
                  onClick={() => toggleApproved(i)}
                  style={{
                    padding: '8px 14px', borderRadius: 6, border: 'none', fontSize: 13, cursor: 'pointer',
                    background: approvedItems.has(i) ? '#16a34a' : '#e5e5e5',
                    color: approvedItems.has(i) ? '#fff' : '#333',
                    fontWeight: 600, marginTop: 4, minHeight: 44,
                  }}
                >
                  {approvedItems.has(i) ? '✓ Approved' : 'Approve Item'}
                </button>
              </div>

              {/* Right: diagram */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                <div style={{ minWidth: 300, minHeight: 250 }}>
                  <MeasurementDiagram
                    item={{
                      type: item.type as 'window',
                      subtype: item.subtype || undefined,
                      measurements: {
                        width_inches: item.measurements.width_inches || 0,
                        height_inches: item.measurements.height_inches || 0,
                        depth_inches: item.measurements.depth_inches || undefined,
                        sill_depth: (item.measurements.additional as Record<string, number>)?.sill_depth || undefined,
                        stack_space: (item.measurements.additional as Record<string, number>)?.stack_space || undefined,
                      },
                      treatment: item.subtype || item.type,
                      mount_type: (item.measurements.additional as Record<string, unknown>)?.mount_type as string || undefined,
                      lining: item.lining || undefined,
                    }}
                    width={380}
                    height={300}
                    interactive
                    onDimensionClick={(field, value) => {
                      const newVal = prompt(`Edit ${field.replace('_', ' ')}:`, String(value));
                      if (newVal !== null) updateItem(i, `measurements.${field}`, parseFloat(newVal) || value);
                    }}
                  />
                </div>
                <span style={{ fontSize: 11, color: '#888' }}>Click dimensions to edit</span>
              </div>
            </div>
          </div>
        ))}

        {error && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, padding: 12, marginBottom: 16, color: '#dc2626', fontSize: 13 }}>
            {error}
          </div>
        )}

        <button
          onClick={handleCreateDraft}
          disabled={stage === 'creating'}
          style={{
            width: '100%', padding: '14px 24px', borderRadius: 8, border: 'none',
            background: '#b8960c', color: '#fff', fontSize: 16, fontWeight: 600,
            cursor: 'pointer', minHeight: 48, opacity: stage === 'creating' ? 0.7 : 1,
          }}
        >
          {stage === 'creating' ? '⏳ Creating Draft Quote...' : `Create Draft Quote with ${result.items.length} Items`}
        </button>
        <p style={{ textAlign: 'center', fontSize: 12, color: '#888', margin: '8px 0 0' }}>
          Creates quote + attaches diagrams for PDF inclusion
        </p>
      </div>
    );
  }

  return null;
}
