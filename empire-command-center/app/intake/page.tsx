'use client';
import { ArrowRight, Camera, ClipboardList, Send, UserPlus } from 'lucide-react';
import Link from 'next/link';
import { IntakeFooter, IntakePublicHeader } from '../components/intake/IntakeChrome';

const steps = [
  { icon: UserPlus, title: 'Sign Up', desc: 'Create a free designer account in under a minute.' },
  { icon: ClipboardList, title: 'Project', desc: 'Tell us the rooms, treatments, and fabric notes.' },
  { icon: Camera, title: 'Upload', desc: 'Drop photos, drawings, CAD, scans, or any project file.' },
  { icon: Send, title: 'Submit', desc: 'Send the brief. We reply with a quote within 24 hours.' },
];

export default function IntakeLanding() {
  return (
    <div data-intake-page className="min-h-screen flex flex-col">
      <IntakePublicHeader showAuth />

      <header className="intake-hero">
        <div className="intake-pill">
          Empire Workroom
        </div>
        <h1 className="intake-display">
          Submit your project.<br />A quote in 24 hours.
        </h1>
        <p>
          Custom drapery, upholstery, blinds, and more. Upload photos, add measurements, and describe the room — we handle the workroom side.
        </p>
        <Link href="/intake/signup" className="intake-btn intake-btn-gold">
          Start Your Project <ArrowRight size={16} aria-hidden="true" />
        </Link>
      </header>

      <main className="intake-shell intake-shell-wide" style={{ flex: 1 }}>
        <p className="intake-label" style={{ textAlign: 'center', marginBottom: 16 }}>How it works</p>
        <div className="intake-journey-grid">
          {steps.map((item, i) => (
            <Link key={item.title} href="/intake/signup" className="intake-journey-card">
              <div className="intake-journey-num">Step {i + 1}</div>
              <div className="intake-journey-icon">
                <item.icon size={22} aria-hidden="true" />
              </div>
              <h2 style={{ fontSize: 22, margin: '0 0 8px' }}>{item.title}</h2>
              <p style={{ fontSize: 14, color: '#4f4a40', lineHeight: 1.5, margin: 0 }}>{item.desc}</p>
            </Link>
          ))}
        </div>
      </main>

      <IntakeFooter />
    </div>
  );
}
