'use client';
import { useState } from 'react';
import { X, ZoomIn, ChevronLeft, ChevronRight } from 'lucide-react';
import type { ImageData } from './ContentAnalyzer';

interface Props {
  images: ImageData[];
  /** Render inline (within markdown flow) vs full canvas */
  inline?: boolean;
}

export default function ImageCanvas({ images, inline }: Props) {
  const [lightboxIdx, setLightboxIdx] = useState<number | null>(null);
  const [errors, setErrors] = useState<Set<number>>(new Set());

  if (images.length === 0) return null;

  const validImages = images.filter((_, i) => !errors.has(i));
  if (validImages.length === 0) return null;

  const handleError = (idx: number) => {
    setErrors(prev => new Set(prev).add(idx));
  };

  const isGallery = validImages.length > 1;

  return (
    <>
      <div className={`${inline ? 'my-2' : ''}`}>
        {isGallery ? (
          /* Gallery grid */
          <div
            className="grid gap-2 rounded-xl overflow-hidden"
            style={{
              gridTemplateColumns: validImages.length === 2 ? '1fr 1fr' :
                                   validImages.length === 3 ? '1fr 1fr 1fr' :
                                   'repeat(2, 1fr)',
            }}
          >
            {images.map((img, i) => {
              if (errors.has(i)) return null;
              return (
                <div
                  key={i}
                  className="relative group cursor-pointer overflow-hidden rounded-lg"
                  style={{ border: '1px solid var(--border)', aspectRatio: '4/3' }}
                  onClick={() => setLightboxIdx(i)}
                >
                  <img
                    src={img.src}
                    alt={img.alt || ''}
                    loading="lazy"
                    onError={() => handleError(i)}
                    className="w-full h-full object-cover transition group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition flex items-center justify-center">
                    <ZoomIn className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition" />
                  </div>
                  {img.alt && (
                    <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-black/60 text-[9px] text-white truncate">
                      {img.alt}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          /* Single image */
          <div
            className="inline-block rounded-xl overflow-hidden cursor-pointer group"
            style={{ border: '1px solid var(--border)', maxWidth: '100%' }}
            onClick={() => setLightboxIdx(0)}
          >
            <div className="relative">
              <img
                src={images[0].src}
                alt={images[0].alt || ''}
                loading="lazy"
                onError={() => handleError(0)}
                className="max-w-full rounded-xl transition group-hover:brightness-90"
                style={{ maxHeight: inline ? 300 : 400 }}
              />
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                <ZoomIn className="w-6 h-6 text-white drop-shadow-lg" />
              </div>
            </div>
            {images[0].alt && (
              <p className="px-2 py-1 text-[10px]" style={{ color: 'var(--text-muted)', background: 'var(--raised)' }}>
                {images[0].alt}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Lightbox */}
      {lightboxIdx !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90"
          onClick={() => setLightboxIdx(null)}
        >
          <button
            className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition"
            onClick={() => setLightboxIdx(null)}
          >
            <X className="w-5 h-5 text-white" />
          </button>

          {isGallery && (
            <>
              <button
                className="absolute left-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition"
                onClick={e => { e.stopPropagation(); setLightboxIdx(prev => prev !== null ? (prev - 1 + images.length) % images.length : 0); }}
              >
                <ChevronLeft className="w-5 h-5 text-white" />
              </button>
              <button
                className="absolute right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 transition"
                onClick={e => { e.stopPropagation(); setLightboxIdx(prev => prev !== null ? (prev + 1) % images.length : 0); }}
              >
                <ChevronRight className="w-5 h-5 text-white" />
              </button>
            </>
          )}

          <img
            src={images[lightboxIdx].src}
            alt={images[lightboxIdx].alt || ''}
            className="max-w-[90vw] max-h-[90vh] object-contain rounded-xl"
            onClick={e => e.stopPropagation()}
          />

          {images[lightboxIdx].alt && (
            <p className="absolute bottom-6 text-sm text-white/80 bg-black/50 px-3 py-1 rounded-lg">
              {images[lightboxIdx].alt}
            </p>
          )}

          {isGallery && (
            <div className="absolute bottom-4 flex gap-1.5">
              {images.map((_, i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full transition cursor-pointer"
                  style={{ background: i === lightboxIdx ? 'var(--gold)' : 'rgba(255,255,255,0.3)' }}
                  onClick={e => { e.stopPropagation(); setLightboxIdx(i); }}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
