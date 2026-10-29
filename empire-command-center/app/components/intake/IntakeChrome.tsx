'use client';
import { Crown, LogOut, User } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { clearToken } from '../../lib/intake-auth';

export const JOURNEY_STEPS = [
  { id: 'signup', label: 'Sign Up' },
  { id: 'project', label: 'Project' },
  { id: 'upload', label: 'Upload' },
  { id: 'submit', label: 'Submit' },
] as const;

export type JourneyId = (typeof JOURNEY_STEPS)[number]['id'] | 'done';

export function journeyFromFormStep(step: number): JourneyId {
  if (step <= 0) return 'project';
  if (step === 1) return 'upload';
  return 'submit';
}

export function IntakeBrand({ href = '/intake' }: { href?: string }) {
  return (
    <Link href={href} className="intake-brand" aria-label="Empire Workroom designer intake home">
      <span className="intake-brand-mark" aria-hidden="true">
        <Crown size={15} />
      </span>
      <span className="intake-brand-copy">
        <span className="intake-brand-name">Empire Workroom</span>
        <span className="intake-brand-sub">Designer Intake</span>
      </span>
    </Link>
  );
}

export function IntakePublicHeader({ showAuth = false }: { showAuth?: boolean }) {
  return (
    <header className="intake-header">
      <div className="intake-header-inner">
        <IntakeBrand />
        {showAuth && (
          <div className="intake-header-actions">
            <Link href="/intake/login" className="intake-link-quiet">Sign In</Link>
            <Link href="/intake/signup" className="intake-btn intake-btn-gold">Get Started</Link>
          </div>
        )}
      </div>
    </header>
  );
}

export function IntakeAuthedHeader({ user }: { user?: { name: string; company?: string } | null }) {
  const router = useRouter();
  const handleLogout = () => {
    clearToken();
    router.push('/intake');
  };

  return (
    <header className="intake-header">
      <div className="intake-header-inner">
        <IntakeBrand />
        {user && (
          <div className="intake-header-actions">
            <button
              type="button"
              onClick={() => router.push('/intake/account')}
              className="intake-icon-btn"
              title="My Account"
            >
              <User size={16} aria-hidden="true" />
              <span className="intake-hide-sm">{user.name}</span>
            </button>
            {user.company && <span className="intake-header-meta intake-hide-sm">{user.company}</span>}
            <button type="button" onClick={handleLogout} className="intake-icon-btn" title="Sign Out">
              <LogOut size={16} aria-hidden="true" />
              <span className="sr-only">Sign out</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export function IntakeStepper({ current }: { current: JourneyId }) {
  const order = JOURNEY_STEPS.map((s) => s.id);
  const currentIndex = current === 'done' ? JOURNEY_STEPS.length : order.indexOf(current);

  return (
    <ol className="intake-stepper" aria-label="Intake progress">
      {JOURNEY_STEPS.map((step, i) => {
        const state = i < currentIndex ? 'done' : i === currentIndex ? 'current' : 'todo';
        return (
          <li
            key={step.id}
            className={`intake-step intake-step-${state}`}
            aria-current={state === 'current' ? 'step' : undefined}
          >
            <span className="intake-step-dot" aria-hidden="true">
              {state === 'done' ? '✓' : i + 1}
            </span>
            <span className="intake-step-label">{step.label}</span>
            {i < JOURNEY_STEPS.length - 1 && <span className="intake-step-rule" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}

export function IntakeFooter() {
  return (
    <footer className="intake-footer">
      <p>© {new Date().getFullYear()} Empire Workroom · Custom drapery &amp; upholstery</p>
    </footer>
  );
}
