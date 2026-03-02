'use client';
import { ReactNode } from 'react';

export type SplitLayout = '2-col' | '2-row' | '3-col' | 'main-side' | 'quad';

interface Props {
  layout: SplitLayout;
  children: ReactNode[];
}

function getGridStyle(layout: SplitLayout, childCount: number): React.CSSProperties {
  switch (layout) {
    case '2-col':
      return { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 };
    case '2-row':
      return { display: 'grid', gridTemplateRows: '1fr 1fr', gap: 8 };
    case '3-col':
      return { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 };
    case 'main-side':
      return { display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 8 };
    case 'quad':
      return { display: 'grid', gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr', gap: 8 };
    default:
      return { display: 'grid', gridTemplateColumns: `repeat(${Math.min(childCount, 3)}, 1fr)`, gap: 8 };
  }
}

function inferLayout(childCount: number): SplitLayout {
  if (childCount <= 2) return '2-col';
  if (childCount === 3) return 'main-side';
  return 'quad';
}

export default function SplitCanvas({ layout, children }: Props) {
  const validChildren = Array.isArray(children) ? children.filter(Boolean) : [children];
  if (validChildren.length === 0) return null;
  if (validChildren.length === 1) return <>{validChildren[0]}</>;

  const effectiveLayout = layout || inferLayout(validChildren.length);

  return (
    <div
      className="h-full"
      style={getGridStyle(effectiveLayout, validChildren.length)}
    >
      {validChildren.map((child, i) => (
        <div
          key={i}
          className="rounded-xl overflow-auto min-h-0"
          style={{
            background: 'var(--raised)',
            border: '1px solid var(--border)',
            padding: 8,
          }}
        >
          {child}
        </div>
      ))}
    </div>
  );
}
