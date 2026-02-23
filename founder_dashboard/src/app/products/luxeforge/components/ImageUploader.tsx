'use client';

import { useRef, useState, useCallback, DragEvent, ClipboardEvent } from 'react';

interface ImageUploaderProps {
  onUpload: (files: File[]) => void;
  uploading?: boolean;
  progress?: number;
}

export default function ImageUploader({ onUpload, uploading = false, progress = 0 }: ImageUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      const images = Array.from(files).filter(f => f.type.startsWith('image/'));
      if (images.length) onUpload(images);
    },
    [onUpload]
  );

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(true);
  };

  const onDragLeave = () => setDragging(false);

  const onPaste = useCallback(
    (e: ClipboardEvent<HTMLDivElement>) => {
      handleFiles(e.clipboardData.files);
    },
    [handleFiles]
  );

  return (
    <div
      onDrop={onDrop}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onPaste={onPaste}
      tabIndex={0}
      className={`w-full rounded-xl border-2 border-dashed p-8 flex flex-col items-center gap-4 cursor-pointer transition-colors outline-none
        ${dragging ? 'border-purple-500 bg-purple-900/20' : 'border-gray-700 bg-gray-900/30 hover:border-gray-500'}`}
      onClick={() => inputRef.current?.click()}
    >
      <span className="text-4xl select-none">🖼️</span>
      <p className="text-gray-300 text-sm text-center">
        Drag &amp; drop images here, paste from clipboard (Ctrl+V),<br />
        or <span className="text-purple-400 font-medium">click to browse</span>
      </p>

      {uploading && (
        <div className="w-full max-w-xs">
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-400 mt-1 text-center">{progress}%</p>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={e => handleFiles(e.target.files)}
        onClick={e => e.stopPropagation()}
      />
    </div>
  );
}
