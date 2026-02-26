'use client';
import { useState, useCallback } from 'react';
import { DeskId, DESK_PROMPTS } from '@/lib/deskData';

export function useDesk() {
  const [activeDesk, setActiveDesk] = useState<DeskId | null>(null);

  const openDesk = useCallback((id: DeskId) => {
    setActiveDesk(id);
  }, []);

  const closeDesk = useCallback(() => {
    setActiveDesk(null);
  }, []);

  const deskPrompt = activeDesk ? DESK_PROMPTS[activeDesk] || null : null;

  return {
    activeDesk,
    deskPrompt,
    openDesk,
    closeDesk,
  };
}
