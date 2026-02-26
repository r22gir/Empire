'use client';
import { useState, useCallback } from 'react';
import { TREATMENT_TYPES, MOCK_FABRICS, TreatmentType } from '@/lib/deskData';
import { Upload, ImageIcon, Ruler, Grid3X3 } from 'lucide-react';
import { TaskList } from './shared';

export default function DesignDesk() {
  const [selectedTreatment, setSelectedTreatment] = useState<TreatmentType>('drapes');
  const [dragActive, setDragActive] = useState(false);
  const [uploadedImages, setUploadedImages] = useState<string[]>([]);
  const [measurements, setMeasurements] = useState({ width: '', height: '' });

  const filteredFabrics = MOCK_FABRICS.filter(
    f => f.treatment === selectedTreatment || selectedTreatment === 'drapes'
  );

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation(); setDragActive(false);
    const files = e.dataTransfer.files;
    for (let i = 0; i < files.length; i++) {
      if (files[i].type.startsWith('image/')) setUploadedImages(prev => [...prev, URL.createObjectURL(files[i])]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (let i = 0; i < files.length; i++) {
      if (files[i].type.startsWith('image/')) setUploadedImages(prev => [...prev, URL.createObjectURL(files[i])]);
    }
    e.target.value = '';
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Treatment selector */}
      <div className="flex gap-2 p-4 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-xs font-semibold self-center mr-2" style={{ color: 'var(--text-muted)' }}>Treatment:</span>
        {TREATMENT_TYPES.map(t => (
          <button key={t.value} onClick={() => setSelectedTreatment(t.value)}
            className="px-3 py-2 rounded-xl text-xs font-medium transition flex items-center gap-1.5"
            style={{
              background: selectedTreatment === t.value ? 'var(--gold-pale)' : 'var(--surface)',
              color: selectedTreatment === t.value ? 'var(--gold)' : 'var(--text-secondary)',
              border: selectedTreatment === t.value ? '1px solid var(--gold-border)' : '1px solid var(--border)',
            }}
          ><span>{t.icon}</span> {t.label}</button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-4 grid grid-cols-3 gap-4">
        {/* Left: Photo upload + measurement */}
        <div className="col-span-1 flex flex-col gap-4">
          <div className="rounded-xl p-4 flex flex-col items-center justify-center text-center transition"
            style={{ background: dragActive ? 'var(--gold-pale)' : 'var(--surface)', border: dragActive ? '2px dashed var(--gold)' : '2px dashed var(--border)', minHeight: 180 }}
            onDragEnter={handleDrag} onDragOver={handleDrag} onDragLeave={handleDrag} onDrop={handleDrop}
          >
            {uploadedImages.length > 0 ? (
              <div className="grid grid-cols-2 gap-2 w-full">
                {uploadedImages.map((img, i) => (
                  <div key={i} className="relative rounded-lg overflow-hidden aspect-video">
                    <img src={img} alt={`Upload ${i + 1}`} className="w-full h-full object-cover" />
                    <button onClick={() => setUploadedImages(prev => prev.filter((_, j) => j !== i))}
                      className="absolute top-1 right-1 w-5 h-5 rounded-full flex items-center justify-center text-[10px]"
                      style={{ background: 'rgba(0,0,0,0.7)', color: '#fff' }}>×</button>
                  </div>
                ))}
              </div>
            ) : (
              <>
                <Upload className="w-8 h-8 mb-2" style={{ color: dragActive ? 'var(--gold)' : 'var(--text-muted)' }} />
                <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Drop window photos here</p>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>xAI Vision integration coming soon</p>
              </>
            )}
            <label className="mt-3 px-3 py-1.5 rounded-lg text-[10px] font-semibold cursor-pointer transition" style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
              Browse Photos
              <input type="file" accept="image/*" multiple className="hidden" onChange={handleFileSelect} />
            </label>
          </div>

          <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2 mb-3">
              <Ruler className="w-4 h-4" style={{ color: 'var(--cyan)' }} />
              <p className="text-xs font-semibold" style={{ color: 'var(--gold)' }}>Measurements</p>
            </div>
            <div className="grid grid-cols-2 gap-2 mb-3">
              {(['width', 'height'] as const).map(dim => (
                <div key={dim}>
                  <label className="text-[10px] block mb-1 capitalize" style={{ color: 'var(--text-muted)' }}>{dim} (in)</label>
                  <input type="text" value={measurements[dim]}
                    onChange={e => setMeasurements(p => ({ ...p, [dim]: e.target.value }))}
                    placeholder={dim === 'width' ? '72' : '84'}
                    className="w-full rounded-lg px-2.5 py-2 text-xs outline-none font-mono"
                    style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                  />
                </div>
              ))}
            </div>
            {measurements.width && measurements.height ? (
              <div className="rounded-lg p-2.5" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
                <p className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{measurements.width}&quot; × {measurements.height}&quot;</p>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#22c55e' }} />
                  <span className="text-[10px]" style={{ color: '#22c55e' }}>Manual entry — 100% confidence</span>
                </div>
              </div>
            ) : (
              <p className="text-[10px] text-center py-2" style={{ color: 'var(--text-muted)' }}>Enter measurements or upload photo for AI analysis</p>
            )}
          </div>

          <TaskList desk="design" compact />
        </div>

        {/* Right: Fabric browser */}
        <div className="col-span-2 rounded-xl flex flex-col" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <div className="px-4 pt-3 pb-2 flex items-center gap-2 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
            <Grid3X3 className="w-4 h-4" style={{ color: 'var(--gold)' }} />
            <p className="text-xs font-semibold" style={{ color: 'var(--gold)' }}>Fabric & Material Browser</p>
            <span className="text-[10px] ml-auto" style={{ color: 'var(--text-muted)' }}>{filteredFabrics.length} options</span>
          </div>
          <div className="flex-1 overflow-y-auto p-3">
            <div className="grid grid-cols-4 gap-3">
              {filteredFabrics.map(fabric => (
                <div key={fabric.id} className="rounded-xl overflow-hidden transition group cursor-pointer"
                  style={{ border: '1px solid var(--border)' }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--gold-border)')}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}>
                  <div className="aspect-square flex items-center justify-center" style={{ background: fabric.color }}>
                    <ImageIcon className="w-6 h-6 opacity-20" style={{ color: '#fff' }} />
                  </div>
                  <div className="p-2.5" style={{ background: 'var(--raised)' }}>
                    <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>{fabric.name}</p>
                    <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{fabric.collection}</p>
                    <p className="text-[10px] font-mono mt-1" style={{ color: 'var(--gold)' }}>${fabric.pricePerYard}/yd</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
