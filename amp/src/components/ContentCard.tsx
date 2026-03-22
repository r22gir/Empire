'use client';

import { Leaf, BookOpen, Sparkles, Zap, Play, Crown } from 'lucide-react';
import { PILLAR_CONFIG, type Pillar } from '@/lib/data';

interface ContentItem {
  id: string;
  type: string;
  title: string;
  description: string;
  duration_seconds?: number;
  pillar?: string;
  premium?: boolean;
  category?: string;
}

interface ContentCardProps {
  item: ContentItem;
  onPlay?: (item: ContentItem) => void;
  compact?: boolean;
}

const TYPE_ICONS: Record<string, { icon: typeof Leaf; label: string }> = {
  meditation: { icon: Leaf, label: 'Meditaci\u00f3n' },
  lesson: { icon: BookOpen, label: 'Lecci\u00f3n' },
  affirmation: { icon: Sparkles, label: 'Afirmaci\u00f3n' },
  exercise: { icon: Zap, label: 'Ejercicio' },
};

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  if (m < 1) return `${seconds}s`;
  return `${m} min`;
}

export default function ContentCard({ item, onPlay, compact = false }: ContentCardProps) {
  const pillarConfig = item.pillar && item.pillar in PILLAR_CONFIG
    ? PILLAR_CONFIG[item.pillar as Pillar]
    : null;
  const pillarColor = pillarConfig?.color ?? '#D4A030';

  const typeInfo = TYPE_ICONS[item.type] ?? { icon: Sparkles, label: item.type };
  const TypeIcon = typeInfo.icon;

  if (compact) {
    return (
      <button
        onClick={() => onPlay?.(item)}
        className="group w-full flex items-center gap-3 p-3 rounded-xl bg-white border border-transparent hover:border-gold-light/60 hover:shadow-sm transition-all text-left"
      >
        {/* Pillar stripe */}
        <div
          className="flex-shrink-0 w-1 h-10 rounded-full"
          style={{ backgroundColor: pillarColor }}
        />

        {/* Type icon */}
        <div
          className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${pillarColor}15` }}
        >
          <TypeIcon size={14} style={{ color: pillarColor }} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-[#2D2A26] truncate group-hover:text-gold-dark transition-colors">
            {item.title}
          </h4>
          <div className="flex items-center gap-2 mt-0.5">
            {item.duration_seconds != null && (
              <span className="text-xs text-[#9B9590]">{formatDuration(item.duration_seconds)}</span>
            )}
            {item.premium && (
              <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-gold-dark">
                <Crown size={10} /> PRO
              </span>
            )}
          </div>
        </div>

        {/* Play indicator */}
        <Play
          size={14}
          className="flex-shrink-0 text-[#9B9590] group-hover:text-gold-dark transition-colors"
        />
      </button>
    );
  }

  return (
    <div className="group relative bg-white rounded-2xl border border-gold-light/30 hover:border-gold-light/70 shadow-sm hover:shadow-md transition-all overflow-hidden">
      {/* Pillar left stripe */}
      <div
        className="absolute top-0 left-0 w-1 h-full rounded-l-2xl"
        style={{ backgroundColor: pillarColor }}
      />

      <div className="p-5 pl-5">
        {/* Header row */}
        <div className="flex items-start gap-3 mb-3">
          {/* Type icon */}
          <div
            className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ backgroundColor: `${pillarColor}15` }}
          >
            <TypeIcon size={18} style={{ color: pillarColor }} />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#9B9590]">
                {typeInfo.label}
              </span>
              {item.premium && (
                <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-gold/10 text-[10px] font-bold text-gold-dark">
                  <Crown size={10} /> Premium
                </span>
              )}
              {item.category && (
                <span className="px-1.5 py-0.5 rounded-full bg-sand text-[10px] font-semibold text-earth">
                  {item.category}
                </span>
              )}
            </div>
            <h3 className="text-base font-bold text-[#2D2A26] mt-1 leading-snug group-hover:text-gold-dark transition-colors">
              {item.title}
            </h3>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-[#5C5650] leading-relaxed line-clamp-2 mb-4">
          {item.description}
        </p>

        {/* Footer row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {item.duration_seconds != null && (
              <span className="text-xs font-semibold text-[#9B9590]">
                {formatDuration(item.duration_seconds)}
              </span>
            )}
            {pillarConfig && (
              <span
                className="inline-flex items-center gap-1 text-xs font-semibold"
                style={{ color: pillarColor }}
              >
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ backgroundColor: pillarColor }}
                />
                {pillarConfig.label}
              </span>
            )}
          </div>

          {onPlay && (
            <button
              onClick={() => onPlay(item)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white shadow-sm active:scale-95 transition-all"
              style={{
                background: `linear-gradient(135deg, ${pillarColor}, #D4A030)`,
              }}
            >
              <Play size={13} className="ml-0.5" />
              {item.type === 'meditation' || item.type === 'exercise' ? 'Iniciar' : 'Abrir'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
