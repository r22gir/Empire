'use client';
import { Quote } from 'lucide-react';
import type { QuoteData } from './ContentAnalyzer';

interface Props {
  quotes: QuoteData[];
}

export default function QuoteCallout({ quotes }: Props) {
  if (quotes.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 my-2">
      {quotes.map((q, i) => (
        <div
          key={i}
          className="rounded-xl p-4 relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, rgba(212,175,55,0.05) 0%, rgba(139,92,246,0.05) 100%)',
            border: '1px solid var(--gold-border)',
            borderLeft: '3px solid var(--gold)',
          }}
        >
          <Quote
            className="absolute top-2 right-2 opacity-10"
            style={{ color: 'var(--gold)', width: 24, height: 24 }}
          />
          <p className="text-sm leading-relaxed pr-6" style={{ color: 'var(--text-primary)' }}>
            {q.text}
          </p>
          {q.source && (
            <p className="mt-2 text-[10px] font-medium" style={{ color: 'var(--text-muted)' }}>
              — {q.source}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
