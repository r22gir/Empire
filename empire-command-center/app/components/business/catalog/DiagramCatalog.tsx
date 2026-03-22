'use client';

import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { DIAGRAM_MAP, CATALOG_CATEGORIES } from './diagramMapper';

// Theme constants
const GOLD = '#b8960c';
const GOLD_BG = '#fdf8eb';
const BORDER = '#ece8e0';
const PAGE_BG = '#faf9f7';

const CATEGORY_COLORS: Record<string, string> = {
  upholstery: '#6b8e6b',
  drapery: '#7b6b9e',
  wall_panel: '#8e7b6b',
  cushion: '#6b7b8e',
};

interface DiagramCatalogProps {
  onSelect: (diagramKey: string) => void;
  onQuickAdd: (diagramKey: string) => void;
  selectedKey?: string;
  filterCategory?: string;
}

export default function DiagramCatalog({
  onSelect,
  onQuickAdd,
  selectedKey,
  filterCategory,
}: DiagramCatalogProps) {
  const [activeCategory, setActiveCategory] = useState(filterCategory || 'all');
  const [searchQuery, setSearchQuery] = useState('');
  const [focusIndex, setFocusIndex] = useState(-1);
  const gridRef = useRef<HTMLDivElement>(null);

  const entries = useMemo(() => Object.entries(DIAGRAM_MAP), []);

  const filtered = useMemo(() => {
    return entries.filter(([key, item]) => {
      const matchCategory =
        activeCategory === 'all' ||
        item.category === activeCategory ||
        (activeCategory === 'wall_panel' && key.startsWith('wall_panel')) ||
        (activeCategory === 'cushion' && key.startsWith('cushion'));
      const matchSearch =
        !searchQuery ||
        item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        key.toLowerCase().includes(searchQuery.toLowerCase());
      return matchCategory && matchSearch;
    });
  }, [entries, activeCategory, searchQuery]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      const cols = 4;
      let next = focusIndex;

      switch (e.key) {
        case 'ArrowRight':
          next = Math.min(focusIndex + 1, filtered.length - 1);
          break;
        case 'ArrowLeft':
          next = Math.max(focusIndex - 1, 0);
          break;
        case 'ArrowDown':
          next = Math.min(focusIndex + cols, filtered.length - 1);
          break;
        case 'ArrowUp':
          next = Math.max(focusIndex - cols, 0);
          break;
        case 'Enter':
        case ' ':
          if (focusIndex >= 0 && focusIndex < filtered.length) {
            e.preventDefault();
            onSelect(filtered[focusIndex][0]);
          }
          return;
        default:
          return;
      }

      e.preventDefault();
      setFocusIndex(next);
    },
    [focusIndex, filtered, onSelect]
  );

  useEffect(() => {
    if (focusIndex >= 0 && gridRef.current) {
      const cards = gridRef.current.querySelectorAll('[data-card]');
      if (cards[focusIndex]) {
        (cards[focusIndex] as HTMLElement).focus();
      }
    }
  }, [focusIndex]);

  useEffect(() => {
    if (filterCategory) setActiveCategory(filterCategory);
  }, [filterCategory]);

  return (
    <div style={{ background: PAGE_BG, borderRadius: 12, padding: 24 }}>
      {/* Search Bar */}
      <div style={{ marginBottom: 16 }}>
        <input
          type="text"
          placeholder="Search diagrams..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setFocusIndex(-1);
          }}
          style={{
            width: '100%',
            padding: '10px 16px',
            fontSize: 14,
            border: `1px solid ${BORDER}`,
            borderRadius: 8,
            background: '#fff',
            outline: 'none',
            boxSizing: 'border-box',
          }}
          onFocus={(e) => (e.target.style.borderColor = GOLD)}
          onBlur={(e) => (e.target.style.borderColor = BORDER)}
        />
      </div>

      {/* Category Filter Pills */}
      <div
        style={{
          display: 'flex',
          gap: 8,
          marginBottom: 20,
          flexWrap: 'wrap',
        }}
      >
        {CATALOG_CATEGORIES.map((cat) => {
          const isActive = activeCategory === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => {
                setActiveCategory(cat.id);
                setFocusIndex(-1);
              }}
              style={{
                padding: '6px 16px',
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                border: `1px solid ${isActive ? GOLD : BORDER}`,
                borderRadius: 20,
                background: isActive ? GOLD_BG : '#fff',
                color: isActive ? GOLD : '#555',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* Results Count */}
      <div
        style={{
          fontSize: 13,
          color: '#888',
          marginBottom: 12,
        }}
      >
        {filtered.length} diagram{filtered.length !== 1 ? 's' : ''} found
      </div>

      {/* Diagram Grid */}
      <div
        ref={gridRef}
        onKeyDown={handleKeyDown}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: 16,
        }}
      >
        {filtered.map(([key, item], idx) => {
          const isSelected = selectedKey === key;
          const isFocused = focusIndex === idx;
          const badgeColor = CATEGORY_COLORS[item.category] || '#888';

          return (
            <div
              key={key}
              data-card
              tabIndex={0}
              onClick={() => {
                setFocusIndex(idx);
                onSelect(key);
              }}
              onFocus={() => setFocusIndex(idx)}
              style={{
                position: 'relative',
                border: `2px solid ${isSelected ? GOLD : isFocused ? '#ccc' : BORDER}`,
                borderRadius: 10,
                background: isSelected ? GOLD_BG : '#fff',
                padding: 12,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                outline: isFocused ? `2px solid ${GOLD}` : 'none',
                outlineOffset: 2,
                boxShadow: isSelected
                  ? `0 0 0 1px ${GOLD}`
                  : '0 1px 3px rgba(0,0,0,0.04)',
              }}
              onMouseEnter={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.borderColor = '#ccc';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
                }
                const btn = e.currentTarget.querySelector(
                  '[data-quick-add]'
                ) as HTMLElement;
                if (btn) btn.style.opacity = '1';
              }}
              onMouseLeave={(e) => {
                if (!isSelected) {
                  e.currentTarget.style.borderColor = BORDER;
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
                }
                const btn = e.currentTarget.querySelector(
                  '[data-quick-add]'
                ) as HTMLElement;
                if (btn) btn.style.opacity = '0';
              }}
            >
              {/* Category Badge */}
              <span
                style={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  fontSize: 10,
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: 10,
                  background: badgeColor,
                  color: '#fff',
                  textTransform: 'uppercase',
                  letterSpacing: 0.5,
                }}
              >
                {item.category}
              </span>

              {/* SVG Thumbnail */}
              <div
                style={{
                  width: '100%',
                  height: 120,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: 8,
                  marginTop: 4,
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={item.svg}
                  alt={item.label}
                  style={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                    opacity: 0.85,
                  }}
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent && !parent.querySelector('[data-placeholder]')) {
                      const placeholder = document.createElement('div');
                      placeholder.setAttribute('data-placeholder', 'true');
                      placeholder.style.cssText =
                        'width:80px;height:80px;border:2px dashed #ddd;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#ccc;font-size:11px;text-align:center;padding:8px;';
                      placeholder.textContent = 'No preview';
                      parent.appendChild(placeholder);
                    }
                  }}
                />
              </div>

              {/* Label */}
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: '#333',
                  textAlign: 'center',
                  lineHeight: 1.3,
                }}
              >
                {item.label}
              </div>

              {/* Quick Add Button */}
              <button
                data-quick-add
                onClick={(e) => {
                  e.stopPropagation();
                  onQuickAdd(key);
                }}
                style={{
                  position: 'absolute',
                  bottom: 8,
                  right: 8,
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  border: 'none',
                  background: GOLD,
                  color: '#fff',
                  fontSize: 18,
                  fontWeight: 700,
                  lineHeight: '28px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  opacity: 0,
                  transition: 'opacity 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 0,
                }}
                title="Quick Add"
              >
                +
              </button>
            </div>
          );
        })}
      </div>

      {/* Empty State */}
      {filtered.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '40px 20px',
            color: '#999',
            fontSize: 14,
          }}
        >
          No diagrams match your search. Try a different term or category.
        </div>
      )}
    </div>
  );
}
