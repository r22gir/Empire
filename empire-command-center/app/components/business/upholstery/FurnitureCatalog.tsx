'use client';

import React, { useState, useCallback, useMemo } from 'react';
import {
  Sofa,
  ArmchairIcon,
  Square,
  RectangleHorizontal,
  CircleDot,
  ChevronLeft,
  CheckCircle2,
  Sparkles,
  Ruler,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FurnitureType {
  key: string;
  name: string;
  category: 'sofa' | 'chair' | 'ottoman' | 'bench' | 'other';
  measurementPoints: string[];
  fabricSections: string[];
}

export interface FurnitureMeasurements {
  furnitureType: string;
  measurements: Record<string, number>;
  cushionCount: number;
  notes: string;
}

export interface FurnitureCatalogProps {
  onSelect?: (type: FurnitureType) => void;
  onMeasurementsComplete?: (data: FurnitureMeasurements) => void;
  suggestedType?: string;
  compact?: boolean;
}

// ---------------------------------------------------------------------------
// Furniture data
// ---------------------------------------------------------------------------

const FURNITURE_TYPES: FurnitureType[] = [
  {
    key: 'lawson-sofa',
    name: 'Lawson Sofa',
    category: 'sofa',
    measurementPoints: [
      'Overall Width',
      'Overall Depth',
      'Overall Height',
      'Seat Height',
      'Seat Depth',
      'Arm Height',
      'Arm Width',
      'Back Height',
      'Cushion Count',
    ],
    fabricSections: [
      'Seat Cushions',
      'Back Cushions',
      'Inside Arms',
      'Outside Arms',
      'Inside Back',
      'Outside Back',
      'Arm Fronts',
      'Deck',
    ],
  },
  {
    key: 'english-roll-arm',
    name: 'English Roll Arm Sofa',
    category: 'sofa',
    measurementPoints: [
      'Overall Width',
      'Overall Depth',
      'Overall Height',
      'Seat Height',
      'Seat Depth',
      'Arm Height',
      'Arm Width',
      'Back Height',
      'Arm Roll Diameter',
      'Cushion Count',
    ],
    fabricSections: [
      'Seat Cushions',
      'Back Cushions',
      'Inside Arms',
      'Outside Arms',
      'Inside Back',
      'Outside Back',
      'Arm Fronts',
      'Deck',
    ],
  },
  {
    key: 'wingback-chair',
    name: 'Wingback Chair',
    category: 'chair',
    measurementPoints: [
      'Overall Width',
      'Overall Depth',
      'Overall Height',
      'Seat Width',
      'Seat Depth',
      'Arm Height',
      'Wing Width',
      'Wing Height',
    ],
    fabricSections: [
      'Seat',
      'Inside Back',
      'Outside Back',
      'Inside Wings (x2)',
      'Outside Wings (x2)',
      'Inside Arms (x2)',
      'Outside Arms (x2)',
      'Arm Fronts (x2)',
      'Cushion',
    ],
  },
  {
    key: 'club-chair',
    name: 'Club Chair',
    category: 'chair',
    measurementPoints: [
      'Overall Width',
      'Overall Depth',
      'Overall Height',
      'Seat Width',
      'Seat Depth',
      'Seat Height',
      'Arm Height',
      'Arm Width',
    ],
    fabricSections: [
      'Seat Cushion',
      'Inside Back',
      'Outside Back',
      'Inside Arms (x2)',
      'Outside Arms (x2)',
      'Arm Fronts (x2)',
      'Deck',
    ],
  },
  {
    key: 'parsons-dining-chair',
    name: 'Parsons Dining Chair',
    category: 'chair',
    measurementPoints: [
      'Overall Width',
      'Overall Depth',
      'Overall Height',
      'Seat Width',
      'Seat Depth',
      'Back Height Above Seat',
    ],
    fabricSections: ['Seat', 'Inside Back', 'Outside Back', 'Sides (x2)'],
  },
  {
    key: 'ottoman-square',
    name: 'Ottoman (Square)',
    category: 'ottoman',
    measurementPoints: ['Width', 'Depth', 'Height'],
    fabricSections: ['Top', 'Front Side', 'Back Side', 'Left Side', 'Right Side', 'Skirt (optional)', 'Tufting (optional)'],
  },
  {
    key: 'bench-flat',
    name: 'Bench (Flat)',
    category: 'bench',
    measurementPoints: ['Width', 'Depth', 'Height', 'Leg Style'],
    fabricSections: ['Top', 'Front Side', 'Back Side', 'Ends (x2)'],
  },
  {
    key: 'window-seat',
    name: 'Window Seat',
    category: 'bench',
    measurementPoints: ['Width', 'Depth', 'Height', 'Bay Angle'],
    fabricSections: ['Top Cushion', 'Front', 'Sides (x2)', 'Back (if freestanding)'],
  },
  {
    key: 'chaise-lounge',
    name: 'Chaise Lounge',
    category: 'other',
    measurementPoints: [
      'Overall Width',
      'Overall Depth',
      'Overall Height',
      'Arm Height',
      'Headrest Height',
      'Seat Depth',
    ],
    fabricSections: [
      'Seat',
      'Inside Back',
      'Outside Back',
      'Inside Arm',
      'Outside Arm',
      'Headrest',
      'Deck',
    ],
  },
  {
    key: 'barrel-chair',
    name: 'Barrel Chair',
    category: 'chair',
    measurementPoints: [
      'Overall Width (Diameter)',
      'Overall Depth',
      'Overall Height',
      'Seat Height',
      'Back Height',
    ],
    fabricSections: [
      'Seat Cushion',
      'Inside Back (curved)',
      'Outside Back (curved)',
      'Deck',
    ],
  },
];

// ---------------------------------------------------------------------------
// Category colours (light tints for fabric section fills)
// ---------------------------------------------------------------------------

const SECTION_TINTS = [
  'rgba(184,150,12,0.10)',
  'rgba(184,150,12,0.18)',
  'rgba(120,100,40,0.10)',
  'rgba(200,180,100,0.12)',
  'rgba(160,140,60,0.10)',
  'rgba(184,150,12,0.06)',
];

const CATEGORY_LABELS: Record<string, string> = {
  sofa: 'Sofa',
  chair: 'Chair',
  ottoman: 'Ottoman',
  bench: 'Bench',
  other: 'Specialty',
};

// ---------------------------------------------------------------------------
// SVG diagram functions — simple line drawings (front view, 200x150 viewBox)
// ---------------------------------------------------------------------------

function SvgLawsonSofa({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Outside back */}
      <rect x="20" y="20" width="160" height="60" rx="4" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Left arm */}
      <rect x="20" y="20" width="20" height="110" rx="3" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Right arm */}
      <rect x="160" y="20" width="20" height="110" rx="3" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Seat / deck */}
      <rect x="40" y="80" width="120" height="30" rx="2" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Back cushions */}
      <rect x="42" y="25" width="55" height="50" rx="6" fill={full ? SECTION_TINTS[3] : 'none'} stroke="#333" strokeWidth="1" />
      <rect x="102" y="25" width="55" height="50" rx="6" fill={full ? SECTION_TINTS[3] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Seat cushions */}
      <rect x="42" y="82" width="37" height="25" rx="4" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      <rect x="81" y="82" width="37" height="25" rx="4" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      <rect x="120" y="82" width="37" height="25" rx="4" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Legs */}
      <rect x="25" y="130" width="6" height="12" rx="1" fill="#333" />
      <rect x="169" y="130" width="6" height="12" rx="1" fill="#333" />
      {full && (
        <>
          <circle cx="10" cy="20" r="2" fill="#b8960c" />
          <circle cx="190" cy="20" r="2" fill="#b8960c" />
          <circle cx="10" cy="142" r="2" fill="#b8960c" />
          <circle cx="100" cy="80" r="2" fill="#b8960c" />
          <text x="3" y="85" fontSize="7" fill="#b8960c">H</text>
          <text x="90" y="148" fontSize="7" fill="#b8960c">W</text>
        </>
      )}
    </svg>
  );
}

function SvgEnglishRollArm({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Back */}
      <rect x="25" y="20" width="150" height="55" rx="6" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Left rolled arm */}
      <path d="M25,30 Q5,50 15,80 Q20,100 25,130" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      <ellipse cx="20" cy="80" rx="12" ry="20" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Right rolled arm */}
      <path d="M175,30 Q195,50 185,80 Q180,100 175,130" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      <ellipse cx="180" cy="80" rx="12" ry="20" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Seat */}
      <rect x="30" y="80" width="140" height="30" rx="3" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Seat cushions */}
      <rect x="33" y="83" width="65" height="24" rx="5" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      <rect x="102" y="83" width="65" height="24" rx="5" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Legs */}
      <rect x="30" y="130" width="5" height="12" rx="1" fill="#333" />
      <rect x="165" y="130" width="5" height="12" rx="1" fill="#333" />
      {full && (
        <>
          <circle cx="20" cy="60" r="2.5" fill="#b8960c" />
          <text x="2" y="63" fontSize="6" fill="#b8960c">Roll</text>
        </>
      )}
    </svg>
  );
}

function SvgWingbackChair({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* High back */}
      <path d="M55,10 Q100,5 145,10 L150,75 Q100,80 50,75 Z" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Left wing */}
      <path d="M55,10 Q20,20 15,50 Q18,70 50,75" fill={full ? SECTION_TINTS[3] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Right wing */}
      <path d="M145,10 Q180,20 185,50 Q182,70 150,75" fill={full ? SECTION_TINTS[3] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Arms */}
      <rect x="30" y="70" width="15" height="45" rx="3" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      <rect x="155" y="70" width="15" height="45" rx="3" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Seat */}
      <rect x="45" y="85" width="110" height="28" rx="4" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Cushion */}
      <rect x="48" y="88" width="104" height="22" rx="6" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Legs */}
      <rect x="45" y="115" width="5" height="14" rx="1" fill="#333" />
      <rect x="150" y="115" width="5" height="14" rx="1" fill="#333" />
      {full && (
        <>
          <circle cx="15" cy="50" r="2" fill="#b8960c" />
          <text x="1" y="45" fontSize="6" fill="#b8960c">Wing</text>
        </>
      )}
    </svg>
  );
}

function SvgClubChair({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Back */}
      <rect x="25" y="20" width="150" height="50" rx="8" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Left arm — wide & rolled */}
      <path d="M25,20 Q5,35 10,70 Q12,100 25,120" fill="none" stroke="#333" strokeWidth="1.5" />
      <rect x="10" y="50" width="25" height="60" rx="8" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Right arm */}
      <path d="M175,20 Q195,35 190,70 Q188,100 175,120" fill="none" stroke="#333" strokeWidth="1.5" />
      <rect x="165" y="50" width="25" height="60" rx="8" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Seat */}
      <rect x="35" y="75" width="130" height="35" rx="4" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Cushion */}
      <rect x="38" y="78" width="124" height="28" rx="6" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Short legs */}
      <rect x="30" y="120" width="8" height="10" rx="2" fill="#333" />
      <rect x="162" y="120" width="8" height="10" rx="2" fill="#333" />
    </svg>
  );
}

function SvgParsonsDiningChair({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Back — tall, straight */}
      <rect x="50" y="10" width="100" height="70" rx="3" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Seat */}
      <rect x="45" y="80" width="110" height="20" rx="3" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Front legs */}
      <rect x="48" y="100" width="6" height="30" rx="1" fill="#333" />
      <rect x="146" y="100" width="6" height="30" rx="1" fill="#333" />
      {/* Back legs (slightly angled) */}
      <line x1="52" y1="80" x2="48" y2="130" stroke="#333" strokeWidth="2" />
      <line x1="148" y1="80" x2="152" y2="130" stroke="#333" strokeWidth="2" />
      {/* Side panels */}
      {full && (
        <>
          <rect x="45" y="10" width="5" height="90" rx="1" fill={SECTION_TINTS[2]} stroke="#333" strokeWidth="0.5" />
          <rect x="150" y="10" width="5" height="90" rx="1" fill={SECTION_TINTS[2]} stroke="#333" strokeWidth="0.5" />
        </>
      )}
    </svg>
  );
}

function SvgOttomanSquare({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Top cushion */}
      <rect x="30" y="20" width="140" height="30" rx="6" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Front */}
      <rect x="30" y="50" width="140" height="60" rx="3" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Tufting lines */}
      <line x1="70" y1="55" x2="70" y2="105" stroke="#333" strokeWidth="0.5" strokeDasharray="3,3" />
      <line x1="100" y1="55" x2="100" y2="105" stroke="#333" strokeWidth="0.5" strokeDasharray="3,3" />
      <line x1="130" y1="55" x2="130" y2="105" stroke="#333" strokeWidth="0.5" strokeDasharray="3,3" />
      {/* Bottom trim / skirt */}
      <rect x="28" y="110" width="144" height="10" rx="2" fill={full ? SECTION_TINTS[5] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Feet */}
      <rect x="35" y="120" width="8" height="10" rx="2" fill="#333" />
      <rect x="157" y="120" width="8" height="10" rx="2" fill="#333" />
    </svg>
  );
}

function SvgBenchFlat({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Top pad */}
      <rect x="15" y="40" width="170" height="25" rx="4" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Front panel */}
      <rect x="15" y="65" width="170" height="25" rx="2" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Tufting dots on top */}
      {[40, 70, 100, 130, 160].map((cx) => (
        <circle key={cx} cx={cx} cy="52" r="2" fill="#333" opacity="0.4" />
      ))}
      {/* Legs */}
      <rect x="20" y="90" width="6" height="30" rx="1" fill="#333" />
      <rect x="90" y="90" width="6" height="30" rx="1" fill="#333" />
      <rect x="174" y="90" width="6" height="30" rx="1" fill="#333" />
    </svg>
  );
}

function SvgWindowSeat({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Back wall / built-in context */}
      <rect x="20" y="20" width="160" height="15" rx="2" fill="none" stroke="#333" strokeWidth="1" strokeDasharray="4,3" />
      {/* Side walls */}
      <rect x="20" y="20" width="15" height="90" rx="2" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      <rect x="165" y="20" width="15" height="90" rx="2" fill={full ? SECTION_TINTS[2] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Seat base */}
      <rect x="35" y="70" width="130" height="15" rx="2" fill="none" stroke="#333" strokeWidth="1" />
      {/* Cushion */}
      <rect x="37" y="55" width="126" height="18" rx="5" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Front panel */}
      <rect x="35" y="85" width="130" height="25" rx="2" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Feet */}
      <rect x="40" y="110" width="6" height="12" rx="1" fill="#333" />
      <rect x="154" y="110" width="6" height="12" rx="1" fill="#333" />
    </svg>
  );
}

function SvgChaiseLounge({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Raised headrest end (left) */}
      <path d="M20,25 Q25,15 40,15 L50,15 Q55,15 55,25 L55,80 L20,80 Z" fill={full ? SECTION_TINTS[3] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Back / arm along top */}
      <path d="M20,25 L20,80" stroke="#333" strokeWidth="1.5" />
      {/* Long seat */}
      <rect x="20" y="80" width="160" height="25" rx="3" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Seat cushion */}
      <rect x="55" y="82" width="122" height="20" rx="5" fill={full ? SECTION_TINTS[4] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Outside back */}
      <rect x="55" y="30" width="125" height="50" rx="4" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* No arm on right — open end */}
      {/* Legs */}
      <rect x="25" y="105" width="5" height="14" rx="1" fill="#333" />
      <rect x="95" y="105" width="5" height="14" rx="1" fill="#333" />
      <rect x="170" y="105" width="5" height="14" rx="1" fill="#333" />
    </svg>
  );
}

function SvgBarrelChair({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Curved back wrapping around */}
      <ellipse cx="100" cy="60" rx="75" ry="55" fill={full ? SECTION_TINTS[0] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Inner cutout — the "opening" of the barrel */}
      <ellipse cx="100" cy="55" rx="55" ry="38" fill={full ? SECTION_TINTS[5] : '#f5f3ef'} stroke="#333" strokeWidth="1" />
      {/* Inside back */}
      <path d="M50,40 Q100,15 150,40" fill={full ? SECTION_TINTS[3] : 'none'} stroke="#333" strokeWidth="1" />
      {/* Seat */}
      <ellipse cx="100" cy="80" rx="50" ry="15" fill={full ? SECTION_TINTS[1] : 'none'} stroke="#333" strokeWidth="1.5" />
      {/* Legs — pedestal style */}
      <rect x="85" y="110" width="30" height="8" rx="3" fill="#333" />
      <rect x="95" y="118" width="10" height="12" rx="2" fill="#333" />
    </svg>
  );
}

const SVG_MAP: Record<string, React.FC<{ full?: boolean }>> = {
  'lawson-sofa': SvgLawsonSofa,
  'english-roll-arm': SvgEnglishRollArm,
  'wingback-chair': SvgWingbackChair,
  'club-chair': SvgClubChair,
  'parsons-dining-chair': SvgParsonsDiningChair,
  'ottoman-square': SvgOttomanSquare,
  'bench-flat': SvgBenchFlat,
  'window-seat': SvgWindowSeat,
  'chaise-lounge': SvgChaiseLounge,
  'barrel-chair': SvgBarrelChair,
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function FurnitureCatalog({
  onSelect,
  onMeasurementsComplete,
  suggestedType,
  compact = false,
}: FurnitureCatalogProps) {
  const [selected, setSelected] = useState<FurnitureType | null>(null);
  const [measurements, setMeasurements] = useState<Record<string, string>>({});
  const [cushionCount, setCushionCount] = useState<number>(2);
  const [notes, setNotes] = useState('');

  // Derive whether all required fields are filled
  const allFilled = useMemo(() => {
    if (!selected) return false;
    return selected.measurementPoints.every((mp) => {
      if (mp === 'Cushion Count') return true; // handled separately
      if (mp === 'Leg Style' || mp === 'Bay Angle') return true; // optional / text
      const v = measurements[mp];
      return v !== undefined && v !== '' && !isNaN(Number(v));
    });
  }, [selected, measurements]);

  const handleSelect = useCallback(
    (ft: FurnitureType) => {
      setSelected(ft);
      setMeasurements({});
      setCushionCount(ft.key.includes('sofa') ? 3 : 1);
      setNotes('');
      onSelect?.(ft);
    },
    [onSelect],
  );

  const handleBack = useCallback(() => {
    setSelected(null);
    setMeasurements({});
    setNotes('');
  }, []);

  const handleComplete = useCallback(() => {
    if (!selected) return;
    const parsed: Record<string, number> = {};
    for (const [k, v] of Object.entries(measurements)) {
      const n = Number(v);
      if (!isNaN(n)) parsed[k] = n;
    }
    onMeasurementsComplete?.({
      furnitureType: selected.key,
      measurements: parsed,
      cushionCount,
      notes,
    });
  }, [selected, measurements, cushionCount, notes, onMeasurementsComplete]);

  // -----------------------------------------------------------------------
  // Detail / measurement view
  // -----------------------------------------------------------------------
  if (selected) {
    const SvgComponent = SVG_MAP[selected.key];
    return (
      <div
        style={{
          background: '#f5f3ef',
          borderRadius: 12,
          border: '1px solid #ece8e0',
          padding: compact ? 16 : 24,
          fontFamily: 'inherit',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <button
            onClick={handleBack}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: '#b8960c',
              fontWeight: 600,
              fontSize: 14,
              padding: 0,
              minHeight: 44,
            }}
          >
            <ChevronLeft size={18} />
            Back
          </button>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#333' }}>
            {selected.name}
          </h2>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: 'uppercase',
              background: '#b8960c',
              color: '#fff',
              padding: '2px 8px',
              borderRadius: 4,
            }}
          >
            {CATEGORY_LABELS[selected.category]}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: compact ? '1fr' : '1fr 1fr',
            gap: 24,
          }}
        >
          {/* Diagram */}
          <div
            style={{
              background: '#fff',
              borderRadius: 10,
              border: '1px solid #ece8e0',
              padding: 16,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <div style={{ width: '100%', maxWidth: 340 }}>
              {SvgComponent && <SvgComponent full />}
            </div>
            <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {selected.fabricSections.map((section) => (
                <span
                  key={section}
                  style={{
                    fontSize: 10,
                    background: 'rgba(184,150,12,0.12)',
                    border: '1px solid #ece8e0',
                    borderRadius: 4,
                    padding: '2px 6px',
                    color: '#666',
                  }}
                >
                  {section}
                </span>
              ))}
            </div>
            <p style={{ fontSize: 11, color: '#999', marginTop: 8 }}>
              Fabric sections shown above. All measurements in inches.
            </p>
          </div>

          {/* Measurement inputs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                marginBottom: 4,
              }}
            >
              <Ruler size={16} color="#b8960c" />
              <span style={{ fontWeight: 600, fontSize: 14, color: '#333' }}>
                Measurements
              </span>
            </div>

            {selected.measurementPoints.map((mp) => {
              if (mp === 'Cushion Count') {
                return (
                  <div key={mp} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <label
                      style={{
                        flex: 1,
                        fontSize: 13,
                        color: '#555',
                        minWidth: 120,
                      }}
                    >
                      {mp}
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={cushionCount}
                      onChange={(e) => setCushionCount(Number(e.target.value) || 1)}
                      style={{
                        width: 70,
                        minHeight: 44,
                        borderRadius: 6,
                        border: '1px solid #ece8e0',
                        padding: '0 10px',
                        fontSize: 14,
                        textAlign: 'center',
                        outline: 'none',
                      }}
                    />
                  </div>
                );
              }
              const isText = mp === 'Leg Style' || mp === 'Bay Angle';
              return (
                <div key={mp} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <label
                    style={{
                      flex: 1,
                      fontSize: 13,
                      color: '#555',
                      minWidth: 120,
                    }}
                  >
                    {mp}
                  </label>
                  <input
                    type={isText ? 'text' : 'number'}
                    placeholder={isText ? 'e.g. tapered' : '"'}
                    value={measurements[mp] ?? ''}
                    onChange={(e) =>
                      setMeasurements((prev) => ({ ...prev, [mp]: e.target.value }))
                    }
                    style={{
                      width: 100,
                      minHeight: 44,
                      borderRadius: 6,
                      border: '1px solid #ece8e0',
                      padding: '0 10px',
                      fontSize: 14,
                      textAlign: isText ? 'left' : 'center',
                      outline: 'none',
                    }}
                  />
                </div>
              );
            })}

            {/* Notes */}
            <div style={{ marginTop: 4 }}>
              <label style={{ fontSize: 13, color: '#555' }}>Notes</label>
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Skirt style, tufting, welt details..."
                style={{
                  width: '100%',
                  marginTop: 4,
                  borderRadius: 6,
                  border: '1px solid #ece8e0',
                  padding: 10,
                  fontSize: 13,
                  resize: 'vertical',
                  outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            {/* Complete button */}
            <button
              onClick={handleComplete}
              disabled={!allFilled}
              style={{
                marginTop: 8,
                minHeight: 48,
                borderRadius: 8,
                border: 'none',
                background: allFilled ? '#b8960c' : '#ddd',
                color: allFilled ? '#fff' : '#999',
                fontWeight: 700,
                fontSize: 15,
                cursor: allFilled ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                transition: 'background 0.2s',
              }}
            >
              <CheckCircle2 size={18} />
              Complete Measurements
            </button>
          </div>
        </div>
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Grid view
  // -----------------------------------------------------------------------
  return (
    <div
      style={{
        background: '#f5f3ef',
        borderRadius: 12,
        border: '1px solid #ece8e0',
        padding: compact ? 16 : 24,
        fontFamily: 'inherit',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 16,
        }}
      >
        <Sofa size={20} color="#b8960c" />
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#333' }}>
          Furniture Catalog
        </h2>
      </div>

      {suggestedType && (
        <p style={{ fontSize: 13, color: '#b8960c', margin: '0 0 12px', fontWeight: 500 }}>
          <Sparkles size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />
          AI has suggested a furniture type below.
        </p>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: compact
            ? 'repeat(auto-fill, minmax(140px, 1fr))'
            : 'repeat(auto-fill, minmax(180px, 1fr))',
          gap: compact ? 10 : 14,
        }}
      >
        {FURNITURE_TYPES.map((ft) => {
          const isSuggested = suggestedType === ft.key;
          const SvgComponent = SVG_MAP[ft.key];
          return (
            <button
              key={ft.key}
              onClick={() => handleSelect(ft)}
              style={{
                position: 'relative',
                background: '#fff',
                borderRadius: 10,
                border: isSuggested ? '2px solid #b8960c' : '1px solid #ece8e0',
                padding: compact ? 10 : 14,
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                minHeight: compact ? 120 : 160,
                transition: 'box-shadow 0.15s, border-color 0.15s',
                boxShadow: isSuggested
                  ? '0 0 0 3px rgba(184,150,12,0.18)'
                  : '0 1px 3px rgba(0,0,0,0.04)',
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = '#b8960c';
                (e.currentTarget as HTMLButtonElement).style.boxShadow =
                  '0 2px 8px rgba(184,150,12,0.15)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = isSuggested
                  ? '#b8960c'
                  : '#ece8e0';
                (e.currentTarget as HTMLButtonElement).style.boxShadow = isSuggested
                  ? '0 0 0 3px rgba(184,150,12,0.18)'
                  : '0 1px 3px rgba(0,0,0,0.04)';
              }}
            >
              {/* AI Suggested badge */}
              {isSuggested && (
                <span
                  style={{
                    position: 'absolute',
                    top: 6,
                    right: 6,
                    fontSize: 9,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    background: '#b8960c',
                    color: '#fff',
                    padding: '2px 6px',
                    borderRadius: 4,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 3,
                  }}
                >
                  <Sparkles size={10} />
                  AI Suggested
                </span>
              )}

              {/* SVG thumbnail */}
              <div
                style={{
                  width: compact ? 100 : 130,
                  height: compact ? 75 : 95,
                  flexShrink: 0,
                }}
              >
                {SvgComponent && <SvgComponent />}
              </div>

              {/* Name */}
              <span
                style={{
                  fontSize: compact ? 12 : 13,
                  fontWeight: 600,
                  color: '#333',
                  textAlign: 'center',
                  lineHeight: 1.2,
                }}
              >
                {ft.name}
              </span>

              {/* Category badge */}
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  color: '#b8960c',
                  background: 'rgba(184,150,12,0.08)',
                  padding: '2px 8px',
                  borderRadius: 4,
                }}
              >
                {CATEGORY_LABELS[ft.category]}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
