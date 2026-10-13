'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';

type BioLink = {
  id: string;
  label: string;
  href: string;
  kind?: string;
  primary?: boolean;
};

type Bio = {
  slug: string;
  name: string;
  tagline: string;
  blurb: string;
  accent: string;
  services: string[];
  quote_intake_path: string;
  links: BioLink[];
};

export default function LinkInBioPage() {
  const params = useParams<{ slug: string }>();
  const slug = params?.slug || '';
  const [bio, setBio] = useState<Bio | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    fetch(`/api/v1/linkinbio/${slug}`)
      .then((r) => r.json().then((body) => ({ ok: r.ok, body })))
      .then((res) => {
        if (!res.ok) throw new Error(res.body?.detail || 'Page not found');
        setBio(res.body);
      })
      .catch((err) => setError(err.message || 'Could not load this page'));
  }, [slug]);

  if (error) {
    return (
      <main data-bio-page style={{ maxWidth: 480, margin: '0 auto', padding: '48px 16px', fontFamily: 'system-ui, sans-serif', textAlign: 'center' }}>
        <h1 style={{ fontSize: 22 }}>Page not found</h1>
        <p style={{ color: '#737373' }}>{error}</p>
      </main>
    );
  }

  if (!bio) {
    return (
      <main data-bio-page style={{ maxWidth: 480, margin: '0 auto', padding: '48px 16px', fontFamily: 'system-ui, sans-serif', textAlign: 'center', color: '#737373' }}>
        Loading…
      </main>
    );
  }

  return (
    <main data-bio-page style={{ maxWidth: 480, margin: '0 auto', padding: '40px 16px 80px', fontFamily: 'system-ui, sans-serif', color: '#1a1a1a' }}>
      <header style={{ textAlign: 'center', marginBottom: 28 }}>
        <div style={{ width: 72, height: 72, borderRadius: 24, margin: '0 auto 16px', background: bio.accent, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 22 }}>
          {bio.name.slice(0, 2).toUpperCase()}
        </div>
        <h1 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>{bio.name}</h1>
        <p style={{ fontSize: 15, color: '#525252', marginTop: 8 }}>{bio.tagline}</p>
        <p style={{ fontSize: 14, color: '#737373', marginTop: 10, lineHeight: 1.5 }}>{bio.blurb}</p>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 28 }}>
        {bio.links.map((link) => (
          <Link
            key={link.id}
            href={link.href}
            data-testid={link.kind === 'quote_intake' ? 'bio-quote-cta' : `bio-link-${link.id}`}
            style={{
              display: 'block',
              textAlign: 'center',
              padding: '14px 16px',
              borderRadius: 10,
              textDecoration: 'none',
              fontWeight: 700,
              fontSize: 16,
              background: link.primary ? bio.accent : '#fff',
              color: link.primary ? '#fff' : bio.accent,
              border: link.primary ? 'none' : `1px solid ${bio.accent}`,
            }}
          >
            {link.label}
          </Link>
        ))}
      </div>

      {bio.services?.length > 0 && (
        <section style={{ background: '#fafafa', border: '1px solid #e5e5e5', borderRadius: 10, padding: 16 }}>
          <h2 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.6, color: '#737373', marginTop: 0 }}>Services</h2>
          <ul style={{ margin: 0, paddingLeft: 18, color: '#404040', fontSize: 14, lineHeight: 1.7 }}>
            {bio.services.map((s) => <li key={s}>{s}</li>)}
          </ul>
        </section>
      )}

      <p style={{ textAlign: 'center', marginTop: 28, fontSize: 12, color: '#a3a3a3' }}>
        Quote requests go to LeadForge. Powered by EmpireBox.
      </p>
    </main>
  );
}
