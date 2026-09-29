'use client';

/**
 * Always-PDF control.
 * Download PDF — a real document endpoint already exists.
 * Print / Export PDF — no document backend; the browser print dialog
 * saves the current view. Never invents an empty PDF file.
 */
export default function ViewPdfControl({
  mode,
  title,
  onDownload,
}: {
  mode: 'print' | 'unavailable';
  title?: string;
  onDownload?: () => void;
}) {
  if (mode === 'unavailable') {
    return (
      <button
        type="button"
        disabled
        title={title || 'No PDF for this screen yet.'}
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: '#999',
          background: '#f3f1ec',
          border: '1px solid #e5e0d8',
          borderRadius: 8,
          padding: '6px 12px',
          cursor: 'not-allowed',
        }}
      >
        Download PDF
      </button>
    );
  }

  return (
    <button
      type="button"
      title={title || 'Opens the browser print dialog so you can save this view as a PDF. This screen does not generate a quote or job PDF.'}
      onClick={() => {
        if (onDownload) onDownload();
        else window.print();
      }}
      style={{
        fontSize: 12,
        fontWeight: 700,
        color: '#1a1a2e',
        background: '#fff',
        border: '1px solid #b8912f',
        borderRadius: 8,
        padding: '6px 12px',
        cursor: 'pointer',
        whiteSpace: 'nowrap',
      }}
    >
      Print / Export PDF
    </button>
  );
}
