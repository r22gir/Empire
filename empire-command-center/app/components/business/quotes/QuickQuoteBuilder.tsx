'use client';

import React, { useState, useRef } from 'react';
import { Zap, Upload, Loader2, CheckCircle, FileText, X, ImageIcon, Camera } from 'lucide-react';
import { API } from '../../../lib/api';

interface QuickQuoteBuilderProps {
  onClose?: () => void;
  onQuoteCreated?: (quote: any) => void;
}

export default function QuickQuoteBuilder({ onClose, onQuoteCreated }: QuickQuoteBuilderProps) {
  const [customerName, setCustomerName] = useState('');
  const [description, setDescription] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageFilename, setImageFilename] = useState('');
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    setImageFile(file);
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API.replace('/api/v1', '')}/api/v1/files/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      setImageFilename(data.filename || data.file_name || file.name);
    } catch {
      setError('Photo upload failed. You can still generate a quote without it.');
      setImageFile(null);
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyzePhoto = async () => {
    if (!imageFile) return;
    setAnalyzing(true);
    try {
      const reader = new FileReader();
      const base64 = await new Promise<string>((resolve) => {
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(imageFile);
      });
      const res = await fetch(`${API}/vision/measure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64 }),
      });
      if (!res.ok) throw new Error('Analysis failed');
      const data = await res.json();
      setAnalysisResult(data);
      // Auto-fill description if empty
      if (!description.trim()) {
        const desc = `${data.window_type || 'Window'} — ${data.width_inches}"W × ${data.height_inches}"H. ${(data.treatment_suggestions || []).join(', ')}`;
        setDescription(desc);
      }
    } catch {
      setError('Photo analysis failed. You can still generate the quote manually.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSubmit = async () => {
    if (!customerName.trim() || !description.trim()) {
      setError('Please enter customer name and project description.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const body: any = {
        customer_name: customerName.trim(),
        description: description.trim(),
      };
      if (imageFilename) body.image_filename = imageFilename;

      const res = await fetch(`${API}/quotes/quick`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      const data = await res.json();
      setResult(data);
      onQuoteCreated?.(data);
    } catch {
      setError('Failed to generate quote. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="empire-card" style={{ padding: 0 }}>
        <div className="flex items-center justify-between" style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
          <h3 className="flex items-center gap-2 text-sm font-bold text-[#1a1a1a]">
            <CheckCircle size={16} className="text-[#22c55e]" /> Quote Generated
          </h3>
          {onClose && (
            <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-[#f0ede8] transition-colors cursor-pointer">
              <X size={16} className="text-[#999]" />
            </button>
          )}
        </div>
        <div style={{ padding: '20px' }}>
          <div style={{ padding: 16, borderRadius: 12, background: '#f0fdf4', border: '1px solid #bbf7d0', marginBottom: 16 }}>
            <div style={{ fontSize: 11, color: '#16a34a', fontWeight: 700, marginBottom: 4 }}>QUOTE NUMBER</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{result.quote_number || result.id || 'Generated'}</div>
            <div style={{ fontSize: 12, color: '#555', marginTop: 4 }}>{result.customer_name || customerName}</div>
            {result.total != null && (
              <div style={{ fontSize: 16, fontWeight: 700, color: '#b8960c', marginTop: 8 }}>${Number(result.total).toLocaleString()}</div>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { setResult(null); setCustomerName(''); setDescription(''); setImageFile(null); setImageFilename(''); setAnalysisResult(null); }}
              className="flex-1 flex items-center justify-center gap-1.5 cursor-pointer font-bold transition-all hover:bg-[#f0ede8]"
              style={{ height: 40, fontSize: 12, borderRadius: 12, border: '1.5px solid #ece8e0', background: '#faf9f7', color: '#555' }}
            >
              <Zap size={14} /> New Quote
            </button>
            {result.id && (
              <button
                onClick={() => window.location.hash = `quote-review-${result.id}`}
                className="flex-1 flex items-center justify-center gap-1.5 cursor-pointer font-bold transition-all hover:bg-[#a08509]"
                style={{ height: 40, fontSize: 12, borderRadius: 12, background: '#b8960c', color: '#fff', border: 'none' }}
              >
                <FileText size={14} /> Review Quote
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="empire-card" style={{ padding: 0 }}>
      <div className="flex items-center justify-between" style={{ padding: '14px 20px', borderBottom: '1px solid #ece8e0' }}>
        <h3 className="flex items-center gap-2 text-sm font-bold text-[#1a1a1a]">
          <Zap size={16} className="text-[#b8960c]" /> Quick Quote Builder
        </h3>
        {onClose && (
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-[#f0ede8] transition-colors cursor-pointer">
            <X size={16} className="text-[#999]" />
          </button>
        )}
      </div>
      <div style={{ padding: '20px' }}>
        {error && (
          <div style={{ padding: '10px 14px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', fontSize: 12, color: '#dc2626', fontWeight: 600, marginBottom: 14 }}>
            {error}
          </div>
        )}

        {/* Customer Name */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
            Customer Name *
          </label>
          <input
            type="text"
            value={customerName}
            onChange={e => setCustomerName(e.target.value)}
            placeholder="e.g. Sarah Johnson"
            className="w-full outline-none focus:border-[#b8960c] transition-colors"
            style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 12, background: '#faf9f7' }}
          />
        </div>

        {/* Description */}
        <div style={{ marginBottom: 14 }}>
          <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
            Project Description *
          </label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="e.g. Living room curtains, 3 windows, 96 inches wide each, blackout lining..."
            rows={3}
            className="w-full outline-none focus:border-[#b8960c] transition-colors resize-none"
            style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 12, background: '#faf9f7' }}
          />
        </div>

        {/* Photo Upload */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
            Photo (Optional)
          </label>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={e => {
              const f = e.target.files?.[0];
              if (f) handleFileUpload(f);
            }}
          />
          {imageFile ? (
            <div className="flex items-center gap-2" style={{ padding: '10px 14px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
              <ImageIcon size={16} className="text-[#b8960c]" />
              <span style={{ fontSize: 12, color: '#555', flex: 1 }}>{imageFile.name}</span>
              {uploading ? (
                <Loader2 size={14} className="text-[#b8960c] animate-spin" />
              ) : (
                <button onClick={() => { setImageFile(null); setImageFilename(''); }} className="p-1 rounded-lg hover:bg-[#f0ede8] cursor-pointer">
                  <X size={14} className="text-[#999]" />
                </button>
              )}
            </div>
          ) : (
            <button
              onClick={() => fileRef.current?.click()}
              className="w-full flex items-center justify-center gap-2 cursor-pointer hover:bg-[#f0ede8] transition-colors"
              style={{ padding: '12px', borderRadius: 12, border: '1.5px dashed #d8d3cb', background: '#faf9f7', fontSize: 12, fontWeight: 600, color: '#888' }}
            >
              <Upload size={16} /> Attach a photo
            </button>
          )}
        </div>

        {/* AI Analysis */}
        {imageFile && !uploading && (
          <div style={{ marginBottom: 18 }}>
            <button
              onClick={handleAnalyzePhoto}
              disabled={analyzing}
              className="w-full flex items-center justify-center gap-2 cursor-pointer font-bold transition-all hover:bg-[#6d28d9]"
              style={{ height: 40, fontSize: 12, borderRadius: 12, background: '#7c3aed', color: '#fff', border: 'none' }}
            >
              {analyzing ? <Loader2 size={14} className="animate-spin" /> : <Camera size={14} />}
              {analyzing ? 'Analyzing Photo...' : 'AI Analyze Photo'}
            </button>
            {analysisResult && (
              <div style={{ marginTop: 12, padding: 14, borderRadius: 12, background: '#f5f0ff', border: '1px solid #ddd6fe' }}>
                <div className="section-label" style={{ color: '#7c3aed', marginBottom: 8 }}>AI Measurement</div>
                <div className="flex items-center gap-4 mb-2">
                  <div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{analysisResult.width_inches}&quot; × {analysisResult.height_inches}&quot;</div>
                    <div style={{ fontSize: 10, color: '#777' }}>{analysisResult.window_type}</div>
                  </div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: analysisResult.confidence > 70 ? '#16a34a' : '#d97706' }}>
                    {analysisResult.confidence}% confidence
                  </div>
                </div>
                {analysisResult.treatment_suggestions?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {analysisResult.treatment_suggestions.map((s: string, i: number) => (
                      <span key={i} style={{ fontSize: 9, padding: '3px 8px', borderRadius: 6, background: '#ede9fe', color: '#7c3aed', fontWeight: 600 }}>{s}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={submitting || uploading || !customerName.trim() || !description.trim()}
          className="w-full flex items-center justify-center gap-2 cursor-pointer font-bold transition-all hover:bg-[#a08509] disabled:opacity-50 active:scale-[0.98]"
          style={{ height: 44, fontSize: 13, borderRadius: 12, background: '#b8960c', color: '#fff', border: 'none', boxShadow: '0 2px 8px rgba(184,150,12,0.25)' }}
        >
          {submitting ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
          Generate Quote
        </button>
      </div>
    </div>
  );
}
