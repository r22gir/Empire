'use client';
import { useState, useRef } from 'react';
import { Camera, Upload, FileText, Archive, Box, Film, File as FileIcon } from 'lucide-react';
import { intakeUpload } from '../../lib/intake-auth';
import { isImageFile, fileKind, fileKindLabel, formatFileSize } from '../../lib/fileKind';
import { API_BASE } from '../../lib/api';

const KIND_ICON: Record<string, typeof FileText> = {
  pdf: FileText,
  doc: FileText,
  sheet: FileText,
  archive: Archive,
  cad: Box,
  '3d-scan': Box,
  video: Film,
  file: FileIcon,
};

export default function PhotoUploader({
  projectId,
  photos,
  scans,
  onUpload,
}: {
  projectId: string;
  photos: any[];
  scans?: any[];
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

  // Designers can upload anything here: photos, PDFs, CAD (dwg/dxf/skp/
  // rvt/3dm), 3D scans (usdz/obj/ply/glb/gltf/fbx/stl/e57), spreadsheets,
  // docs, zip, video. Images go through the existing /photos endpoint
  // (with client-side compression); everything else goes to /scans,
  // which stores the file as-is.
  const uploadOne = async (file: File) => {
    if (file.type.startsWith('image/') || isImageFile(file.name)) {
      await compressAndUpload(file);
    } else {
      await intakeUpload(`/projects/${projectId}/scans`, file);
    }
  };

  const handleFiles = async (files: FileList | File[]) => {
    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        await uploadOne(file);
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

  // Combine photos + scans into one display list, each item tagged with
  // its source path so we know which the user is looking at.
  const files = [
    ...photos.map((p: any) => ({ ...p, _source: 'photos' as const })),
    ...(scans || []).map((s: any) => ({ ...s, _source: 'scans' as const })),
  ];

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
          {uploading ? 'Uploading...' : 'Drag files here or'}
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="w-full sm:w-auto px-5 py-3 min-h-[44px] text-sm font-bold bg-[#1a1a1a] text-white rounded-[10px] hover:bg-[#333] transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
          >
            <Upload size={16} /> Browse Files
          </button>
          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            disabled={uploading}
            className="w-full sm:w-auto px-5 py-3 min-h-[44px] text-sm font-semibold border border-[#ece8e0] text-[#888] rounded-[10px] hover:border-[#d5d0c8] hover:text-[#555] transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5 bg-[#faf9f7]"
          >
            <Camera size={16} /> Take Photo
          </button>
        </div>
        <p className="text-[10px] text-[#bbb] mt-3">
          Photos, drawings, CAD &amp; 3D scans, PDFs, spreadsheets, docs, zip, and video are all accepted.
        </p>
        {/* "Browse Files" accepts any file type — designers attach CAD,
            3D scans, PDFs, etc. "Take Photo" opens the camera, so it
            stays image-only (that's what a camera captures). */}
        <input ref={fileRef} type="file" multiple onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
        <input ref={cameraRef} type="file" accept="image/*" onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
      </div>

      {files.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 mt-4">
          {files.map((p: any, i: number) => {
            const name = p.original_name || p.filename || `File ${i + 1}`;
            if (isImageFile(name)) {
              return (
                <div key={i} className="relative aspect-square rounded-[10px] overflow-hidden bg-[#f5f2ed] border border-[#ece8e0]">
                  <img
                    src={`${API_BASE}${p.path}`}
                    alt={name}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent text-white text-[8px] px-1.5 py-1 pt-3 truncate">
                    {name}
                  </div>
                </div>
              );
            }
            const Icon = KIND_ICON[fileKind(name)] || FileIcon;
            return (
              <a
                key={i}
                href={`${API_BASE}${p.path}`}
                target="_blank"
                rel="noopener noreferrer"
                className="relative aspect-square rounded-[10px] overflow-hidden bg-[#f5f2ed] border border-[#ece8e0] flex flex-col items-center justify-center gap-1.5 p-2 text-center hover:border-[#b8960c] transition-colors"
                title={name}
              >
                <Icon size={22} className="text-[#b8960c]" />
                <span className="text-[9px] font-semibold text-[#555] truncate w-full">{name}</span>
                <span className="text-[8px] text-[#aaa]">
                  {fileKindLabel(name)}{p.size ? ` · ${formatFileSize(p.size)}` : ''}
                </span>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
