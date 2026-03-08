'use client';
import { useState, useRef } from 'react';
import { Camera, Upload, X, Image as ImageIcon } from 'lucide-react';
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
    // Client-side compression for images
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
        className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${
          dragOver ? 'border-[#c9a84c] bg-[#fdf8eb]' : 'border-[#e5e0d8] hover:border-[#c9a84c]'
        }`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <Upload size={24} className="mx-auto text-[#aaa] mb-2" />
        <p className="text-sm text-[#777] mb-3">
          {uploading ? 'Uploading...' : 'Drag photos here or'}
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2.5 text-xs font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            <ImageIcon size={14} /> Browse Files
          </button>
          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            disabled={uploading}
            className="px-4 py-2.5 text-xs font-semibold border border-[#e5e0d8] text-[#777] rounded-lg hover:border-[#c9a84c] hover:text-[#c9a84c] transition-colors disabled:opacity-50 flex items-center gap-1.5"
          >
            <Camera size={14} /> Take Photo
          </button>
        </div>
        <input ref={fileRef} type="file" accept="image/*" multiple onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
      </div>

      {photos.length > 0 && (
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 mt-4">
          {photos.map((p: any, i: number) => (
            <div key={i} className="relative aspect-square rounded-lg overflow-hidden bg-[#f5f3ef] border border-[#e5e0d8]">
              <img
                src={`http://localhost:8000${p.path}`}
                alt={p.original_name}
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-[9px] px-1.5 py-0.5 truncate">
                {p.original_name}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
