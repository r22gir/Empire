'use client';
import { ReactNode, useRef, useEffect, useState } from 'react';
import type { CanvasMode } from './ContentAnalyzer';

interface Props {
  mode: CanvasMode;
  children: ReactNode;
}

export default function CanvasTransition({ mode, children }: Props) {
  const [visible, setVisible] = useState(true);
  const [displayMode, setDisplayMode] = useState(mode);
  const prevMode = useRef(mode);

  useEffect(() => {
    if (mode !== prevMode.current) {
      // Fade out
      setVisible(false);
      const timer = setTimeout(() => {
        setDisplayMode(mode);
        setVisible(true);
        prevMode.current = mode;
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [mode]);

  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(4px)',
        transition: 'opacity 150ms ease, transform 150ms ease',
        height: '100%',
      }}
    >
      {children}
    </div>
  );
}
