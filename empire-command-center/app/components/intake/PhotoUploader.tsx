'use client';
import { useState, useRef } from 'react';
import { Camera, Upload, Image as ImageIcon } from 'lucide-react';
import { intakeUpload } from '../../lib/intake-auth';

export default function PhotoUploader({
  projectId,
  photos,
  onUpload,
}: {
  projectId: string;
  photos: any[];
  onUpload: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const compressAndUpload = async (file: File) => {
    let toUpload = file;
    if (file.type.startsWith('image/') && file.size > 500_000) {
      try {
        const bitmap = await createImageBitmap(file);
        const maxDim = 1200;
        let w = bitmap.width, h = bitmap.height;
        if (w > maxDim || h > maxDim) {
          const ratio = Math.min(maxDim / w, maxDim / h);
          w = Math.round(w * ratio);
          h = Math.round(h * ratio);
        }
        const canvas = new OffscreenCanvas(w, h);
        const ctx = canvas.getContext('2d')!;
        ctx.drawImage(bitmap, 0, 0, w, h);
        const blob = await canvas.convertToBlob({ type: 'image/jpeg', quality: 0.8 });
        toUpload = new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' });
      } catch (_e) {
        // Fallback: upload original
      }
    }
    await intakeUpload(`/projects/${projectId}/photos`, toUpload);
  };

  const handleFiles = async (files: FileList | File[]) => {
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        await compressAndUpload(file);
      } catch (e) {
        console.error('Upload failed:', e);
      }
    }
    setUploading(false);
    onUpload();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
  };

  return (
    <div>
      <div
        className={`border-2 border-dashed rounded-[14px] p-6 text-center transition-colors ${
          dragOver ? 'border-[#b8960c] bg-[#fdf8eb]' : 'border-[#ece8e0] hover:border-[#d5d0c8]'
        }`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <Upload size={22} className="mx-auto text-[#c5c0b8] mb-2" />
        <p className="text-[12px] text-[#888] mb-3">
          {uploading ? 'Uploading...' : 'Drag photos here or'}
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2 text-[11px] font-bold bg-[#1a1a1a] text-white rounded-[10px] hover:bg-[#333] transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            <ImageIcon size={13} /> Browse Files
          </button>
          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2 text-[11px] font-semibold border border-[#ece8e0] text-[#888] rounded-[10px] hover:border-[#d5d0c8] hover:text-[#555] transition-colors disabled:opacity-50 flex items-center gap-1.5 bg-[#faf9f7]"
          >
            <Camera size={13} /> Take Photo
          </button>
        </div>
        <input ref={fileRef} type="file" accept="image/*" multiple onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
      </div>

      {photos.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 mt-4">
          {photos.map((p: any, i: number) => (
            <div key={i} className="relative aspect-square rounded-[10px] overflow-hidden bg-[#f5f2ed] border border-[#ece8e0]">
              <img
                src={`http://localhost:8000${p.path}`}
                alt={p.original_name}
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent text-white text-[8px] px-1.5 py-1 pt-3 truncate">
                {p.original_name}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
