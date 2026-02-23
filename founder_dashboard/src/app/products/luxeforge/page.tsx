'use client';

import { useState, useEffect, useCallback } from 'react';
import CameraCapture from './components/CameraCapture';
import ImageUploader from './components/ImageUploader';
import ImageGallery from './components/ImageGallery';
import ImageViewer from './components/ImageViewer';

const API_BASE = process.env.NEXT_PUBLIC_API_URL
  ? process.env.NEXT_PUBLIC_API_URL.replace('/api/v1', '')
  : 'http://localhost:8000';

const IMAGES_API = `${API_BASE}/api/luxeforge/images`;

interface LuxeImage {
  id: string;
  original_name: string;
  thumbnail_path: string;
  file_path: string;
  size: number;
  mime_type: string;
  created_at: string;
}

type Tab = 'camera' | 'upload' | 'gallery';

export default function LuxeForgePage() {
  const [tab, setTab] = useState<Tab>('camera');
  const [images, setImages] = useState<LuxeImage[]>([]);
  const [viewImage, setViewImage] = useState<LuxeImage | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const fetchImages = useCallback(async () => {
    try {
      const res = await fetch(IMAGES_API);
      if (!res.ok) throw new Error('Failed to load images');
      const data: LuxeImage[] = await res.json();
      setImages(data);
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    fetchImages();
  }, [fetchImages]);

  // Upload a File object
  const uploadFile = async (file: File): Promise<boolean> => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${IMAGES_API}/upload`, { method: 'POST', body: form });
    return res.ok;
  };

  // Upload a data URL (from camera capture)
  const handleCameraCapture = async (dataUrl: string) => {
    const blob = await (await fetch(dataUrl)).blob();
    const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
    setUploading(true);
    setUploadProgress(50);
    setError(null);
    try {
      const ok = await uploadFile(file);
      if (!ok) throw new Error('Upload failed');
      setUploadProgress(100);
      await fetchImages();
      setTab('gallery');
    } catch {
      setError('Failed to save captured image.');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleUpload = async (files: File[]) => {
    setUploading(true);
    setError(null);
    let completed = 0;
    let failed = 0;
    for (const file of files) {
      try {
        await uploadFile(file);
      } catch {
        failed++;
      }
      completed++;
      setUploadProgress(Math.round((completed / files.length) * 100));
    }
    await fetchImages();
    setUploading(false);
    setUploadProgress(0);
    if (failed > 0) {
      setError(`${failed} of ${files.length} image(s) failed to upload.`);
    }
    setTab('gallery');
  };

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`${IMAGES_API}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      setImages(prev => prev.filter(img => img.id !== id));
    } catch {
      setError('Failed to delete image.');
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: 'camera', label: '📷 Camera' },
    { key: 'upload', label: '⬆️ Upload' },
    { key: 'gallery', label: `🖼️ Gallery (${images.length})` },
  ];

  return (
    <div className="min-h-screen bg-[#050508] text-white">
      {/* Header */}
      <div className="bg-[#0a0a0f] border-b border-gray-800 px-6 py-4">
        <h1 className="text-2xl font-bold text-purple-400">LuxeForge</h1>
        <p className="text-sm text-gray-400">Camera &amp; Image Management</p>
      </div>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* Tab bar */}
        <div className="flex gap-2">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors
                ${tab === t.key
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Error banner */}
        {error && (
          <div className="bg-red-900/40 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="ml-4 text-red-400 hover:text-red-300">✕</button>
          </div>
        )}

        {/* Tab content */}
        {tab === 'camera' && (
          <div className="bg-[#0a0a0f] border border-gray-800 rounded-xl p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-200">Capture Photo</h2>
            <CameraCapture onCapture={handleCameraCapture} />
            {uploading && (
              <p className="text-sm text-purple-400 text-center animate-pulse">Saving captured image…</p>
            )}
          </div>
        )}

        {tab === 'upload' && (
          <div className="bg-[#0a0a0f] border border-gray-800 rounded-xl p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-200">Upload Images</h2>
            <ImageUploader
              onUpload={handleUpload}
              uploading={uploading}
              progress={uploadProgress}
            />
          </div>
        )}

        {tab === 'gallery' && (
          <div className="bg-[#0a0a0f] border border-gray-800 rounded-xl p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-200">Image Gallery</h2>
            <ImageGallery
              images={images}
              onDelete={handleDelete}
              onView={img => setViewImage(img)}
            />
          </div>
        )}
      </div>

      {/* Lightbox */}
      <ImageViewer image={viewImage} onClose={() => setViewImage(null)} />
    </div>
  );
}
