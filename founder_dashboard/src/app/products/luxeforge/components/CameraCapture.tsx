'use client';

import { useRef, useState, useEffect, useCallback } from 'react';

interface CameraCaptureProps {
  onCapture: (dataUrl: string) => void;
}

export default function CameraCapture({ onCapture }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('user');
  const [active, setActive] = useState(false);

  const startCamera = useCallback(async (facing: 'user' | 'environment') => {
    // Stop any existing tracks before starting a new stream
    if (videoRef.current?.srcObject) {
      const existingStream = videoRef.current.srcObject as MediaStream;
      existingStream.getTracks().forEach(t => t.stop());
    }
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: facing },
        audio: false,
      });
      setStream(mediaStream);
      setError(null);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
      setActive(true);
    } catch {
      setError('Camera not available. Please allow camera access or check your device.');
      setActive(false);
    }
  }, []);

  useEffect(() => {
    return () => {
      stream?.getTracks().forEach(t => t.stop());
    };
  }, [stream]);

  const handleStart = () => startCamera(facingMode);

  const handleStop = () => {
    stream?.getTracks().forEach(t => t.stop());
    setStream(null);
    setActive(false);
  };

  const handleFlip = () => {
    const next = facingMode === 'user' ? 'environment' : 'user';
    setFacingMode(next);
    if (active) startCamera(next);
  };

  const handleCapture = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')?.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9);
    onCapture(dataUrl);
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-full max-w-md aspect-video bg-gray-900 rounded-xl overflow-hidden border border-gray-700 flex items-center justify-center">
        {active ? (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-gray-500 text-sm">Camera off</span>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/90 p-4 text-center text-red-400 text-sm">
            {error}
          </div>
        )}
      </div>

      <canvas ref={canvasRef} className="hidden" />

      <div className="flex gap-3">
        {!active ? (
          <button
            onClick={handleStart}
            className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-medium"
          >
            Start Camera
          </button>
        ) : (
          <>
            <button
              onClick={handleCapture}
              className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-medium"
            >
              📸 Capture
            </button>
            <button
              onClick={handleFlip}
              className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium"
              title="Switch front/back camera"
            >
              🔄 Flip
            </button>
            <button
              onClick={handleStop}
              className="px-4 py-2 rounded-lg bg-red-700 hover:bg-red-600 text-white text-sm font-medium"
            >
              Stop
            </button>
          </>
        )}
      </div>
    </div>
  );
}
