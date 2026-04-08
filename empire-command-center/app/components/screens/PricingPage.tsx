'use client';
import { useState } from 'react';
import { Check, Sparkles, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';
import { API } from '../../lib/api';

const TIERS = [
  {
    id: 'lite' as const,
    name: 'Lite',
    monthlyPrice: 29,
    annualPrice: 24,
    description: 'Everything you need to launch your first business.',
    features: [
      '1 business workspace',
      'Basic AI assistant',
      'Quote & invoice management',
      'Email support',
    ],
    highlighted: false,
  },
  {
    id: 'pro' as const,
    name: 'Pro',
    monthlyPrice: 79,
    annualPrice: 66,
    description: 'Scale with advanced AI and multi-business tools.',
    features: [
      'Everything in Lite',
      '3 business workspaces',
      'Advanced AI (vision, voice)',
      'CraftForge + SocialForge',
      'Priority support',
    ],
    highlighted: true,
  },
  {
    id: 'empire' as const,
    name: 'Empire',
    monthlyPrice: 199,
    annualPrice: 166,
    description: 'The full suite for ambitious operators.',
    features: [
      'Everything in Pro',
      'Unlimited workspaces',
      'Full AI suite (all desks)',
      'Custom integrations',
      'Dedicated support',
      'White-label option',
    ],
    highlighted: false,
  },
];

const FAQS = [
  {
    q: 'How does the free trial work?',
    a: 'Every plan starts with a 14-day free trial. No credit card required to begin. You get full access to all features in your chosen tier during the trial period.',
  },
  {
    q: 'Can I switch plans later?',
    a: 'Yes. You can upgrade or downgrade at any time. When upgrading, you get immediate access to new features. When downgrading, changes take effect at the end of your current billing cycle.',
  },
  {
    q: 'What happens to my data if I cancel?',
    a: 'Your data is retained for 30 days after cancellation. You can export everything at any time. We never delete your data without notice.',
  },
  {
    q: 'Is there a discount for annual billing?',
    a: 'Yes. Annual billing saves you 2 months — that is roughly 17% off the monthly price. You can switch between monthly and annual billing at any time.',
  },
  {
    q: 'What AI models are included?',
    a: 'Lite includes our basic AI assistant powered by efficient models. Pro adds vision and voice capabilities. Empire unlocks the full AI suite with all 12 specialized desks, including advanced models like Grok, Claude, and local Ollama models.',
  },
  {
    q: 'Do you offer custom enterprise plans?',
    a: 'Yes. For teams with 10+ users or specialized needs, contact us for custom pricing, SLAs, and dedicated onboarding. Email support@empirebox.store.',
  },
];

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const handleCheckout = async (tier: 'lite' | 'pro' | 'empire') => {
    setLoading(tier);
    setError(null);
    try {
      const res = await fetch(`${API}/payments/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tier,
          success_url: window.location.origin + '/success',
          cancel_url: window.location.href,
        }),
      });

      if (res.status === 503) {
        setError('Stripe checkout is not yet configured. Coming soon!');
        setLoading(null);
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body.detail || 'Something went wrong. Please try again.');
        setLoading(null);
        return;
      }

      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        setError('No checkout URL returned. Please try again.');
      }
    } catch {
      setError('Could not reach the server. Please check your connection.');
    }
    setLoading(null);
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto', background: '#f5f3ef', padding: '48px 24px 80px' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto 40px' }}>
        <h1 style={{ fontSize: 32, fontWeight: 700, color: '#1a1a1a', margin: '0 0 12px', lineHeight: 1.2 }}>
          Simple, transparent pricing
        </h1>
        <p style={{ fontSize: 16, color: '#777', margin: 0, lineHeight: 1.6 }}>
          Start free for 14 days. No credit card required. Pick the plan that fits your business.
        </p>
      </div>

      {/* Billing Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginBottom: 40 }}>
        <span style={{ fontSize: 14, fontWeight: annual ? 400 : 600, color: annual ? '#999' : '#1a1a1a', transition: 'all 0.2s' }}>Monthly</span>
        <button
          onClick={() => setAnnual(!annual)}
          style={{
            width: 52,
            height: 28,
            borderRadius: 14,
            border: 'none',
            background: annual ? '#b8960c' : '#d8d3cb',
            position: 'relative',
            cursor: 'pointer',
            transition: 'background 0.2s',
            padding: 0,
          }}
        >
          <div style={{
            width: 22,
            height: 22,
            borderRadius: 11,
            background: '#fff',
            position: 'absolute',
            top: 3,
            left: annual ? 27 : 3,
            transition: 'left 0.2s',
            boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
          }} />
        </button>
        <span style={{ fontSize: 14, fontWeight: annual ? 600 : 400, color: annual ? '#1a1a1a' : '#999', transition: 'all 0.2s' }}>
          Annual
        </span>
        {annual && (
          <span style={{
            fontSize: 11, fontWeight: 700, color: '#b8960c', background: '#fdf8eb',
            padding: '3px 10px', borderRadius: 20, marginLeft: 4,
          }}>
            Save 2 months
          </span>
        )}
      </div>

      {/* Tier Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: 20,
        maxWidth: 1000,
        margin: '0 auto 60px',
        alignItems: 'start',
      }}>
        {TIERS.map((tier) => {
          const price = annual ? tier.annualPrice : tier.monthlyPrice;
          const isLoading = loading === tier.id;

          return (
            <div
              key={tier.id}
              style={{
                background: '#fff',
                borderRadius: 16,
                border: tier.highlighted ? '2px solid #b8960c' : '1px solid #ece8e0',
                padding: tier.highlighted ? '0' : '0',
                position: 'relative',
                overflow: 'hidden',
                boxShadow: tier.highlighted
                  ? '0 8px 32px rgba(184,150,12,0.15)'
                  : '0 2px 8px rgba(0,0,0,0.04)',
                transition: 'box-shadow 0.2s',
              }}
            >
              {/* Recommended badge */}
              {tier.highlighted && (
                <div style={{
                  background: '#b8960c',
                  color: '#fff',
                  textAlign: 'center',
                  fontSize: 11,
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  padding: '6px 0',
                }}>
                  <Sparkles size={12} style={{ display: 'inline', verticalAlign: -2, marginRight: 4 }} />
                  RECOMMENDED
                </div>
              )}

              <div style={{ padding: '28px 24px 24px' }}>
                {/* Tier name */}
                <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: '0 0 6px' }}>
                  {tier.name}
                </h2>
                <p style={{ fontSize: 13, color: '#999', margin: '0 0 20px', lineHeight: 1.5 }}>
                  {tier.description}
                </p>

                {/* Price */}
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 4 }}>
                  <span style={{ fontSize: 40, fontWeight: 700, color: '#1a1a1a', lineHeight: 1 }}>
                    ${price}
                  </span>
                  <span style={{ fontSize: 14, color: '#999' }}>/mo</span>
                </div>
                {annual && (
                  <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
                    <span style={{ textDecoration: 'line-through', marginRight: 6 }}>
                      ${tier.monthlyPrice}/mo
                    </span>
                    billed annually (${price * 12}/yr)
                  </div>
                )}

                <div style={{ height: 1, background: '#ece8e0', margin: '20px 0' }} />

                {/* Features */}
                <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px' }}>
                  {tier.features.map((f, i) => (
                    <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12 }}>
                      <Check size={16} style={{ color: '#b8960c', marginTop: 1, flexShrink: 0 }} />
                      <span style={{ fontSize: 13, color: '#555', lineHeight: 1.4 }}>{f}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <button
                  onClick={() => handleCheckout(tier.id)}
                  disabled={isLoading}
                  style={{
                    width: '100%',
                    padding: '12px 0',
                    borderRadius: 10,
                    border: tier.highlighted ? 'none' : '1px solid #ece8e0',
                    background: tier.highlighted
                      ? 'linear-gradient(135deg, #b8960c, #d4af37)'
                      : '#fff',
                    color: tier.highlighted ? '#fff' : '#1a1a1a',
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    transition: 'all 0.2s',
                    opacity: isLoading ? 0.7 : 1,
                  }}
                  onMouseEnter={(e) => {
                    if (!tier.highlighted) {
                      (e.currentTarget as HTMLButtonElement).style.background = '#faf9f7';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!tier.highlighted) {
                      (e.currentTarget as HTMLButtonElement).style.background = '#fff';
                    }
                  }}
                >
                  {isLoading ? 'Redirecting...' : 'Start Free Trial'}
                  {!isLoading && <ArrowRight size={14} />}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {error && (
        <div style={{
          maxWidth: 500,
          margin: '-40px auto 40px',
          padding: '14px 20px',
          borderRadius: 12,
          background: error.includes('Coming soon') ? '#fdf8eb' : '#fef2f2',
          border: error.includes('Coming soon') ? '1px solid #fde68a' : '1px solid #fecaca',
          fontSize: 13,
          color: error.includes('Coming soon') ? '#92400e' : '#dc2626',
          textAlign: 'center',
        }}>
          {error}
        </div>
      )}

      {/* FAQ Section */}
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', textAlign: 'center', marginBottom: 24 }}>
          Frequently asked questions
        </h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {FAQS.map((faq, i) => {
            const isOpen = openFaq === i;
            return (
              <div
                key={i}
                style={{
                  background: '#fff',
                  borderRadius: 12,
                  border: '1px solid #ece8e0',
                  overflow: 'hidden',
                }}
              >
                <button
                  onClick={() => setOpenFaq(isOpen ? null : i)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '16px 20px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', lineHeight: 1.4 }}>
                    {faq.q}
                  </span>
                  {isOpen
                    ? <ChevronUp size={16} style={{ color: '#999', flexShrink: 0, marginLeft: 12 }} />
                    : <ChevronDown size={16} style={{ color: '#999', flexShrink: 0, marginLeft: 12 }} />
                  }
                </button>
                {isOpen && (
                  <div style={{
                    padding: '0 20px 16px',
                    fontSize: 13,
                    color: '#666',
                    lineHeight: 1.7,
                  }}>
                    {faq.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
