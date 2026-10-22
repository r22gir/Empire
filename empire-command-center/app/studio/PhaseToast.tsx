'use client';

export default function PhaseToast({ message, onDismiss }: { message: string | null; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <div
      className="phase-toast"
      data-testid="phase-toast"
      role="status"
      aria-live="polite"
      onClick={onDismiss}
    >
      {message}
    </div>
  );
}
