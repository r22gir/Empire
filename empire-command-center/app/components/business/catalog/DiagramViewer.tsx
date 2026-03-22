'use client';

import React, { useMemo } from 'react';
import { DIAGRAM_MAP } from './diagramMapper';

interface DiagramViewerProps {
  diagramKey: string;
  dimensions?: { width?: number; height?: number; depth?: number };
  showAnnotations?: boolean;
}

function formatDimension(inches: number): string {
  const feet = Math.floor(inches / 12);
  const remainingInches = inches % 12;
  const feetStr =
    feet > 0
      ? `${feet}'-${remainingInches}"`
      : `${remainingInches}"`;
  return `${inches}" / ${feetStr}`;
}

const ANNO_COLOR = '#999';
const ANNO_FONT = '12px -apple-system, BlinkMacSystemFont, sans-serif';
const ARROW_SIZE = 6;
const LINE_OFFSET = 24;
const LABEL_OFFSET = 14;

// SVG arrow marker definition
function ArrowMarkers() {
  return (
    <defs>
      <marker
        id="arrow-start"
        markerWidth={ARROW_SIZE}
        markerHeight={ARROW_SIZE}
        refX={ARROW_SIZE}
        refY={ARROW_SIZE / 2}
        orient="auto"
      >
        <polygon
          points={`${ARROW_SIZE},0 ${ARROW_SIZE},${ARROW_SIZE} 0,${ARROW_SIZE / 2}`}
          fill={ANNO_COLOR}
        />
      </marker>
      <marker
        id="arrow-end"
        markerWidth={ARROW_SIZE}
        markerHeight={ARROW_SIZE}
        refX={0}
        refY={ARROW_SIZE / 2}
        orient="auto"
      >
        <polygon
          points={`0,0 ${ARROW_SIZE},${ARROW_SIZE / 2} 0,${ARROW_SIZE}`}
          fill={ANNO_COLOR}
        />
      </marker>
    </defs>
  );
}

export default function DiagramViewer({
  diagramKey,
  dimensions,
  showAnnotations = false,
}: DiagramViewerProps) {
  const diagram = DIAGRAM_MAP[diagramKey];

  const hasAnnotations = showAnnotations && dimensions;
  const hasWidth = hasAnnotations && dimensions?.width;
  const hasHeight = hasAnnotations && dimensions?.height;
  const hasDepth = hasAnnotations && dimensions?.depth;

  // Diagram area dimensions
  const imgW = 320;
  const imgH = 240;

  // Total SVG size with annotation margins
  const padTop = hasWidth ? 40 : 0;
  const padRight = hasHeight ? 50 : 0;
  const padBottom = hasDepth ? 50 : 0;
  const padLeft = hasDepth ? 50 : 0;

  const svgW = padLeft + imgW + padRight;
  const svgH = padTop + imgH + padBottom;

  const dimLabels = useMemo(() => {
    if (!dimensions) return { w: '', h: '', d: '' };
    return {
      w: dimensions.width ? formatDimension(dimensions.width) : '',
      h: dimensions.height ? formatDimension(dimensions.height) : '',
      d: dimensions.depth ? formatDimension(dimensions.depth) : '',
    };
  }, [dimensions]);

  if (!diagram) {
    return (
      <div
        style={{
          padding: 40,
          textAlign: 'center',
          color: '#999',
          border: '1px dashed #ddd',
          borderRadius: 8,
        }}
      >
        Diagram not found: {diagramKey}
      </div>
    );
  }

  return (
    <div style={{ display: 'inline-block' }}>
      <svg
        width={svgW}
        height={svgH}
        viewBox={`0 0 ${svgW} ${svgH}`}
        style={{ overflow: 'visible' }}
      >
        <ArrowMarkers />

        {/* Diagram Image */}
        <image
          href={diagram.svg}
          x={padLeft}
          y={padTop}
          width={imgW}
          height={imgH}
          preserveAspectRatio="xMidYMid meet"
        />

        {/* Width annotation — top */}
        {hasWidth && (
          <g>
            {/* Extension lines */}
            <line x1={padLeft} y1={padTop - 4} x2={padLeft} y2={padTop - LINE_OFFSET}
              stroke={ANNO_COLOR} strokeWidth={0.75} />
            <line x1={padLeft + imgW} y1={padTop - 4} x2={padLeft + imgW} y2={padTop - LINE_OFFSET}
              stroke={ANNO_COLOR} strokeWidth={0.75} />
            {/* Dimension line */}
            <line
              x1={padLeft}
              y1={padTop - LABEL_OFFSET}
              x2={padLeft + imgW}
              y2={padTop - LABEL_OFFSET}
              stroke={ANNO_COLOR}
              strokeWidth={0.75}
              markerStart="url(#arrow-start)"
              markerEnd="url(#arrow-end)"
            />
            {/* Label */}
            <text
              x={padLeft + imgW / 2}
              y={padTop - LABEL_OFFSET - 5}
              textAnchor="middle"
              fill={ANNO_COLOR}
              style={{ font: ANNO_FONT }}
            >
              {dimLabels.w}
            </text>
          </g>
        )}

        {/* Height annotation — right */}
        {hasHeight && (
          <g>
            {/* Extension lines */}
            <line x1={padLeft + imgW + 4} y1={padTop} x2={padLeft + imgW + LINE_OFFSET} y2={padTop}
              stroke={ANNO_COLOR} strokeWidth={0.75} />
            <line x1={padLeft + imgW + 4} y1={padTop + imgH} x2={padLeft + imgW + LINE_OFFSET} y2={padTop + imgH}
              stroke={ANNO_COLOR} strokeWidth={0.75} />
            {/* Dimension line */}
            <line
              x1={padLeft + imgW + LABEL_OFFSET}
              y1={padTop}
              x2={padLeft + imgW + LABEL_OFFSET}
              y2={padTop + imgH}
              stroke={ANNO_COLOR}
              strokeWidth={0.75}
              markerStart="url(#arrow-start)"
              markerEnd="url(#arrow-end)"
            />
            {/* Label */}
            <text
              x={padLeft + imgW + LABEL_OFFSET + 6}
              y={padTop + imgH / 2}
              textAnchor="start"
              dominantBaseline="middle"
              fill={ANNO_COLOR}
              style={{ font: ANNO_FONT }}
              transform={`rotate(-90, ${padLeft + imgW + LABEL_OFFSET + 6}, ${padTop + imgH / 2})`}
            >
              {dimLabels.h}
            </text>
          </g>
        )}

        {/* Depth annotation — bottom-left at 45 degrees */}
        {hasDepth && (
          <g>
            {(() => {
              const startX = padLeft;
              const startY = padTop + imgH;
              const len = 70;
              const angle = Math.PI / 4; // 45 degrees
              const endX = startX - len * Math.cos(angle);
              const endY = startY + len * Math.sin(angle);
              const midX = (startX + endX) / 2;
              const midY = (startY + endY) / 2;
              return (
                <>
                  <line
                    x1={startX}
                    y1={startY}
                    x2={endX}
                    y2={endY}
                    stroke={ANNO_COLOR}
                    strokeWidth={0.75}
                    markerStart="url(#arrow-start)"
                    markerEnd="url(#arrow-end)"
                  />
                  <text
                    x={midX - 8}
                    y={midY + 4}
                    textAnchor="end"
                    fill={ANNO_COLOR}
                    style={{ font: ANNO_FONT }}
                    transform={`rotate(-45, ${midX - 8}, ${midY + 4})`}
                  >
                    {dimLabels.d}
                  </text>
                </>
              );
            })()}
          </g>
        )}
      </svg>

      {/* Label below */}
      <div
        style={{
          textAlign: 'center',
          marginTop: 8,
          fontSize: 14,
          fontWeight: 500,
          color: '#444',
        }}
      >
        {diagram.label}
      </div>
    </div>
  );
}
