// R1X-PUB-EMPIREBOX — public apex landing page.
// This route is served at https://empirebox.store/ and https://www.empirebox.store/
// via the host-aware middleware in /middleware.ts. The middleware rewrites
// the apex root "/" → "/landing" so this file is the rendered body for both
// hostnames. The Command Center at app/page.tsx is NOT touched.
//
// Section outline follows R1X-PUB-EMPIREBOX-COPY.md §1:
//   1 Header / Nav
//   2 Hero
//   3 What EmpireBox Is
//   4 Ecosystem Map
//   5 Module Grid
//   6 How It Works
//   7 Trust & Disclaimers
//   8 CTAs / Next Steps
//   9 Footer

import type { LucideIcon } from 'lucide-react';
import RevealOnScroll from './RevealOnScroll';
import { MODULES, WORKFLOWS, type ModuleEntry, type WorkflowStep } from './_data';

export const metadata = {
  title: 'EmpireBox — practical service tools for documents, business, and operations',
  description:
    'EmpireBox is an ecosystem of focused apps for document apostille, business formation, custom fabrication, pricing, and operations. Start with ApostApp, expand as you grow.',
  robots: { index: true, follow: true },
};

// ──────────────────────────────────────────────────────────────────────────
// Small visual primitives (server-rendered, zero client JS)
// ──────────────────────────────────────────────────────────────────────────

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="eb-eyebrow-wrap">
      <span className="eb-eyebrow">{children}</span>
      <span className="eb-eyebrow-rule" aria-hidden="true" />
    </div>
  );
}

function Section({ id, children, reveal }: { id?: string; children: React.ReactNode; reveal?: boolean }) {
  return (
    <section id={id} className="eb-section" data-reveal={reveal ? '' : undefined}>
      {children}
    </section>
  );
}

/**
 * Module card. Status pill + icon + name + description + CTA.
 * The whole card is a link; if href is "#" (or starts with # and points
 * nowhere useful) the link is rendered but muted.
 */
function ModuleCard({ m }: { m: ModuleEntry }) {
  const Icon: LucideIcon = m.icon;
  const ctaDisabled = m.ctaHref === '#' || !m.ctaHref;
  const statusText = m.statusText;
  return (
    <a
      href={m.ctaHref}
      className="empire-card eb-module-card"
      aria-label={m.ariaLabel || `${m.name} — ${statusText}`}
      data-testid={`module-${m.id}`}
    >
      <div className="eb-module-card-row1">
        <Icon className="eb-module-card-icon" size={20} aria-hidden="true" />
        <span className={`eb-badge ${m.status}`}>{statusText}</span>
      </div>
      <h3 className="eb-h3">{m.name}</h3>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.55, margin: 0 }}>
        {m.description}
      </p>
      <span className={`eb-module-card-cta${ctaDisabled ? ' disabled' : ''}`}>{m.ctaLabel}</span>
    </a>
  );
}

function WorkflowSteps({ steps }: { steps: WorkflowStep[] }) {
  return (
    <ol
      className="eb-workflow-steps"
      style={{ ['--eb-steps' as string]: steps.length } as React.CSSProperties}
    >
      {steps.map((s, i) => (
        <li key={i} className="eb-workflow-step">
          <span className="eb-workflow-num">{String(i + 1).padStart(2, '0')}</span>
          <h3 className="eb-workflow-title">
            {s.title}
            {s.marker && (
              <span className={`eb-verified ${s.marker}`} title="Verified status marker">
                {s.markerText || markerLabel(s.marker)}
              </span>
            )}
          </h3>
          <p className="eb-workflow-body">{s.body}</p>
        </li>
      ))}
    </ol>
  );
}

function markerLabel(m: WorkflowStep['marker']): string {
  switch (m) {
    case 'full':    return 'VERIFIED';
    case 'partial': return 'VERIFIED_PARTIAL';
    case 'founder': return 'FOUNDER-ONLY';
    case 'vision':  return 'VISION-ONLY';
  }
}

// ──────────────────────────────────────────────────────────────────────────
// Hero — eyebrow + H1 + subhead + body + 2-3 CTAs
// ──────────────────────────────────────────────────────────────────────────

function Hero() {
  return (
    <Section reveal>
      <Eyebrow>The EmpireBox ecosystem</Eyebrow>
      <h1 className="eb-h1">EmpireBox</h1>
      <p className="eb-subhead">
        Practical service tools for documents, business, and operations.
      </p>
      <p className="eb-body">
        EmpireBox is the system behind a small set of real services. Each module does one job
        well: ApostApp handles document apostille and authentication, LLCFactory helps you form
        a company, the Workroom and WoodCraft modules run custom fabrication workflows,
        Pricing Studio builds clear quotes, ContractorForge coordinates service jobs, and
        MAX/EmpireAssist keeps phone, email, and follow-up organized. The modules share data,
        share a design language, and share a single operator — so the work that used to live
        in five different tools lives in one ecosystem.
      </p>
      <div className="eb-hero-ctas">
        <a
          href="https://apostapp.empirebox.store/apostille"
          className="eb-cta-primary"
          data-testid="cta-start-apostapp"
        >
          Start with ApostApp →
        </a>
        <a
          href="https://apostapp.empirebox.store/apostille/status"
          className="eb-cta-secondary"
          data-testid="cta-track-order"
        >
          Track an ApostApp order
        </a>
        <a href="#start" className="eb-cta-tertiary" data-testid="cta-founder-preview">
          Request Founder preview
        </a>
      </div>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// What EmpireBox Is — 3-5 sentence explainer for non-technical readers
// ──────────────────────────────────────────────────────────────────────────

function WhatEmpireBoxIs() {
  return (
    <Section reveal>
      <Eyebrow>What EmpireBox is</Eyebrow>
      <h2 className="eb-h2">A small operating system for a service-led business</h2>
      <div className="eb-rail">
        <p className="eb-body" style={{ maxWidth: 'none' }}>
          EmpireBox is the operating system for a small, service-led business. It groups the
          everyday tools you would otherwise stitch together by hand — document preparation and
          apostille, business formation, custom fabrication, pricing, customer follow-up, social
          coordination, and operations — into one ecosystem that a single operator can actually
          run.
        </p>
        <p className="eb-body" style={{ maxWidth: 'none' }}>
          It is not a law firm and does not give legal advice. It is not a generic SaaS bundle.
          It is a set of focused modules that you turn on as you need them, with a consistent
          interface and a shared back office. The modules range from “Available” today to
          “On the roadmap,” and the public page is honest about which is which.
        </p>
        <p className="eb-body" style={{ maxWidth: 'none' }}>
          A useful way to think about it: EmpireBox is the box, and each module is a tool inside
          it. You do not have to buy the whole ecosystem to use one of the tools. You can start
          with a single module and add more as your business grows.
        </p>
      </div>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Ecosystem Diagram — inline SVG hub-and-spoke, with a vertical mobile fallback
// ──────────────────────────────────────────────────────────────────────────

function EcosystemDiagram() {
  return (
    <div
      className="eb-eco-wrap"
      role="img"
      aria-label="EmpireBox ecosystem diagram. Center: EmpireBox. Spokes: ApostApp, Workroom, WoodCraft, ContractorForge, Pricing Studio, MAX / EmpireAssist."
    >
      <svg
        viewBox="0 0 960 540"
        xmlns="http://www.w3.org/2000/svg"
        className="eb-eco-svg"
        data-testid="ecosystem-diagram"
      >
        {/* Center hub */}
        <g>
          <circle cx="480" cy="270" r="78" fill="var(--panel)" stroke="var(--gold-border)" strokeWidth="2" />
          <text
            x="480"
            y="262"
            textAnchor="middle"
            fontSize="14"
            fontWeight="700"
            fill="var(--text)"
            fontFamily="Inter, system-ui, sans-serif"
          >
            EMPIREBOX
          </text>
          <text
            x="480"
            y="282"
            textAnchor="middle"
            fontSize="11"
            fontWeight="500"
            fill="var(--muted)"
            fontFamily="Inter, system-ui, sans-serif"
          >
            the ecosystem
          </text>
        </g>

        {/* Spokes — 6 spokes, 60° apart starting at -90° */}
        {[0, 60, 120, 180, 240, 300].map((angle, i) => {
          const rad = ((angle - 90) * Math.PI) / 180;
          const x1 = 480 + Math.cos(rad) * 90;
          const y1 = 270 + Math.sin(rad) * 90;
          const x2 = 480 + Math.cos(rad) * 200;
          const y2 = 270 + Math.sin(rad) * 200;
          return (
            <line
              key={`spoke-${i}`}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="var(--border-h)"
              strokeWidth="1.5"
            />
          );
        })}

        {/* Module nodes */}
        {[
          { label: 'ApostApp',        sub: 'Apostilles',       dx:    0, dy: -210, live: true  },
          { label: 'Workroom',        sub: 'Upholstery',       dx:  182, dy: -105, live: false },
          { label: 'WoodCraft',       sub: 'Furniture',        dx:  182, dy:  105, live: false },
          { label: 'ContractorForge', sub: 'Service business', dx:    0, dy:  210, live: false },
          { label: 'Pricing Studio',  sub: 'Quotes & cost',    dx: -182, dy:  105, live: false },
          { label: 'MAX / Assist',    sub: 'Operations',       dx: -182, dy: -105, live: false },
        ].map((m, i) => (
          <g key={`node-${i}`} transform={`translate(${480 + m.dx}, ${270 + m.dy})`}>
            <rect
              x={-72}
              y={-28}
              width={144}
              height={56}
              rx={10}
              fill={m.live ? 'var(--gold-light)' : 'var(--card-bg)'}
              stroke={m.live ? 'var(--gold-border)' : 'var(--border)'}
              strokeWidth={m.live ? 1.5 : 1}
            />
            <text
              x="0"
              y={-4}
              textAnchor="middle"
              fontSize="13"
              fontWeight="700"
              fill="var(--text)"
              fontFamily="Inter, system-ui, sans-serif"
            >
              {m.label}
            </text>
            <text
              x="0"
              y="14"
              textAnchor="middle"
              fontSize="10"
              fontWeight="500"
              fill="var(--text-secondary)"
              fontFamily="Inter, system-ui, sans-serif"
            >
              {m.sub}
            </text>
          </g>
        ))}
      </svg>

      {/* Mobile fallback — vertical list */}
      <ol className="eb-eco-list" aria-hidden="true">
        {[
          'ApostApp — Apostilles',
          'Workroom — Upholstery',
          'WoodCraft — Furniture',
          'ContractorForge — Service business',
          'Pricing Studio — Quotes & cost',
          'MAX / Assist — Operations',
        ].map((label) => (
          <li
            key={label}
            className="empire-card"
            style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}
          >
            {label}
          </li>
        ))}
      </ol>

      {/* Long description for screen readers / SEO */}
      <p className="eb-eco-sr">
        EmpireBox is the system. ApostApp is the customer-facing apostille service. Workroom and
        WoodCraft handle fabrication. ContractorForge serves service businesses. Pricing Studio
        generates quotes. MAX and EmpireAssist are the operations layer.
      </p>
    </div>
  );
}

function EcosystemSection() {
  return (
    <Section id="ecosystem" reveal>
      <Eyebrow>The ecosystem</Eyebrow>
      <h2 className="eb-h2">How the pieces fit</h2>
      <p className="eb-section-intro">
        EmpireBox is organized as one ecosystem of focused modules. The map below shows what is
        live, what is in active development, and what is on the roadmap. The map is the source of
        truth for what EmpireBox is — if a module is not on the map, it is not part of the public
        product yet.
      </p>
      <EcosystemDiagram />
      <p
        style={{
          fontSize: 13,
          color: 'var(--muted)',
          lineHeight: 1.55,
          maxWidth: 640,
          margin: '16px auto 0',
          textAlign: 'center',
        }}
      >
        ApostApp, Workroom, WoodCraft, ContractorForge, Pricing Studio, and MAX/EmpireAssist
        are the customer-facing surface. The supporting services and operator tools behind them
        are what makes the system work.
      </p>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Module Grid — every GREEN/YELLOW module + 2 PARKED. No ShipForge.
// ──────────────────────────────────────────────────────────────────────────

function ModuleGrid() {
  return (
    <Section id="modules" reveal>
      <Eyebrow>What&apos;s available</Eyebrow>
      <h2 className="eb-h2">The module grid</h2>
      <p className="eb-section-intro">
        Every module in the EmpireBox ecosystem, in one place. Status labels are honest: the
        four public labels are <em>Available</em>, <em>In active development</em>,
        <em>Founder preview</em>, and <em>On the roadmap</em>.
      </p>
      <div className="eb-module-grid">
        {MODULES.map((m) => (
          <ModuleCard key={m.id} m={m} />
        ))}
      </div>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// How It Works — the 5 workflow examples with [VERIFIED] markers
// ──────────────────────────────────────────────────────────────────────────

function HowItWorks() {
  return (
    <Section id="how-it-works" reveal>
      <Eyebrow>How it works</Eyebrow>
      <h2 className="eb-h2">Five real workflows</h2>
      <p className="eb-section-intro">
        Each example shows what you do and what EmpireBox handles. Inline markers show whether
        each step is fully verified in production, verified in part, or a vision item still on
        the roadmap.
      </p>
      <div className="eb-rail">
        {WORKFLOWS.map((wf) => (
          <article key={wf.id} id={wf.id} className="eb-workflow" data-testid={wf.id}>
            <p className="eb-workflow-label">{wf.label}</p>
            <span
              className="eb-verified"
              style={{ marginLeft: 0, marginBottom: 12, display: 'inline-block' }}
            >
              {wf.badge}
            </span>
            <WorkflowSteps steps={wf.steps} />
            <div className="eb-workflow-honest">
              <span className="eb-workflow-honest-label">Honest limits: </span>
              {wf.honestLimits}
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Visual accent — gold rule that grows on scroll
// ──────────────────────────────────────────────────────────────────────────

function VisualAccent() {
  return (
    <div className="eb-visual-accent" data-reveal>
      <div className="eb-gold-rule" />
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Trust & Disclaimers — verbatim from COPY §2.F
// ──────────────────────────────────────────────────────────────────────────

function TrustSection() {
  return (
    <Section id="trust" reveal>
      <Eyebrow>Important things to know</Eyebrow>
      <h2 className="eb-h2">Trust &amp; disclaimers</h2>
      <div className="eb-rail">
        <div className="eb-trust-card">
          <p>
            <strong>EmpireBox is a software ecosystem, not a law firm, and EmpireBox does not
            provide legal advice.</strong> If you need legal advice — for a document, a contract,
            a filing, or a business decision — please consult a licensed attorney in the relevant
            jurisdiction. Where a module touches a regulated activity (for example, ApostApp’s
            document apostille and authentication), the work is performed by qualified operators
            and vendors; EmpireBox provides the system that organizes the work, not the regulated
            service itself.
          </p>
          <p>
            <strong>Government processing times vary.</strong> Apostille and authentication
            processing times are set by the issuing government office (for example, the DC, MD,
            or VA Secretary of State) and by the U.S. Department of State for federal documents.
            EmpireBox cannot guarantee a processing time, an approval, or an outcome, and rush or
            expedited tiers reflect the operator’s effort, not a guarantee of government action.
            <strong> A government office may request additional documents, an in-person
            appearance, or a correction at any time</strong>; the customer is responsible for
            responding to those requests promptly.
          </p>
          <p>
            <strong>Third-party services have separate terms.</strong> Payments, banking, social
            platforms, marketplace listings, government filings, courier services, and any other
            third-party integrations are governed by those providers’ own terms, fees, and
            policies. EmpireBox is not a party to those agreements and does not warrant their
            availability, pricing, or behavior. Where a module uses a third-party provider (for
            example, a payment rail, a courier, or a translation vendor), the customer’s
            relationship for that specific service is with that provider.
          </p>
          <p>
            <strong>Operator review is part of the workflow.</strong> Several EmpireBox modules
            use AI to draft, summarize, or route work. Every EmpireBox output that leaves the
            system is reviewed by a human operator before it is sent, posted, or filed. You
            should expect operator review at every step that touches a customer, a vendor, or a
            government office.
          </p>
          <p>
            <strong>No outcome guarantees.</strong> EmpireBox helps organize business workflows —
            it does not guarantee revenue, customer acquisition, government approval, or any
            specific business outcome. Where a module supports a regulated or licensed activity,
            the relevant professional, vendor, or government office remains responsible for the
            work.
          </p>
          <p>
            <strong>Data and privacy.</strong> Customer and order data is stored in the
            EmpireBox system and is only shared with the third parties needed to perform the
            requested service (for example, a notary, a translator, a courier, a government
            office, or a payment provider). EmpireBox does not sell customer data.
          </p>
        </div>
      </div>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// ApostApp preservation callout — kept short; ApostApp lives elsewhere
// ──────────────────────────────────────────────────────────────────────────

function ApostAppCallout() {
  return (
    <Section reveal>
      <div className="eb-rail">
        <aside
          style={{
            background: 'var(--blue-bg)',
            border: '1px solid #bfdbfe',
            borderRadius: 'var(--radius-sm)',
            padding: 16,
            fontSize: 14,
            lineHeight: 1.6,
            color: 'var(--text-secondary)',
          }}
        >
          <strong style={{ color: 'var(--text)' }}>ApostApp</strong> — apostille &amp; document
          legalization support — lives at{' '}
          <a
            href="https://apostapp.empirebox.store/apostille"
            className="eb-link"
            data-testid="callout-apostapp"
          >
            apostapp.empirebox.store/apostille
          </a>
          . The intake form, the status tracker, and the post-intake confirmation all run on
          that hostname and are not part of this landing page.
        </aside>
      </div>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// CTAs / Next Steps — the final 3-4 action cards
// ──────────────────────────────────────────────────────────────────────────

function CtaSection() {
  return (
    <Section id="start" reveal>
      <Eyebrow>Start here</Eyebrow>
      <h2 className="eb-h2">Pick a place to start</h2>
      <p className="eb-section-intro">
        You do not have to buy the whole ecosystem. Pick the one that meets you where you are.
      </p>
      <div className="eb-cta-grid">
        <div className="eb-cta-card gold">
          <h3>Start with ApostApp</h3>
          <p>
            Open the public apostille intake and place an order. Available today for DC, MD, VA,
            and Federal documents.
          </p>
          <a
            href="https://apostapp.empirebox.store/apostille"
            data-testid="cta-card-start-apostapp"
          >
            Go to ApostApp →
          </a>
        </div>
        <div className="eb-cta-card green">
          <h3>Track an ApostApp order</h3>
          <p>Check the current status of an order by reference number on the public tracker.</p>
          <a
            href="https://apostapp.empirebox.store/apostille/status"
            data-testid="cta-card-track"
          >
            Open the status tracker →
          </a>
        </div>
        <div className="eb-cta-card blue">
          <h3>Explore the ecosystem</h3>
          <p>See every module, what it does, and where it stands. Or request Founder preview.</p>
          <a href="#ecosystem" data-testid="cta-card-explore">
            Jump to the ecosystem →
          </a>
        </div>
      </div>
    </Section>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Header / Nav (sticky, slim, 2 nav anchors)
// ──────────────────────────────────────────────────────────────────────────

function HeaderBar() {
  return (
    <header className="eb-header" role="banner">
      <div className="eb-header-inner">
        <div>
          <a href="#top" className="eb-wordmark" aria-label="EmpireBox home">
            EMPIREBOX
          </a>
          <span className="eb-tagline">practical service tools</span>
        </div>
        <nav className="eb-nav" aria-label="Primary">
          <a href="#ecosystem">Ecosystem</a>
          <a href="#start">Start</a>
        </nav>
      </div>
    </header>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Footer
// ──────────────────────────────────────────────────────────────────────────

function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="eb-footer" role="contentinfo">
      <div>© {year} EmpireBox · empirebox.store</div>
      <div className="eb-footer-row">Washington DC · Maryland · Virginia</div>
      <div className="eb-footer-row">
        EmpireBox is a software ecosystem, not a law firm, and does not provide legal advice.
      </div>
      <div className="eb-footer-row">
        Contact:{' '}
        <a href="mailto:hello@empirebox.store">hello@empirebox.store</a>
      </div>
    </footer>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Page entry
// ──────────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <main data-empirebox-page>
      <a href="#main" className="eb-skip-link">
        Skip to main content
      </a>
      <HeaderBar />
      <div id="main" className="eb-outer">
        <Hero />
        <WhatEmpireBoxIs />
        <EcosystemSection />
        <ModuleGrid />
        <HowItWorks />
        <VisualAccent />
        <TrustSection />
        <ApostAppCallout />
        <CtaSection />
      </div>
      <Footer />
      <RevealOnScroll />
    </main>
  );
}
