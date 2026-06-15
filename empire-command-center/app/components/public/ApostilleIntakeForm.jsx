'use client';

import { useEffect, useState } from 'react';

export default function ApostilleIntakeForm() {
  const [packages, setPackages] = useState([]);
  const [testMode, setTestMode] = useState(true);
  const [selectedPackage, setSelectedPackage] = useState('standard');
  const [form, setForm] = useState({
    client_name: '',
    email: '',
    phone: '',
    document_type: 'articles_of_organization',
    destination_country: '',
    origin_state: 'MD',
    notes: '',
    // R1D-PUB-NAV-2 optional Service Navigator signals (defaults: empty / unchecked)
    service_path: '',
    notarization_needed: false,
    business_document_interest: false,
    interested_in_llcfactory: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch('/api/v1/apostapp/public/packages')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        setPackages(d.packages || []);
        setTestMode(d.test_mode);
      })
      .catch(function () { setError('Could not load service packages. Please refresh.'); });
  }, []);

  function update(field, value) {
    setForm(function (f) {
      var next = {};
      for (var k in f) next[k] = f[k];
      next[field] = value;
      return next;
    });
  }

  function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    // R1D-PUB-NAV-2: include the optional Service Navigator signals.
    // The 3 booleans are coerced to true|false|null so the backend can
    // distinguish "not engaged" (null) from "explicitly false".
    var body = {
      client_name: form.client_name,
      email: form.email,
      phone: form.phone,
      document_type: form.document_type,
      destination_country: form.destination_country,
      origin_state: form.origin_state,
      service_level: selectedPackage,
      notes: form.notes,
    };
    // Only include service_path if non-empty
    if (form.service_path) body.service_path = form.service_path;
    // Always include booleans so backend can record explicit intent
    body.notarization_needed = !!form.notarization_needed;
    body.business_document_interest = !!form.business_document_interest;
    body.interested_in_llcfactory = !!form.interested_in_llcfactory;
    fetch('/api/v1/apostapp/public/intake', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(function (r) { return r.json().then(function (body) { return { ok: r.ok, body: body }; }); })
      .then(function (res) {
        if (!res.ok) {
          var msg = (res.body && res.body.detail) ? res.body.detail : ('Request failed (' + res.body ? 'unknown' : 'unknown') + ')';
          throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
        }
        window.location.href = '/apostille/confirmation?order_id=' + res.body.order_id;
      })
      .catch(function (err) {
        setError(err.message || 'Request failed');
        setSubmitting(false);
      });
  }

  return (
    <form id="intake-form" onSubmit={submit} data-testid="intake-form" style={{ marginTop: 24 }}>
      {testMode && (
        <div style={{ background: '#fef3c7', color: '#92400e', padding: '10px', textAlign: 'center', fontSize: 13, marginBottom: 16, border: '1px solid #fcd34d', borderRadius: 4 }}>
          <strong>TEST MODE</strong> — No real payments will be charged. Stripe is in test mode.
        </div>
      )}

      <h2 style={{ fontSize: 18, marginTop: 0, marginBottom: 12 }}>Choose your package</h2>
      <div style={{ display: 'block', marginBottom: 16 }}>
        {packages.map(function (pkg) {
          var isSelected = selectedPackage === pkg.id;
          return (
            <label
              key={pkg.id}
              data-testid={'package-' + pkg.id}
              style={{
                display: 'block',
                padding: 12,
                marginBottom: 8,
                border: isSelected ? '2px solid #0ea5e9' : '1px solid #d4d4d4',
                borderRadius: 6,
                cursor: 'pointer',
                background: '#fff',
              }}
            >
              <input
                type="radio"
                name="package"
                value={pkg.id}
                checked={isSelected}
                onChange={function () { setSelectedPackage(pkg.id); }}
                style={{ marginRight: 8 }}
              />
              <strong>{pkg.name}</strong>
              <span style={{ marginLeft: 8, color: '#0ea5e9', fontWeight: 'bold' }}>
                From ${(pkg.price_cents / 100).toFixed(0)}
              </span>
              <span style={{ marginLeft: 8, color: '#737373', fontSize: 13 }}>
                {pkg.turnaround}
              </span>
              <div style={{ fontSize: 13, color: '#525252', marginTop: 4 }}>{pkg.description}</div>
            </label>
          );
        })}
      </div>

      <h2 style={{ fontSize: 18, marginTop: 0, marginBottom: 12 }}>Tell us about your request</h2>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>
          Your name *
        </label>
        <input
          type="text"
          required
          value={form.client_name}
          onChange={function (e) { update('client_name', e.target.value); }}
          placeholder="Full name"
          style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>
          Email *
        </label>
        <input
          type="email"
          required
          value={form.email}
          onChange={function (e) { update('email', e.target.value); }}
          placeholder="you@example.com"
          style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>
          Phone (optional)
        </label>
        <input
          type="tel"
          value={form.phone}
          onChange={function (e) { update('phone', e.target.value); }}
          placeholder="555-0100"
          style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>
          State of document origin *
        </label>
        <select
          value={form.origin_state}
          onChange={function (e) { update('origin_state', e.target.value); }}
          style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
        >
          <option value="DC">District of Columbia</option>
          <option value="MD">Maryland</option>
          <option value="VA">Virginia</option>
          <option value="FED">Federal (US Dept of State)</option>
        </select>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>
          Document type *
        </label>
        <select
          value={form.document_type}
          onChange={function (e) { update('document_type', e.target.value); }}
          style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
        >
          <option value="articles_of_organization">Articles of Organization</option>
          <option value="birth_certificate">Birth Certificate</option>
          <option value="marriage_certificate">Marriage Certificate</option>
          <option value="death_certificate">Death Certificate</option>
          <option value="diploma">Diploma</option>
          <option value="transcript">Transcript</option>
          <option value="corporate_document">Corporate Document</option>
          <option value="operating_agreement">Operating Agreement</option>
          <option value="power_of_attorney">Power of Attorney</option>
          <option value="affidavit">Affidavit</option>
          <option value="court_order">Court Order</option>
          <option value="fbi_background_check">FBI Background Check</option>
          <option value="commercial_invoice">Commercial Invoice</option>
          <option value="certificate_of_good_standing">Certificate of Good Standing</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>
          Destination country *
        </label>
        <input
          type="text"
          required
          value={form.destination_country}
          onChange={function (e) { update('destination_country', e.target.value); }}
          placeholder="e.g. Colombia"
          style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>
          Notes (optional)
        </label>
        <textarea
          value={form.notes}
          onChange={function (e) { update('notes', e.target.value); }}
          placeholder="Anything we should know?"
          rows={3}
          style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box', fontFamily: 'inherit' }}
        />
      </div>

      {/* R1D-PUB-NAV-2: optional Service Navigator signals.
          All four fields are OPTIONAL. They help the team understand what
          the customer was looking at on the navigator before submitting. */}
      <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 4, padding: 12, marginBottom: 12, fontSize: 13, color: '#0c4a6e' }} data-testid="nav-metadata">
        <strong>Optional — help us help you</strong>
        <p style={{ margin: '4px 0 8px', fontSize: 12, lineHeight: 1.5 }}>
          The information above tells us what you need. The fields below tell us
          which service path or topic you were exploring on the page. This is
          optional and helps us route your request faster.
        </p>
        <div style={{ marginBottom: 8 }}>
          <label style={{ display: 'block', fontSize: 12, fontWeight: 'bold', marginBottom: 3 }}>
            Which service path applies to you?
          </label>
          <select
            value={form.service_path}
            onChange={function (e) { update('service_path', e.target.value); }}
            data-testid="service-path"
            style={{ width: '100%', padding: 6, fontSize: 13, border: '1px solid #bae6fd', borderRadius: 4, boxSizing: 'border-box', background: '#fff' }}
          >
            <option value="">— not sure / just starting —</option>
            <option value="state_apostille">State Apostille (DC/MD/VA)</option>
            <option value="federal_apostille">Federal Apostille (US Dept. of State, DS-4194)</option>
            <option value="embassy_legalization">Embassy / Consular Legalization (non-Hague country)</option>
            <option value="certified_copy">Certified Copy Request</option>
            <option value="vital_records_apostille">Vital Records + Apostille</option>
            <option value="fbi_background_apostille">FBI Background Check + Apostille</option>
            <option value="other">Other / not listed</option>
          </select>
        </div>
        <div style={{ marginBottom: 6 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={form.notarization_needed}
              onChange={function (e) { update('notarization_needed', e.target.checked); }}
              data-testid="notarization-needed"
            />
            My document needs notarization (I&apos;ll use the Remote Notary / RON option)
          </label>
        </div>
        <div style={{ marginBottom: 6 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={form.business_document_interest}
              onChange={function (e) { update('business_document_interest', e.target.checked); }}
              data-testid="business-document-interest"
            />
            This is for a business document (Certificate of Good Standing, Articles of Organization, etc.)
          </label>
        </div>
        <div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={form.interested_in_llcfactory}
              onChange={function (e) { update('interested_in_llcfactory', e.target.checked); }}
              data-testid="interested-in-llcfactory"
            />
            I&apos;d like a follow-up about LLCFactory (LLC formation, business setup) before the apostille
          </label>
        </div>
      </div>

      <div style={{ background: '#fafafa', border: '1px solid #e5e5e5', borderRadius: 4, padding: 12, fontSize: 12, lineHeight: 1.5, color: '#525252', marginBottom: 12 }}>
        <strong>By submitting, you agree to our terms:</strong>
        <p style={{ margin: '6px 0 0' }}>
          EmpireBox is not a government agency. Apostilles are issued by state Secretary of State
          offices (DC, MD, VA) or the U.S. Department of State. Processing times are estimates, not
          guarantees. The customer is responsible for providing accurate documents and information.
          Some documents may require notarization or certification before apostille. This service
          does not constitute legal advice. Refunds: 100% if EmpireBox errors; 50% if work has not
          started; no refund if work has started. Document privacy: we do not share with third
          parties except the issuing authority. Limitation of liability: capped at the amount paid.
        </p>
      </div>

      {error && (
        <div data-testid="error" style={{ background: '#fee2e2', color: '#991b1b', padding: 10, borderRadius: 4, fontSize: 14, marginBottom: 12 }}>
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        data-testid="submit"
        style={{
          padding: '12px 24px',
          background: submitting ? '#a3a3a3' : '#0ea5e9',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          fontSize: 16,
          fontWeight: 'bold',
          cursor: submitting ? 'not-allowed' : 'pointer',
          width: '100%',
        }}
      >
        {submitting ? 'Submitting…' : 'Request apostille'}
      </button>

      <p style={{ fontSize: 12, color: '#737373', textAlign: 'center', marginTop: 12 }}>
        Need to check an existing request? <a href="/apostille/status" style={{ color: '#0ea5e9' }}>Track your order</a>.
      </p>
    </form>
  );
}
