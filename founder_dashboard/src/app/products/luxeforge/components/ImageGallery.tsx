'use client';

const FALLBACK_IMG =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">' +
    '<rect width="100" height="100" fill="#374151"/>' +
    '<text x="50" y="55" text-anchor="middle" fill="#9CA3AF" font-size="12">No preview</text>' +
    '</svg>'
  );

interface GalleryImage {
  id: string;
  original_name: string;
  thumbnail_path: string;
  file_path: string;
  size: number;
  mime_type: string;
  created_at: string;
}

interface ImageGalleryProps {
  images: GalleryImage[];
  onDelete: (id: string) => void;
  onView: (image: GalleryImage) => void;
}

export default function ImageGallery({ images, onDelete, onView }: ImageGalleryProps) {
  if (images.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 text-sm">
        No images yet. Capture or upload your first image above.
      </div>
    );
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {images.map(img => (
        <div
          key={img.id}
          className="relative group rounded-xl overflow-hidden bg-gray-900 border border-gray-700"
        >
          {/* Thumbnail */}
          <button
            onClick={() => onView(img)}
            className="w-full aspect-square focus:outline-none"
            title="View full size"
          >
            <img
              src={`/api/luxeforge/images/file/${img.id}`}
              alt={img.original_name}
              className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
              onError={e => {
                (e.target as HTMLImageElement).src = FALLBACK_IMG;
              }}
            />
          </button>

          {/* Overlay with info and delete */}
          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-2 pointer-events-none group-hover:pointer-events-auto">
            <div className="flex justify-end">
              <button
                onClick={e => { e.stopPropagation(); onDelete(img.id); }}
                className="w-7 h-7 rounded-full bg-red-600 hover:bg-red-500 text-white text-xs flex items-center justify-center"
                title="Delete image"
              >
                ✕
              </button>
            </div>
            <div>
              <p className="text-xs text-white truncate" title={img.original_name}>{img.original_name}</p>
              <p className="text-xs text-gray-400">{formatSize(img.size)}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
