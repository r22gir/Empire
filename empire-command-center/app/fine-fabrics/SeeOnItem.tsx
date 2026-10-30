'use client';

import { useMemo, useRef, useState } from 'react';
import { swatchSrc } from './api';
import {
  MOCKUP_ITEMS,
  SHOP_THIS_LOOK,
  TEMPLATES,
  VIEW,
  polygonToPath,
  quoteHref,
  sampleHref,
  templateFor,
  tileSizePx,
  type MockupItemId,
  type Point,
} from './seeOnItem';
import type { FabricProduct } from './types';

type Mode = 'templates' | 'upload';

export default function SeeOnItem({ product }: { product: FabricProduct }) {
  const [item, setItem] = useState<MockupItemId>('pillow');
  const [mode, setMode] = useState<Mode>('templates');
  const [photo, setPhoto] = useState<string | null>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [closed, setClosed] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const fabric = swatchSrc(product);
  const tile = tileSizePx(product.width, product.repeat);
  const patternId = `ff-swatch-${product.id}`;
  const template = templateFor(item);
  const clipPath = useMemo(() => (closed ? polygonToPath(points) : ''), [closed, points]);

  function onSvgClick(event: React.MouseEvent<SVGSVGElement>) {
    if (mode !== 'upload' || !photo || closed) return;
    const svg = event.currentTarget;
    const box = svg.getBoundingClientRect();
    const x = ((event.clientX - box.left) / box.width) * VIEW.w;
    const y = ((event.clientY - box.top) / box.height) * VIEW.h;
    setPoints((cur) => [...cur, { x, y }]);
  }

  return (
    <section className="ff-see" id="see-it">
      <p className="ff-eyebrow">See it on your item</p>
      <h2>Quick mockups</h2>
      <p className="ff-note">
        The cloth is tiled onto a clean template, scaled by width and repeat when those
        are known. Upload a photo to mark the area — the image never leaves this browser.
      </p>
      <div className="ff-see-modes" role="tablist">
        <button type="button" className={mode === 'templates' ? 'is-on' : ''} onClick={() => setMode('templates')}>
          Templates
        </button>
        <button type="button" className={mode === 'upload' ? 'is-on' : ''} onClick={() => setMode('upload')}>
          Upload your photo
        </button>
      </div>
      {mode === 'templates' ? (
        <div className="ff-see-items" role="tablist" aria-label="Item templates">
          {MOCKUP_ITEMS.map((entry) => (
            <button
              key={entry.id}
              type="button"
              data-mockup={entry.id}
              className={item === entry.id ? 'is-on' : ''}
              onClick={() => setItem(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </div>
      ) : (
        <div className="ff-see-upload">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              const url = URL.createObjectURL(file);
              setPhoto(url);
              setPoints([]);
              setClosed(false);
            }}
          />
          <button className="ff-btn-ghost" type="button" onClick={() => fileRef.current?.click()}>
            Choose a room photo
          </button>
          <button
            className="ff-btn-ghost"
            type="button"
            disabled={points.length < 3}
            onClick={() => setClosed(true)}
          >
            Close area
          </button>
          <button
            className="ff-btn-ghost"
            type="button"
            onClick={() => {
              setPoints([]);
              setClosed(false);
            }}
          >
            Clear marks
          </button>
          <p className="ff-note">Tap the photo to mark a polygon. Client-side only — nothing is stored.</p>
        </div>
      )}
      <div className="ff-see-stage" data-item={mode === 'templates' ? item : 'upload'}>
        <svg
          viewBox={`0 0 ${VIEW.w} ${VIEW.h}`}
          role="img"
          aria-label={mode === 'templates' ? `${template.id} mockup` : 'Uploaded photo mockup'}
          onClick={onSvgClick}
        >
          <defs>
            <pattern id={patternId} patternUnits="userSpaceOnUse" width={tile} height={tile}>
              <image href={fabric} x="0" y="0" width={tile} height={tile} preserveAspectRatio="xMidYMid slice" />
            </pattern>
          </defs>
          {mode === 'upload' ? (
            <>
              {photo ? (
                <image href={photo} x="0" y="0" width={VIEW.w} height={VIEW.h} preserveAspectRatio="xMidYMid slice" />
              ) : (
                <rect x="0" y="0" width={VIEW.w} height={VIEW.h} fill="#efe6d6" />
              )}
              {closed && clipPath ? (
                <>
                  <path d={clipPath} fill={`url(#${patternId})`} />
                  <path d={clipPath} fill="rgba(20,18,16,0.18)" />
                </>
              ) : null}
              {points.map((p, i) => (
                <circle key={`${p.x}-${p.y}-${i}`} cx={p.x} cy={p.y} r="4" fill="#b8912f" />
              ))}
              {points.length > 1 && !closed ? (
                <polyline
                  points={points.map((p) => `${p.x},${p.y}`).join(' ')}
                  fill="none"
                  stroke="#b8912f"
                  strokeWidth="2"
                />
              ) : null}
            </>
          ) : (
            <>
              <rect x="0" y="0" width={VIEW.w} height={VIEW.h} fill="#f3eee4" />
              <path d={template.fill} fill={`url(#${patternId})`} />
              {template.shade.map((d, i) => (
                <path key={i} d={d} fill="rgba(20,18,16,0.16)" />
              ))}
              {template.outline.map((d, i) => (
                <path key={`o${i}`} d={d} fill="none" stroke="#20241f" strokeWidth="2.2" />
              ))}
              {(template.wood || []).map((d, i) => (
                <path key={`w${i}`} d={d} fill="#6b5344" />
              ))}
            </>
          )}
        </svg>
      </div>
      <div className="ff-actions">
        <a className="ff-btn" href={sampleHref(product.id)}>Order sample</a>
        <a className="ff-btn-ghost" href={quoteHref(product.id, item, product.empire_code)}>
          Get a quote for this item
        </a>
      </div>
      <div className="ff-look">
        <p className="ff-eyebrow">Shop this look</p>
        <p className="ff-note">Pillow SKUs will land here. The row is a placeholder.</p>
        <div className="ff-look-row">
          {SHOP_THIS_LOOK.map((card) => (
            <div key={card.id} className="ff-look-card" aria-disabled="true">
              <div className="ff-look-swatch" style={{ backgroundImage: `url(${fabric})` }} />
              <strong>{card.label}</strong>
              <span className="ff-note">{card.note}</span>
            </div>
          ))}
        </div>
      </div>
      <span hidden>{TEMPLATES.length}</span>
    </section>
  );
}
