'use client';

import { useEffect, useCallback } from 'react';

interface ViewerImage {
  id: string;
  original_name: string;
  file_path: string;
}

interface ImageViewerProps {
  image: ViewerImage | null;
  onClose: () => void;
}

export default function ImageViewer({ image, onClose }: ImageViewerProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  if (!image) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative max-w-4xl w-full mx-4"
        onClick={e => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 text-white text-2xl hover:text-gray-300"
          aria-label="Close"
        >
          ✕
        </button>

        <img
          src={`/api/luxeforge/images/file/${image.id}`}
          alt={image.original_name}
          className="w-full max-h-[80vh] object-contain rounded-xl"
        />

        <p className="mt-2 text-center text-gray-400 text-sm">{image.original_name}</p>
      </div>
    </div>
  );
}
