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
            background: '#fffdf7',
            border: '1px solid #c4b48a',
            borderLeft: '3px solid #7d5f17',
            color: '#16191c',
          }}
        >
          <Quote
            className="absolute top-2 right-2 opacity-10"
            style={{ color: '#7d5f17', width: 24, height: 24 }}
          />
          <p className="text-sm leading-relaxed pr-6" style={{ color: '#16191c' }}>
            {q.text}
          </p>
          {q.source && (
            <p className="mt-2 text-[10px] font-medium" style={{ color: '#4a453c' }}>
              — {q.source}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
