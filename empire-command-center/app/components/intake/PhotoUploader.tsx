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

type QueueItem = {
  id: string;
  name: string;
  preview?: string;
  status: 'uploading' | 'done' | 'error';
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
  const [queue, setQueue] = useState<QueueItem[]>([]);
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
    const list = Array.from(files);
    const items: QueueItem[] = list.map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      name: file.name,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
      status: 'uploading',
    }));
    setQueue(items);
    setUploading(true);
    for (let i = 0; i < list.length; i++) {
      try {
        await uploadOne(list[i]);
        setQueue((prev) => prev.map((item, idx) => idx === i ? { ...item, status: 'done' } : item));
      } catch (e) {
        console.error('Upload failed:', e);
        setQueue((prev) => prev.map((item, idx) => idx === i ? { ...item, status: 'error' } : item));
      }
    }
    setUploading(false);
    onUpload();
    setQueue((prev) => (prev.every((item) => item.status === 'done') ? [] : prev));
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

  const doneCount = queue.filter((q) => q.status === 'done').length;
  const progressPct = queue.length ? Math.round((doneCount / queue.length) * 100) : 0;

  return (
    <div>
      <div
        className={`intake-dropzone ${dragOver ? 'intake-dropzone-active' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <Upload size={28} className="mx-auto mb-3" style={{ color: '#6b5408' }} aria-hidden="true" />
        <p className="text-base font-semibold mb-1" style={{ color: '#1a1a2e' }}>
          {uploading ? 'Uploading…' : 'Drop files here, or tap to add'}
        </p>
        <p className="text-sm mb-4" style={{ color: '#4f4a40' }}>
          Photos, drawings, CAD, 3D scans, PDFs, spreadsheets, docs, zip, and video.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="intake-btn intake-btn-charcoal w-full sm:w-auto"
          >
            <Upload size={16} aria-hidden="true" /> Browse Files
          </button>
          <button
            type="button"
            onClick={() => cameraRef.current?.click()}
            disabled={uploading}
            className="intake-btn intake-btn-ghost w-full sm:w-auto"
          >
            <Camera size={16} aria-hidden="true" /> Take Photo
          </button>
        </div>
        {/* "Browse Files" accepts any file type — designers attach CAD,
            3D scans, PDFs, etc. "Take Photo" opens the camera, so it
            stays image-only (that's what a camera captures). */}
        <input ref={fileRef} type="file" multiple onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
        <input ref={cameraRef} type="file" accept="image/*" onChange={e => e.target.files && handleFiles(e.target.files)} className="hidden" />
      </div>

      {queue.length > 0 && (
        <div className="mt-4" aria-live="polite">
          <div className="flex items-center justify-between text-sm mb-1" style={{ color: '#4f4a40' }}>
            <span>{uploading ? `Uploading ${doneCount + 1} of ${queue.length}` : `${doneCount} of ${queue.length} uploaded`}</span>
            <span>{progressPct}%</span>
          </div>
          <div className="intake-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progressPct}>
            <span style={{ width: `${progressPct}%` }} />
          </div>
          <div className="intake-file-grid">
            {queue.map((item) => {
              const Icon = KIND_ICON[fileKind(item.name)] || FileIcon;
              return (
                <div key={item.id} className="intake-file-tile">
                  {item.preview ? (
                    <img src={item.preview} alt="" />
                  ) : (
                    <Icon size={22} style={{ color: '#6b5408' }} aria-hidden="true" />
                  )}
                  <span className="absolute bottom-0 left-0 right-0 text-[11px] font-semibold px-1.5 py-1 truncate" style={{ background: 'rgba(26,26,46,0.72)', color: '#fff' }}>
                    {item.status === 'error' ? 'Failed · ' : item.status === 'uploading' ? 'Uploading · ' : ''}{item.name}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {files.length > 0 && (
        <div className="intake-file-grid" style={{ marginTop: queue.length ? 12 : 16 }}>
          {files.map((p: any, i: number) => {
            const name = p.original_name || p.filename || `File ${i + 1}`;
            if (isImageFile(name)) {
              return (
                <div key={i} className="intake-file-tile">
                  <img
                    src={`${API_BASE}${p.path}`}
                    alt={name}
                  />
                  <div className="absolute bottom-0 left-0 right-0 text-[11px] font-semibold px-1.5 py-1 pt-3 truncate" style={{ background: 'linear-gradient(to top, rgba(26,26,46,0.72), transparent)', color: '#fff' }}>
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
                className="intake-file-tile"
                title={name}
              >
                <Icon size={22} style={{ color: '#6b5408' }} aria-hidden="true" />
                <span className="text-xs font-semibold truncate w-full" style={{ color: '#3d3a32' }}>{name}</span>
                <span className="text-[11px]" style={{ color: '#4f4a40' }}>
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
