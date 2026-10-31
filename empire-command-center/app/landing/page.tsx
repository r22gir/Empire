// empirebox.store public landing (served at apex "/" via middleware rewrite → /landing).
// 2026-10 rewrite: three logical groups (Home & design / Business tools / Documents),
// recent work + design-to-build process, no retired/internal modules, no dead anchors.
// ApostApp is presented as a separate document service with no link to Workroom.

import type { LucideIcon } from 'lucide-react';
import RevealOnScroll from './RevealOnScroll';
import { GROUPS, PROCESS_STEPS, RECENT_WORK, type ModuleEntry } from './_data';

export const metadata = {
  title: 'EmpireBox — custom workroom, fabrics, woodwork, and small-business tools',
  description:
    'Empire Workroom, Empire Fine Fabrics, and Empire Woodworks: custom drapery, upholstery, and millwork from 3D design to CNC cutting to finish. Plus the business tools we built to run the shop.',
  robots: { index: true, follow: true },
};

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="eb-eyebrow-wrap">
      <span className="eb-eyebrow">{children}</span>
      <span className="eb-eyebrow-rule" aria-hidden="true" />
    </div>
  );
}

function Section({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="eb-section" data-reveal="">
      {children}
    </section>
  );
}

function ModuleCard({ m }: { m: ModuleEntry }) {
  const Icon: LucideIcon = m.icon;
  const inner = (
    <>
      <div className="eb-module-card-row1">
        <Icon className="eb-module-card-icon" size={20} aria-hidden="true" />
        <span className={`eb-badge ${m.status}`}>{m.statusText}</span>
      </div>
      <h3 className="eb-h3">{m.name}</h3>
      <p style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.55, margin: 0 }}>{m.description}</p>
      {m.ctaHref && <span className="eb-module-card-cta">{m.ctaLabel}</span>}
    </>
  );
  if (!m.ctaHref) {
    return (
      <div className="empire-card eb-module-card" aria-label={m.ariaLabel || `${m.name} — ${m.statusText}`} data-testid={`module-${m.id}`}>
        {inner}
      </div>
    );
  }
  return (
    <a href={m.ctaHref} className="empire-card eb-module-card" aria-label={m.ariaLabel || `${m.name} — ${m.statusText}`} data-testid={`module-${m.id}`}>
      {inner}
    </a>
  );
}

function HeaderBar() {
  return (
    <header className="eb-header" role="banner">
      <div className="eb-header-inner">
        <div>
          <a href="/" className="eb-wordmark" aria-label="EmpireBox home">EMPIREBOX</a>
          <span className="eb-tagline">custom work &amp; business tools</span>
        </div>
        <nav className="eb-nav" aria-label="Primary">
          <a href="#home-design">Home &amp; design</a>
          <a href="#recent-work">Our work</a>
          <a href="#business-tools">Business tools</a>
          <a href="#documents">Documents</a>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <Section>
      <Eyebrow>Washington DC · Maryland · Virginia</Eyebrow>
      <h1 className="eb-h1">EmpireBox</h1>
      <p className="eb-subhead">Custom drapery, upholstery, fabrics, and woodwork — designed, cut, and built in our own shop.</p>
      <p className="eb-body" style={{ color: 'var(--text)' }}>
        Empire Workroom makes window treatments, upholstery, and cushions. Empire Fine Fabrics supplies
        decorator fabrics. Empire Woodworks (coming soon) takes millwork and furniture from 3D design to
        CNC cutting to hand finish. The business tools we built to run all of it are available to other
        small service businesses too.
      </p>
      <div className="eb-hero-ctas">
        <a href="https://workroom.empirebox.store" className="eb-cta-primary" data-testid="cta-workroom">Visit the Workroom →</a>
        <a href="https://fabrics.empirebox.store" className="eb-cta-secondary" data-testid="cta-fabrics">Shop Empire Fine Fabrics</a>
        <a href="#recent-work" className="eb-cta-tertiary" data-testid="cta-recent-work">See recent work</a>
      </div>
    </Section>
  );
}

function Group({ g }: { g: (typeof GROUPS)[number] }) {
  return (
    <Section id={g.id}>
      <Eyebrow>{g.title}</Eyebrow>
      <h2 className="eb-h2">{g.title}</h2>
      <p className="eb-section-intro" style={{ color: 'var(--text)' }}>{g.intro}</p>
      <div className="eb-module-grid">
        {g.modules.map((m) => <ModuleCard key={m.id} m={m} />)}
      </div>
    </Section>
  );
}

function RecentWork() {
  return (
    <Section id="recent-work">
      <Eyebrow>Recent work &amp; our process</Eyebrow>
      <h2 className="eb-h2">From 3D design to CNC cutting to finished piece</h2>
      <ol className="eb-module-grid" style={{ listStyle: 'none', padding: 0 }} data-testid="process-steps">
        {PROCESS_STEPS.map((s, i) => {
          const Icon = s.icon;
          return (
            <li key={s.title} className="empire-card eb-module-card">
              <div className="eb-module-card-row1">
                <Icon className="eb-module-card-icon" size={20} aria-hidden="true" />
                <span className="eb-badge available">Step {i + 1}</span>
              </div>
              <h3 className="eb-h3">{s.title}</h3>
              <p style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.55, margin: 0 }}>{s.body}</p>
            </li>
          );
        })}
      </ol>
      <div className="eb-module-grid" style={{ marginTop: 24 }} data-testid="recent-work">
        {RECENT_WORK.map((w) => (
          <figure key={w.id} className="empire-card eb-module-card" style={{ margin: 0 }}>
            <div
              role="img"
              aria-label={`Photo placeholder: ${w.title}`}
              style={{
                aspectRatio: '4 / 3', borderRadius: 8, border: '2px dashed var(--border-h)',
                background: 'var(--panel)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                textAlign: 'center', padding: 12, fontSize: 12, color: 'var(--text-secondary)',
              }}
            >
              PHOTO PLACEHOLDER<br />{w.photoNeeded}
            </div>
            <span className="eb-badge preview" style={{ alignSelf: 'flex-start' }}>{w.category}</span>
            <h3 className="eb-h3">{w.title}</h3>
            <figcaption style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.55 }}>{w.blurb}</figcaption>
          </figure>
        ))}
      </div>
    </Section>
  );
}

function TrustSection() {
  return (
    <Section id="trust">
      <Eyebrow>Good to know</Eyebrow>
      <div className="eb-rail">
        <div className="eb-trust-card">
          <p><strong>Every quote is reviewed by a person.</strong> Our tools help draft and organize work; nothing goes to a customer without operator review.</p>
          <p><strong>Shipping is paid by the customer</strong> on fabric and product orders.</p>
          <p><strong>ApostApp is a separate document service.</strong> EmpireBox is not a law firm and does not give legal advice; government processing times vary and are outside our control.</p>
        </div>
      </div>
    </Section>
  );
}

function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="eb-footer" role="contentinfo">
      <div>© {year} EmpireBox · empirebox.store</div>
      <div className="eb-footer-row">Washington DC · Maryland · Virginia</div>
      <div className="eb-footer-row">Contact: <a href="mailto:hello@empirebox.store">hello@empirebox.store</a></div>
    </footer>
  );
}

export default function LandingPage() {
  const [home, business, documents] = GROUPS;
  return (
    <main data-empirebox-page>
      <a href="#main" className="eb-skip-link">Skip to main content</a>
      <HeaderBar />
      <div id="main" className="eb-outer">
        <Hero />
        <Group g={home} />
        <RecentWork />
        <Group g={business} />
        <Group g={documents} />
        <TrustSection />
      </div>
      <Footer />
      <RevealOnScroll />
    </main>
  );
}
