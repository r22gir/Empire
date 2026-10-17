'use client';
import { useEffect, useState } from 'react';
import { API } from '../lib/api';
import { EXAMPLE_MONEY, useExampleMode } from './exampleData';
import { figuresFromPayload, type MoneyFigures, type StudioMoneyPayload } from './studioMoney';

export function useStudioMoney(): { figures: MoneyFigures; loading: boolean; example: boolean } {
  const example = useExampleMode();
  const [payload, setPayload] = useState<StudioMoneyPayload | null>(null);
  const [loading, setLoading] = useState(!example);

  useEffect(() => {
    if (example) {
      setLoading(false);
      setPayload(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetch(`${API}/finance/studio-money`, { cache: 'no-store', signal: AbortSignal.timeout(12000) })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled) {
          setPayload(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPayload(null);
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [example]);

  return {
    example,
    loading: example ? false : loading,
    figures: figuresFromPayload(payload, {
      example,
      loading: example ? false : loading,
      exampleMoney: {
        toCollect: EXAMPLE_MONEY.toCollect,
        depositsDue: EXAMPLE_MONEY.depositsDue,
        paidMtd: EXAMPLE_MONEY.paidMtd,
      },
    }),
  };
}
