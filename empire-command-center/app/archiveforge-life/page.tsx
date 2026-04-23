import type { Metadata } from 'next';
import ArchiveForgePage from '../components/screens/ArchiveForgePage';

export const metadata: Metadata = {
  title: 'ArchiveForge LIFE Intake',
  description: 'Direct LIFE magazine intake, cover matching, photo upload, review, and MarketForge publishing.',
  openGraph: {
    title: 'ArchiveForge LIFE Intake',
    description: 'Find the matching LIFE issue, upload item photos, and publish through ArchiveForge.',
    type: 'website',
    url: 'https://studio.empirebox.store/archiveforge-life',
  },
};

const steps = [
  'Find matching LIFE issue',
  'Select cover reference',
  'Upload item photos',
  'Enter condition and details',
  'Review and publish',
];

export default function ArchiveForgeLifePublicPage() {
  return (
    <main style={page}>
      <style>{`
        @media (max-width: 820px) {
          [data-af-shell] {
            display: flex !important;
            flex-direction: column !important;
          }
          [data-af-assistant] {
            padding: 16px !important;
            gap: 12px !important;
            border-right: 0 !important;
            border-bottom: 1px solid #1f2937 !important;
          }
          [data-af-assistant] h1 {
            font-size: 20px !important;
          }
          [data-af-guide] {
            display: grid !important;
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
          [data-af-truth] {
            margin-top: 0 !important;
          }
          [data-af-workflow] {
            min-height: 72vh !important;
          }
        }
      `}</style>
      <section style={shell} data-af-shell>
        <aside style={assistant} data-af-assistant>
          <div style={brandRow}>
            <div style={mark}>AF</div>
            <div>
              <div style={eyebrow}>ArchiveForge</div>
              <h1 style={title}>LIFE magazine intake</h1>
            </div>
          </div>

          <p style={intro}>
            Start with a date, event, or person. ArchiveForge will find real LIFE cover references, keep them separate from your uploaded item photos, then guide the listing through review and MarketForge publish.
          </p>

          <a href="#life-workflow" style={cta}>Start issue lookup</a>

          <div style={guide} data-af-guide>
            <div style={guideTitle}>Assistant path</div>
            {steps.map((step, index) => (
              <div key={step} style={stepRow}>
                <span style={stepNum}>{index + 1}</span>
                <span>{step}</span>
              </div>
            ))}
          </div>

          <div style={truthBox} data-af-truth>
            <strong>Reference truth</strong>
            <span>Google Books covers are for identification only. MarketForge uses your actual uploaded photos.</span>
          </div>
        </aside>

        <section id="life-workflow" style={workflow} data-af-workflow aria-label="ArchiveForge LIFE workflow">
          <ArchiveForgePage />
        </section>
      </section>
    </main>
  );
}

const page = {
  minHeight: '100vh',
  background: '#f4f0e8',
  color: '#171717',
  fontFamily: "'Inter', 'Segoe UI', sans-serif",
} as const;

const shell = {
  minHeight: '100vh',
  display: 'grid',
  gridTemplateColumns: 'minmax(260px, 340px) minmax(0, 1fr)',
} as const;

const assistant = {
  background: '#111827',
  color: '#f9fafb',
  padding: '24px',
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
  borderRight: '1px solid #1f2937',
} as const;

const brandRow = {
  display: 'flex',
  gap: 12,
  alignItems: 'center',
} as const;

const mark = {
  width: 42,
  height: 42,
  borderRadius: 8,
  background: '#06b6d4',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 13,
  fontWeight: 900,
  color: '#fff',
} as const;

const eyebrow = {
  fontSize: 11,
  color: '#9ca3af',
  fontWeight: 800,
  textTransform: 'uppercase',
  letterSpacing: 0,
} as const;

const title = {
  margin: '2px 0 0',
  fontSize: 24,
  lineHeight: 1.1,
  fontWeight: 900,
  letterSpacing: 0,
} as const;

const intro = {
  margin: 0,
  fontSize: 14,
  lineHeight: 1.55,
  color: '#d1d5db',
} as const;

const cta = {
  display: 'inline-flex',
  justifyContent: 'center',
  borderRadius: 8,
  padding: '12px 14px',
  background: '#f9fafb',
  color: '#111827',
  fontSize: 13,
  fontWeight: 900,
  textDecoration: 'none',
} as const;

const guide = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
} as const;

const guideTitle = {
  fontSize: 12,
  color: '#9ca3af',
  fontWeight: 900,
  textTransform: 'uppercase',
  letterSpacing: 0,
} as const;

const stepRow = {
  display: 'flex',
  alignItems: 'center',
  gap: 9,
  fontSize: 13,
  lineHeight: 1.35,
  color: '#f3f4f6',
} as const;

const stepNum = {
  width: 22,
  height: 22,
  borderRadius: 8,
  background: '#1f2937',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 11,
  fontWeight: 900,
  color: '#67e8f9',
  flexShrink: 0,
} as const;

const truthBox = {
  marginTop: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  border: '1px solid #374151',
  borderRadius: 8,
  padding: 12,
  fontSize: 12,
  lineHeight: 1.4,
  color: '#d1d5db',
} as const;

const workflow = {
  minHeight: '100vh',
  overflow: 'hidden',
} as const;
