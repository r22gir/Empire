'use client';
import { useEffect, useState } from 'react';
import { Check, Sparkles, ArrowRight, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import { businessopsCheckout, businessopsInfo, businessopsSignup, type SellablePackageId } from '../../lib/api';
import { isPublicSignupEnabled } from '../../lib/businessopsSignup';

const TIERS: Array<{
  id: SellablePackageId;
  name: string;
  monthlyPrice: number;
  annualPrice: number;
  description: string;
  features: string[];
  highlighted: boolean;
}> = [
  {
    id: 'pkg_starter',
    name: 'Starter',
    monthlyPrice: 29,
    annualPrice: 24,
    description: 'Workroom + WoodCraft core + ForgeCRM. The entry tier for solo operators.',
    features: [
      '1 business workspace',
      'MAX chat (standard)',
      'Quote & invoice management',
      'Email support',
    ],
    highlighted: false,
  },
  {
    id: 'pkg_growth',
    name: 'Growth',
    monthlyPrice: 79,
    annualPrice: 66,
    description: 'Starter + Drawing Studio + SocialForge + LeadForge + MarketForge.',
    features: [
      'Everything in Starter',
      'Drawing Studio + SocialForge',
      'LeadForge + MarketForge',
      'Priority support',
    ],
    highlighted: true,
  },
  {
    id: 'pkg_empire',
    name: 'Empire',
    monthlyPrice: 199,
    annualPrice: 166,
    description: 'Growth + ApostApp + VendorOps + SupportForge + ArchiveForge.',
    features: [
      'Everything in Growth',
      'ApostApp (Founder-handled)',
      'VendorOps + SupportForge',
      'Dedicated support',
    ],
    highlighted: false,
  },
  {
    id: 'pkg_apostille_only',
    name: 'Apostille-only',
    monthlyPrice: 49,
    annualPrice: 41,
    description: 'ApostApp + VendorOps only. The DMV market entry tier.',
    features: [
      'Apostille intake + status',
      'VendorOps notary routing',
      'Founder-handled fulfillment',
      'Email updates',
    ],
    highlighted: false,
  },
];

const FAQS = [
  {
    q: 'How does the free trial work?',
    a: 'Every plan starts with a 14-day free trial. Stripe TEST / sandbox checkout is used in this environment — live charges are disabled.',
  },
  {
    q: 'Can I switch plans later?',
    a: 'Yes. You can upgrade or downgrade at any time. When upgrading, you get immediate access to new features. When downgrading, changes take effect at the end of your current billing cycle.',
  },
  {
    q: 'What happens to my data if I cancel?',
    a: 'Your data is retained for 30 days after cancellation. You can export everything at any time. We never delete your data without notice. Tenant isolation keeps other businesses off your records.',
  },
  {
    q: 'Is there a discount for annual billing?',
    a: 'Yes. Annual billing saves you 2 months — that is roughly 17% off the monthly price. You can switch between monthly and annual billing at any time.',
  },
  {
    q: 'Is the Founder package for sale?',
    a: 'No. Founder / Internal ($0) is never sold. It is the operator workspace only.',
  },
  {
    q: 'Do you offer custom enterprise plans?',
    a: 'Yes. For teams with 10+ users or specialized needs, contact us for custom pricing, SLAs, and dedicated onboarding. Email support@empirebox.store.',
  },
];

type SignupDraft = {
  email: string;
  password: string;
  display_name: string;
  business_name: string;
};

export default function PricingPage() {
  const [annual, setAnnual] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [pendingPackage, setPendingPackage] = useState<SellablePackageId | null>(null);
  const [signupOpen, setSignupOpen] = useState(false);
  const [draft, setDraft] = useState<SignupDraft>({
    email: '',
    password: '',
    display_name: '',
    business_name: '',
  });

  useEffect(() => {
    let cancelled = false;
    businessopsInfo()
      .then((info) => {
        if (!cancelled) setSignupOpen(isPublicSignupEnabled(info));
      })
      .catch(() => {
        if (!cancelled) setSignupOpen(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const startBuy = (packageId: SellablePackageId) => {
    if (!signupOpen) return;
    setError(null);
    setPendingPackage(packageId);
  };

  const handleCheckout = async () => {
    if (!signupOpen || !pendingPackage) return;
    setLoading(pendingPackage);
    setError(null);
    try {
      const signup = await businessopsSignup({
        ...draft,
        package_id: pendingPackage,
      });
      if (typeof window !== 'undefined') {
        localStorage.setItem('empire_tenant_id', signup.tenant.id);
        localStorage.setItem('empire_business_id', signup.business.id);
        if (signup.access_token) localStorage.setItem('empire_access_token', signup.access_token);
      }
      const data = await businessopsCheckout({
        business_id: signup.business.id,
        tenant_id: signup.tenant.id,
        package_id: pendingPackage,
        customer_email: draft.email,
        interval: annual ? 'year' : 'month',
        success_url: window.location.origin + '/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url: window.location.href,
      });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
        return;
      }
      setError('No checkout URL returned. Please try again.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      setError(message);
    }
    setLoading(null);
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto', background: '#f5f3ef', padding: '48px 24px 80px' }}>
      <div style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto 40px' }}>
        <h1 style={{ fontSize: 32, fontWeight: 700, color: '#1a1a1a', margin: '0 0 12px', lineHeight: 1.2 }}>
          Simple, transparent pricing
        </h1>
        <p style={{ fontSize: 16, color: '#777', margin: 0, lineHeight: 1.6 }}>
          Starter $29, Growth $79, Empire $199, Apostille-only $49. Stripe TEST / sandbox only.
        </p>
        {!signupOpen && (
          <div
            data-testid="signup-coming-soon"
            style={{
              margin: '24px auto 0',
              maxWidth: 480,
              padding: '16px 20px',
              borderRadius: 14,
              background: '#fdf8eb',
              border: '1px solid #f0e2b3',
              color: '#7a5d0b',
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
              textAlign: 'left',
            }}
          >
            <Clock size={18} style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '0.02em', marginBottom: 4 }}>
                Coming soon
              </div>
              <div style={{ fontSize: 13, lineHeight: 1.55, color: '#8a7018' }}>
                Public signup opens at launch. Preview the plans below — we are not taking
                self-serve workspaces yet.
              </div>
            </div>
          </div>
        )}
      </div>

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

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: 20,
        maxWidth: 1120,
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
                position: 'relative',
                overflow: 'hidden',
                boxShadow: tier.highlighted
                  ? '0 8px 32px rgba(184,150,12,0.15)'
                  : '0 2px 8px rgba(0,0,0,0.04)',
                transition: 'box-shadow 0.2s',
              }}
            >
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
                <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: '0 0 6px' }}>
                  {tier.name}
                </h2>
                <p style={{ fontSize: 13, color: '#999', margin: '0 0 20px', lineHeight: 1.5 }}>
                  {tier.description}
                </p>

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

                <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px' }}>
                  {tier.features.map((f, i) => (
                    <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12 }}>
                      <Check size={16} style={{ color: '#b8960c', marginTop: 1, flexShrink: 0 }} />
                      <span style={{ fontSize: 13, color: '#555', lineHeight: 1.4 }}>{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => startBuy(tier.id)}
                  disabled={!signupOpen || isLoading}
                  data-testid={`buy-${tier.id}`}
                  style={{
                    width: '100%',
                    padding: '12px 0',
                    borderRadius: 10,
                    border: signupOpen
                      ? (tier.highlighted ? 'none' : '1px solid #ece8e0')
                      : '1px solid #ece8e0',
                    background: signupOpen
                      ? (tier.highlighted
                        ? 'linear-gradient(135deg, #b8960c, #d4af37)'
                        : '#fff')
                      : '#f7f4ee',
                    color: signupOpen
                      ? (tier.highlighted ? '#fff' : '#1a1a1a')
                      : '#9a8f78',
                    fontSize: 14,
                    fontWeight: 700,
                    cursor: signupOpen && !isLoading ? 'pointer' : 'not-allowed',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8,
                    transition: 'all 0.2s',
                    opacity: isLoading ? 0.7 : 1,
                  }}
                >
                  {!signupOpen ? 'Coming soon' : isLoading ? 'Redirecting...' : 'Buy'}
                  {signupOpen && !isLoading && <ArrowRight size={14} />}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {signupOpen && pendingPackage && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
            zIndex: 40,
          }}
        >
          <div style={{ background: '#fff', borderRadius: 16, width: '100%', maxWidth: 420, padding: 24 }}>
            <h3 style={{ margin: '0 0 8px', fontSize: 18 }}>Create your workspace</h3>
            <p style={{ margin: '0 0 16px', fontSize: 13, color: '#777' }}>
              Self-serve signup, then Stripe TEST checkout for{' '}
              {TIERS.find((t) => t.id === pendingPackage)?.name}.
            </p>
            {(['display_name', 'business_name', 'email', 'password'] as const).map((field) => (
              <label key={field} style={{ display: 'block', marginBottom: 10, fontSize: 12, color: '#555' }}>
                {field.replace('_', ' ')}
                <input
                  type={field === 'password' ? 'password' : field === 'email' ? 'email' : 'text'}
                  value={draft[field]}
                  onChange={(e) => setDraft({ ...draft, [field]: e.target.value })}
                  style={{
                    width: '100%',
                    marginTop: 4,
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #ece8e0',
                    fontSize: 14,
                  }}
                />
              </label>
            ))}
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button
                onClick={() => setPendingPackage(null)}
                style={{ flex: 1, padding: 12, borderRadius: 10, border: '1px solid #ece8e0', background: '#fff', fontWeight: 600 }}
              >
                Cancel
              </button>
              <button
                onClick={handleCheckout}
                disabled={!!loading}
                style={{
                  flex: 1,
                  padding: 12,
                  borderRadius: 10,
                  border: 'none',
                  background: '#b8960c',
                  color: '#fff',
                  fontWeight: 700,
                }}
              >
                {loading ? 'Redirecting...' : 'Buy'}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div style={{
          maxWidth: 500,
          margin: '-40px auto 40px',
          padding: '14px 20px',
          borderRadius: 12,
          background: error.includes('not configured') ? '#fdf8eb' : '#fef2f2',
          border: error.includes('not configured') ? '1px solid #fde68a' : '1px solid #fecaca',
          fontSize: 13,
          color: error.includes('not configured') ? '#92400e' : '#dc2626',
          textAlign: 'center',
        }}>
          {error}
        </div>
      )}

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
