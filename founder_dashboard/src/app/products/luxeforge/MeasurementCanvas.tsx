'use client';

import { useRef, useState, useEffect, useCallback } from 'react';

export interface Point {
  x: number;
  y: number;
}

export interface MeasureLine {
  id: string;
  label: string;
  start: Point;
  end: Point;
  pixels: number;
  realLength?: number;
  color: string;
}

interface MeasurementCanvasProps {
  imageUrl: string;
  lines: MeasureLine[];
  onLinesChange: (lines: MeasureLine[]) => void;
  referenceLineId?: string; // ID of the calibration/reference line
  unit: 'inches' | 'cm';
}

const COLORS = ['#f59e0b', '#3b82f6', '#10b981', '#ef4444', '#8b5cf6', '#ec4899'];
const HANDLE_RADIUS = 7;

function dist(a: Point, b: Point) {
  return Math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2);
}

export default function MeasurementCanvas({
  imageUrl,
  lines,
  onLinesChange,
  referenceLineId,
  unit,
}: MeasurementCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [drawing, setDrawing] = useState(false);
  const [currentStart, setCurrentStart] = useState<Point | null>(null);
  const [currentEnd, setCurrentEnd] = useState<Point | null>(null);
  const [dragging, setDragging] = useState<{ id: string; handle: 'start' | 'end' } | null>(null);
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 });

  // Load image dimensions
  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      imgRef.current = img;
      setImgSize({ w: img.naturalWidth, h: img.naturalHeight });
    };
    img.src = imageUrl;
  }, [imageUrl]);

  // Redraw canvas whenever lines or image change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !imgRef.current) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw all committed lines
    for (const line of lines) {
      drawLine(ctx, line, referenceLineId === line.id, unit);
    }

    // Draw the in-progress line
    if (drawing && currentStart && currentEnd) {
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(currentStart.x, currentStart.y);
      ctx.lineTo(currentEnd.x, currentEnd.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [lines, drawing, currentStart, currentEnd, referenceLineId, unit, imgSize]);

  function drawLine(
    ctx: CanvasRenderingContext2D,
    line: MeasureLine,
    isReference: boolean,
    unit: string,
  ) {
    ctx.strokeStyle = isReference ? '#facc15' : line.color;
    ctx.lineWidth = 2;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(line.start.x, line.start.y);
    ctx.lineTo(line.end.x, line.end.y);
    ctx.stroke();

    // Endpoint handles
    for (const pt of [line.start, line.end]) {
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, HANDLE_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = isReference ? '#facc15' : line.color;
      ctx.fill();
    }

    // Label
    const mid: Point = { x: (line.start.x + line.end.x) / 2, y: (line.start.y + line.end.y) / 2 };
    const label =
      line.realLength !== undefined
        ? `${line.label ? line.label + ': ' : ''}${line.realLength} ${unit}`
        : `${line.label || 'Line'} (${Math.round(line.pixels)}px)`;

    ctx.font = 'bold 13px sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 3;
    ctx.strokeText(label, mid.x + 6, mid.y - 6);
    ctx.fillText(label, mid.x + 6, mid.y - 6);
  }

  function getCanvasPoint(e: React.MouseEvent): Point {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      const pt = getCanvasPoint(e);
      // Inline handle lookup to avoid stale-closure issues
      const handle = (() => {
        for (const line of lines) {
          if (dist(pt, line.start) <= HANDLE_RADIUS + 4) return { id: line.id, handle: 'start' as const };
          if (dist(pt, line.end) <= HANDLE_RADIUS + 4) return { id: line.id, handle: 'end' as const };
        }
        return null;
      })();
      if (handle) {
        setDragging(handle);
        return;
      }
      setDrawing(true);
      setCurrentStart(pt);
      setCurrentEnd(pt);
    },
    [lines],
  );

  const onMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const pt = getCanvasPoint(e);
      if (dragging) {
        const updated = lines.map((l) => {
          if (l.id !== dragging.id) return l;
          const updated = { ...l, [dragging.handle]: pt };
          updated.pixels = dist(updated.start, updated.end);
          return updated;
        });
        onLinesChange(updated);
        return;
      }
      if (drawing) {
        setCurrentEnd(pt);
      }
    },
    [dragging, drawing, lines, onLinesChange],
  );

  const onMouseUp = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) {
        setDragging(null);
        return;
      }
      if (drawing && currentStart && currentEnd) {
        setDrawing(false);
        const pixels = dist(currentStart, currentEnd);
        if (pixels > 5) {
          const colorIndex = lines.length % COLORS.length;
          const newLine: MeasureLine = {
            id: crypto.randomUUID(),
            label: `Line ${lines.length + 1}`,
            start: currentStart,
            end: currentEnd,
            pixels,
            color: COLORS[colorIndex],
          };
          onLinesChange([...lines, newLine]);
        }
        setCurrentStart(null);
        setCurrentEnd(null);
      }
    },
    [dragging, drawing, currentStart, currentEnd, lines, onLinesChange],
  );

  return (
    <div ref={containerRef} className="relative w-full select-none">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={imageUrl}
        alt="Measurement target"
        className="w-full rounded-lg"
        draggable={false}
      />
      <canvas
        ref={canvasRef}
        width={imgSize.w || 800}
        height={imgSize.h || 600}
        className="absolute inset-0 w-full h-full rounded-lg cursor-crosshair"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={() => {
          setDrawing(false);
          setCurrentStart(null);
          setCurrentEnd(null);
          setDragging(null);
        }}
      />
    </div>
  );
}
