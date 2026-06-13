'use client';

import React from 'react';

const styles = {
  section: {
    fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
    color: '#1a1a1a',
    fontSize: 15,
    lineHeight: 1.6,
  },
  h2: {
    fontSize: 20,
    fontWeight: 800,
    marginTop: 28,
    marginBottom: 8,
    color: '#1a1a1a',
  },
  h3: {
    fontSize: 15,
    fontWeight: 700,
    margin: 0,
    marginBottom: 6,
    color: '#1a1a1a',
  },
  sub: {
    fontSize: 14,
    color: '#525252',
    margin: 0,
    marginBottom: 12,
    lineHeight: 1.5,
  },
  info: {
    background: '#f0f9ff',
    border: '1px solid #bae6fd',
    borderRadius: 6,
    padding: 14,
    fontSize: 14,
    lineHeight: 1.55,
    color: '#0c4a6e',
    margin: '12px 0',
  },
  warning: {
    background: '#fef3c7',
    border: '1px solid #fcd34d',
    borderRadius: 6,
    padding: 12,
    fontSize: 13,
    lineHeight: 1.55,
    color: '#92400e',
    margin: '12px 0',
  },
  cardGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: 12,
    marginTop: 8,
    marginBottom: 8,
  },
  card: {
    background: '#fafafa',
    border: '1px solid #e5e5e5',
    borderRadius: 6,
    padding: 14,
    fontSize: 14,
    color: '#1a1a1a',
  },
  cardTitle: {
    fontSize: 15,
    fontWeight: 700,
    margin: 0,
    marginBottom: 4,
    color: '#1a1a1a',
  },
  cardDesc: {
    fontSize: 14,
    color: '#1a1a1a',
    margin: 0,
    marginBottom: 8,
    lineHeight: 1.5,
  },
  cardMeta: {
    fontSize: 13,
    color: '#525252',
    margin: 0,
    marginTop: 6,
    lineHeight: 1.5,
  },
  cardMetaLabel: {
    fontWeight: 600,
    color: '#1a1a1a',
  },
  link: {
    color: '#0ea5e9',
  },
  ul: {
    margin: '6px 0 6px 0',
    paddingLeft: 20,
    fontSize: 14,
    color: '#1a1a1a',
    lineHeight: 1.6,
  },
  li: {
    marginBottom: 4,
  },
  faqItem: {
    marginBottom: 10,
    fontSize: 14,
    color: '#1a1a1a',
    lineHeight: 1.6,
  },
  faqQ: {
    fontWeight: 700,
    color: '#1a1a1a',
  },
  disclaimer: {
    fontStyle: 'italic',
    fontSize: 13,
    color: '#525252',
    lineHeight: 1.6,
    marginTop: 24,
    padding: '12px 14px',
    background: '#fafafa',
    border: '1px solid #e5e5e5',
    borderRadius: 6,
  },
  pricingRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    padding: '6px 0',
    borderBottom: '1px solid #e5e5e5',
    fontSize: 14,
  },
  pricingName: {
    fontWeight: 600,
    color: '#1a1a1a',
  },
  pricingMeta: {
    fontSize: 13,
    color: '#525252',
  },
  pricingPrice: {
    fontWeight: 700,
    color: '#1a1a1a',
  },
};

function ServiceCard(props) {
  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>{props.title}</h3>
      <p style={styles.cardDesc}>{props.description}</p>
      <p style={styles.cardMeta}>
        <span style={styles.cardMetaLabel}>Processing time: </span>
        {props.processing}
      </p>
      <p style={styles.cardMeta}>
        <span style={styles.cardMetaLabel}>Who needs it: </span>
        {props.who}
      </p>
    </div>
  );
}

function FaqItem(props) {
  return (
    <div style={styles.faqItem}>
      <div style={styles.faqQ}>{props.q}</div>
      <div>{props.a}</div>
    </div>
  );
}

export default function ApostilleServiceNavigator() {
  return (
    <section data-testid="service-navigator" style={styles.section}>
      {/* 1. SERVICE PATHS */}
      <h2 id="nav-services" style={styles.h2}>Service paths (choose what you need)</h2>
      <p style={styles.sub}>
        Most customers only need one of these. Pick the path that matches where your
        document came from and where it&apos;s going. Not sure? Submit the intake form
        below and we&apos;ll point you to the right one.
      </p>

      <div style={styles.cardGrid}>
        <ServiceCard
          title="State Apostille (DC / MD / VA)"
          description="For documents issued by a US state, to be used in a Hague Convention country."
          processing="5–10 business days"
          who="Individuals and businesses using state-issued documents abroad"
        />
        <ServiceCard
          title="Federal Apostille (US Dept. of State)"
          description="For federal documents such as FBI background checks, federal court documents, and USPTO patents. DS-4194 form."
          processing="5–11 weeks"
          who="Clients with federally issued documents headed to a Hague country"
        />
        <ServiceCard
          title="Embassy Legalization"
          description="For non-Hague countries (China, UAE, Qatar, and others). A chain: state → US Dept. of State → foreign embassy or consulate."
          processing="2–6 weeks"
          who="Anyone sending documents to a country that isn’t part of the Hague Apostille Convention"
        />
        <ServiceCard
          title="Certified Copy Request"
          description="When the original isn’t available, we obtain a certified copy from the issuing authority first, then apostille it."
          processing="3–10 business days (plus apostille time)"
          who="Customers who lost the original or only have a scan"
        />
        <ServiceCard
          title="Vital Records + Apostille"
          description="For birth, death, and marriage certificates from MD / DC / VA vital records offices."
          processing="7–14 business days"
          who="Family / personal records going abroad (citizenship, marriage, estate)"
        />
        <ServiceCard
          title="FBI Background Check + Apostille"
          description="Channeled through the FBI’s Identity History Summary Checks process, then federal apostille."
          processing="6–14 weeks"
          who="Immigration, work, or residency filings that need a US federal background check"
        />
      </div>

      {/* 2. NOTARIZATION */}
      <h2 id="nav-notary" style={styles.h2}>Notarization (if your document needs it)</h2>
      <div style={styles.info}>
        <strong>Will my document need notarization?</strong>
        <p style={{ margin: '6px 0 0 0' }}>
          Some documents (affidavits, powers of attorney, some business paperwork) must
          be signed in front of a notary before they can be apostilled. If yours is
          already signed and notarized, you can skip this step. If not, we can arrange
          it for you.
        </p>
      </div>

      <div style={styles.cardGrid}>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Document already notarized</h3>
          <p style={styles.cardDesc}>
            Great — skip notarization and proceed straight to apostille.
          </p>
        </div>
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Document needs notarization</h3>
          <p style={styles.cardDesc}>
            We coordinate remote online notarization (RON) via a licensed DC / MD / VA
            notary.
          </p>
          <p style={styles.cardMeta}>
            <span style={styles.cardMetaLabel}>Processing time: </span>
            1–3 business days
          </p>
          <p style={styles.cardMeta}>
            <strong>Remote Notary (RON) is available</strong> — we&apos;ll email you a
            secure link to meet with a notary on video. Available for clients in DC,
            MD, VA, and most other US states.
          </p>
          <p style={styles.cardMeta}>
            RON is handled by a licensed third-party notary; ApostApp schedules the
            session, you sign on video, the notary e-records the document. RON sessions
            are scheduled on business days within 24 hours of request; apostille work
            begins after RON completes.
          </p>
        </div>
      </div>

      {/* 3. BUSINESS-DOCUMENT APOSTILLE (not LLC formation) */}
      <h2 id="nav-business" style={styles.h2}>Business documents</h2>
      <p style={styles.cardDesc}>
        Business documents such as Certificates of Good Standing, Articles of
        Organization, corporate authorizations, and related records may need
        apostille or authentication after they are prepared or issued. ApostApp
        authenticates and legalizes these documents for use abroad.
      </p>

      {/* 3b. RELATED SERVICE NOTE (LLCFactory cross-link, small) */}
      <div style={{ ...styles.card, background: '#f0f9ff', borderColor: '#bae6fd' }}>
        <p style={styles.cardDesc}>
          <strong>Related service:</strong> Need help forming an LLC or preparing
          business documents before apostille? EmpireBox also offers LLCFactory
          for business setup support. ApostApp can help authenticate or legalize
          business documents after they are ready.
        </p>
      </div>

      {/* 4. PRICING & ESTIMATE */}
      <h2 id="nav-pricing" style={styles.h2}>Pricing &amp; estimate guidance</h2>
      <div style={styles.card}>
        <p style={{ ...styles.cardDesc, marginBottom: 10 }}>
          ApostApp has three live service packages. All packages include intake review,
          document handling guidance, and status updates.
        </p>

        <div style={styles.pricingRow}>
          <div>
            <div style={styles.pricingName}>Basic — Intake &amp; Review</div>
            <div style={styles.pricingMeta}>5–7 business days</div>
          </div>
          <div style={styles.pricingPrice}>$35</div>
        </div>
        <div style={styles.pricingRow}>
          <div>
            <div style={styles.pricingName}>Standard — Apostille Support</div>
            <div style={styles.pricingMeta}>3–5 business days</div>
          </div>
          <div style={styles.pricingPrice}>$95</div>
        </div>
        <div style={{ ...styles.pricingRow, borderBottom: 'none' }}>
          <div>
            <div style={styles.pricingName}>Rush — Apostille Support</div>
            <div style={styles.pricingMeta}>1–3 business days</div>
          </div>
          <div style={styles.pricingPrice}>$195</div>
        </div>

        <ul style={{ ...styles.ul, marginTop: 12 }}>
          <li style={styles.li}>
            State and federal filing fees are <strong>separate from</strong> ApostApp
            service fees (pass-through; amount varies by state and document type).
          </li>
          <li style={styles.li}>
            Embassy legalization fees (when applicable) are pass-through.
          </li>
          <li style={styles.li}>
            Shipping is <strong>additional</strong> and quoted at intake.
          </li>
          <li style={styles.li}>
            A final quote is provided before payment — nothing is charged until you
            approve it.
          </li>
        </ul>
      </div>

      {/* 5. SHIPPING */}
      <h2 id="nav-shipping" style={styles.h2}>Shipping options</h2>
      <div style={styles.card}>
        <p style={{ ...styles.cardDesc, marginBottom: 8 }}>
          Choose how we&apos;ll return your finished documents. Shipping is quoted at
          intake and added to the final price.
        </p>
        <ul style={styles.ul}>
          <li style={styles.li}>USPS Priority Mail — 3–5 business days — $12</li>
          <li style={styles.li}>USPS Express Mail — 1–2 business days — $28</li>
          <li style={styles.li}>FedEx Overnight — $45</li>
          <li style={styles.li}>International Priority — $65 (for returned documents going abroad)</li>
          <li style={styles.li}>Local Pickup (DC office) — $0</li>
        </ul>
      </div>

      {/* 6. UPLOAD / FILE SUBMISSION */}
      <h2 id="nav-upload" style={styles.h2}>Upload / file submission</h2>
      <p style={styles.sub}>
        After intake and payment, you&apos;ll receive an upload link by email for your
        document(s).
      </p>
      <div style={styles.warning}>
        <strong>Heads up:</strong> File upload is currently handled by email — after you
        submit the intake form below and pay, our team will email you a secure upload
        link within 1 business day. Direct in-browser upload is coming soon.
      </div>

      {/* 7. FAQ */}
      <h2 id="nav-faq" style={styles.h2}>Frequently asked questions</h2>
      <div style={styles.card}>
        <FaqItem
          q="What’s the difference between apostille and embassy legalization?"
          a="Apostille is for Hague Convention countries — one certificate is attached and the document is ready to use. Embassy legalization is for non-Hague countries and is a multi-step chain through the state, the US Department of State, and the destination country’s embassy or consulate."
        />
        <FaqItem
          q="How long does it take?"
          a="It depends on the service path. State apostille: 5–10 business days. Federal: 5–11 weeks. Embassy legalization: 2–6 weeks. Rush options are available for most paths."
        />
        <FaqItem
          q="Can I track my order?"
          a="Yes — after intake you’ll get an order ID and a status page where you can check progress at any time."
        />
        <FaqItem
          q="What payment methods do you accept?"
          a="Credit and debit card via Stripe. Secure checkout. We don’t store your card on file."
        />
        <FaqItem
          q="Are you a law firm?"
          a="No. ApostApp is a document preparation and submission service. We don’t provide legal advice. Government processing times are set by the issuing authority, not by us."
        />
      </div>

      {/* 8. DISCLAIMER */}
      <p style={styles.disclaimer}>
        ApostApp is not a law firm. We do not provide legal advice or representation.
        Final government processing times, fees, and acceptance are determined by the
        issuing authority. Information provided through ApostApp is for document
        preparation purposes only. If you need legal advice, consult a licensed
        attorney in the relevant jurisdiction.
      </p>
    </section>
  );
}
