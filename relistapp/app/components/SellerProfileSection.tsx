'use client';

import { useState, useEffect } from 'react';
import {
  UserCircle, Store, MapPin, Phone, Mail, Globe, CreditCard, Truck,
  FileText, Camera, Check, AlertCircle, ChevronDown, ChevronUp,
  Copy, ExternalLink, Shield, Sparkles, Save, CheckCircle2,
} from 'lucide-react';
import { PLATFORM_COLORS } from '../lib/mock-data';

interface SellerProfile {
  // Identity
  business_name: string;
  display_name: string;
  full_name: string;
  email: string;
  phone: string;
  website: string;
  logo_url: string;
  // Business
  business_type: 'individual' | 'llc' | 'corporation' | 'sole_prop';
  ein_tax_id: string;
  state_tax_id: string;
  business_license: string;
  // Address
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip: string;
  country: string;
  // Shipping
  ship_from_address: string;
  ship_from_city: string;
  ship_from_state: string;
  ship_from_zip: string;
  default_carrier: string;
  handling_time_days: number;
  free_shipping_threshold: number;
  // Return policy
  return_policy: 'no_returns' | '14_days' | '30_days' | '60_days';
  return_shipping_paid_by: 'buyer' | 'seller';
  // Financials
  bank_name: string;
  bank_routing: string;
  bank_account: string;
  paypal_email: string;
  // Platform-specific
  ebay_store_name: string;
  ebay_store_category: string;
  etsy_shop_name: string;
  etsy_shop_section: string;
  shopify_store_url: string;
  amazon_seller_name: string;
  // Listing defaults
  default_condition: string;
  default_category: string;
  default_description_footer: string;
  default_tags: string;
  // About
  seller_bio: string;
  years_selling: number;
}

const DEFAULT_PROFILE: SellerProfile = {
  business_name: '', display_name: '', full_name: '', email: '', phone: '', website: '', logo_url: '',
  business_type: 'individual', ein_tax_id: '', state_tax_id: '', business_license: '',
  address_line1: '', address_line2: '', city: '', state: '', zip: '', country: 'US',
  ship_from_address: '', ship_from_city: '', ship_from_state: '', ship_from_zip: '',
  default_carrier: 'usps', handling_time_days: 1, free_shipping_threshold: 0,
  return_policy: '30_days', return_shipping_paid_by: 'buyer',
  bank_name: '', bank_routing: '', bank_account: '', paypal_email: '',
  ebay_store_name: '', ebay_store_category: 'Clothing, Shoes & Accessories',
  etsy_shop_name: '', etsy_shop_section: '',
  shopify_store_url: '', amazon_seller_name: '',
  default_condition: 'good', default_category: 'Clothing', default_description_footer: '', default_tags: '',
  seller_bio: '', years_selling: 0,
};

const PLATFORMS_FIELDS: { platform: string; color: string; fields: { key: keyof SellerProfile; label: string; auto_from?: keyof SellerProfile; placeholder?: string }[] }[] = [
  {
    platform: 'eBay', color: PLATFORM_COLORS.ebay,
    fields: [
      { key: 'ebay_store_name', label: 'eBay Store Name', auto_from: 'display_name', placeholder: 'Your eBay store name' },
      { key: 'ebay_store_category', label: 'Primary Store Category', placeholder: 'e.g. Clothing, Shoes & Accessories' },
    ],
  },
  {
    platform: 'Etsy', color: PLATFORM_COLORS.etsy,
    fields: [
      { key: 'etsy_shop_name', label: 'Etsy Shop Name', auto_from: 'display_name', placeholder: 'Your Etsy shop name' },
      { key: 'etsy_shop_section', label: 'Default Shop Section', placeholder: 'e.g. Vintage Clothing' },
    ],
  },
  {
    platform: 'Shopify', color: PLATFORM_COLORS.shopify,
    fields: [
      { key: 'shopify_store_url', label: 'Shopify Store URL', auto_from: 'website', placeholder: 'yourstore.myshopify.com' },
    ],
  },
  {
    platform: 'Amazon', color: PLATFORM_COLORS.amazon,
    fields: [
      { key: 'amazon_seller_name', label: 'Amazon Seller Name', auto_from: 'business_name', placeholder: 'Your Amazon seller display name' },
    ],
  },
];

const SECTION_CONFIG = [
  { id: 'identity', label: 'Business Identity', icon: Store, description: 'Your business name, contact info, and branding' },
  { id: 'address', label: 'Address & Location', icon: MapPin, description: 'Business and shipping addresses' },
  { id: 'shipping', label: 'Shipping & Returns', icon: Truck, description: 'Default shipping settings and return policy' },
  { id: 'financial', label: 'Payment & Banking', icon: CreditCard, description: 'Payment accounts for platform payouts' },
  { id: 'platforms', label: 'Platform Profiles', icon: Globe, description: 'Platform-specific store names and settings' },
  { id: 'defaults', label: 'Listing Defaults', icon: FileText, description: 'Default values auto-filled on new listings' },
];

export default function SellerProfileSection() {
  const [profile, setProfile] = useState<SellerProfile>(DEFAULT_PROFILE);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ identity: true });
  const [saved, setSaved] = useState(false);
  const [completeness, setCompleteness] = useState(0);

  // Load from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('relistapp_seller_profile');
    if (stored) {
      try { setProfile({ ...DEFAULT_PROFILE, ...JSON.parse(stored) }); } catch {}
    }
  }, []);

  // Calculate completeness
  useEffect(() => {
    const required: (keyof SellerProfile)[] = [
      'business_name', 'display_name', 'full_name', 'email', 'phone',
      'address_line1', 'city', 'state', 'zip',
      'ship_from_zip', 'default_carrier',
      'return_policy',
    ];
    const filled = required.filter(k => profile[k] && String(profile[k]).trim() !== '');
    setCompleteness(Math.round((filled.length / required.length) * 100));
  }, [profile]);

  const update = (key: keyof SellerProfile, val: any) => {
    setProfile(p => ({ ...p, [key]: val }));
    setSaved(false);
  };

  const save = () => {
    localStorage.setItem('relistapp_seller_profile', JSON.stringify(profile));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const autoFillShipping = () => {
    setProfile(p => ({
      ...p,
      ship_from_address: p.address_line1,
      ship_from_city: p.city,
      ship_from_state: p.state,
      ship_from_zip: p.zip,
    }));
  };

  const autoFillPlatforms = () => {
    setProfile(p => ({
      ...p,
      ebay_store_name: p.ebay_store_name || p.display_name || p.business_name,
      etsy_shop_name: p.etsy_shop_name || p.display_name?.replace(/\s+/g, '') || '',
      shopify_store_url: p.shopify_store_url || p.website || '',
      amazon_seller_name: p.amazon_seller_name || p.business_name || p.display_name,
      paypal_email: p.paypal_email || p.email,
    }));
  };

  const toggle = (id: string) => setExpanded(e => ({ ...e, [id]: !e[id] }));

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: '#ecfeff' }}>
            <UserCircle size={24} style={{ color: '#06b6d4' }} />
          </div>
          <div>
            <h1 className="text-xl font-bold">Seller Profile</h1>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Fill once — auto-populates all platform sign-ups
            </p>
          </div>
        </div>
        <button onClick={save} className="btn-primary" style={{ minWidth: 130 }}>
          {saved ? <><CheckCircle2 size={15} /> Saved!</> : <><Save size={15} /> Save Profile</>}
        </button>
      </div>

      {/* Completeness Bar */}
      <div className="empire-card" style={{ padding: '14px 18px' }}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Shield size={14} style={{ color: completeness === 100 ? '#16a34a' : '#d97706' }} />
            <span className="text-sm font-semibold">Profile Completeness</span>
          </div>
          <span className="text-sm font-bold" style={{ color: completeness === 100 ? '#16a34a' : '#d97706' }}>
            {completeness}%
          </span>
        </div>
        <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${completeness}%`,
              background: completeness === 100 ? '#16a34a' : completeness > 60 ? '#06b6d4' : '#d97706',
            }}
          />
        </div>
        <p className="text-xs mt-2" style={{ color: 'var(--muted)' }}>
          {completeness === 100
            ? 'Profile complete! Ready to auto-fill platform sign-ups.'
            : 'Complete your profile to auto-fill all platform registrations.'}
        </p>
      </div>

      {/* Auto-fill Banner */}
      <div className="empire-card flex items-center gap-3" style={{ background: '#f0fdfa', borderColor: '#99f6e4', padding: '12px 16px' }}>
        <Sparkles size={18} style={{ color: '#06b6d4' }} />
        <div className="flex-1">
          <div className="text-sm font-semibold" style={{ color: '#0d9488' }}>Auto-Fill Magic</div>
          <div className="text-xs" style={{ color: '#5eead4' }}>Your profile data auto-populates when connecting to eBay, Etsy, Shopify, and other platforms. Fill it once, connect everywhere.</div>
        </div>
        <button onClick={autoFillPlatforms} className="btn-secondary text-xs" style={{ whiteSpace: 'nowrap' }}>
          <Sparkles size={12} /> Auto-Fill Platforms
        </button>
      </div>

      {/* ── IDENTITY SECTION ── */}
      <AccordionSection
        id="identity" config={SECTION_CONFIG[0]} expanded={expanded} toggle={toggle}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="Business Name *" value={profile.business_name} onChange={v => update('business_name', v)} placeholder="Empire Resells LLC" />
          <Field label="Display Name *" value={profile.display_name} onChange={v => update('display_name', v)} placeholder="EmpireResells" hint="Used as default store name across platforms" />
          <Field label="Full Legal Name *" value={profile.full_name} onChange={v => update('full_name', v)} placeholder="Your full legal name" />
          <div>
            <label className="field-label">Business Type *</label>
            <select className="form-input" value={profile.business_type} onChange={e => update('business_type', e.target.value)}>
              <option value="individual">Individual / Sole Proprietor</option>
              <option value="sole_prop">Sole Proprietorship</option>
              <option value="llc">LLC</option>
              <option value="corporation">Corporation</option>
            </select>
          </div>
          <Field label="Email *" value={profile.email} onChange={v => update('email', v)} placeholder="you@example.com" type="email" />
          <Field label="Phone *" value={profile.phone} onChange={v => update('phone', v)} placeholder="(555) 123-4567" type="tel" />
          <Field label="Website" value={profile.website} onChange={v => update('website', v)} placeholder="https://yourstore.com" />
          <div>
            <label className="field-label">EIN / Tax ID</label>
            <input className="form-input" type="password" value={profile.ein_tax_id} onChange={e => update('ein_tax_id', e.target.value)} placeholder="XX-XXXXXXX" />
            <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Required for eBay & Amazon business accounts</p>
          </div>
        </div>
        <div className="mt-4">
          <Field label="Seller Bio" value={profile.seller_bio} onChange={v => update('seller_bio', v)} placeholder="Tell buyers about your shop, experience, and what makes you unique..." multiline />
          <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>Used in Etsy About section, eBay seller info, and Shopify About page</p>
        </div>
      </AccordionSection>

      {/* ── ADDRESS SECTION ── */}
      <AccordionSection
        id="address" config={SECTION_CONFIG[1]} expanded={expanded} toggle={toggle}
      >
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Field label="Address Line 1 *" value={profile.address_line1} onChange={v => update('address_line1', v)} placeholder="123 Main Street" />
          </div>
          <Field label="Address Line 2" value={profile.address_line2} onChange={v => update('address_line2', v)} placeholder="Suite 100" />
          <Field label="City *" value={profile.city} onChange={v => update('city', v)} placeholder="City" />
          <Field label="State *" value={profile.state} onChange={v => update('state', v)} placeholder="CA" />
          <Field label="ZIP Code *" value={profile.zip} onChange={v => update('zip', v)} placeholder="90210" />
        </div>

        <div className="mt-5 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold">Ship-From Address</span>
            <button onClick={autoFillShipping} className="text-xs font-semibold px-3 py-1 rounded-lg transition-all cursor-pointer" style={{ background: '#ecfeff', color: '#06b6d4', border: '1px solid #cffafe' }}>
              <Copy size={11} className="inline mr-1" /> Same as above
            </button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Ship-From Address" value={profile.ship_from_address} onChange={v => update('ship_from_address', v)} placeholder="123 Main Street" />
            <Field label="City" value={profile.ship_from_city} onChange={v => update('ship_from_city', v)} placeholder="City" />
            <Field label="State" value={profile.ship_from_state} onChange={v => update('ship_from_state', v)} placeholder="CA" />
            <Field label="Ship-From ZIP *" value={profile.ship_from_zip} onChange={v => update('ship_from_zip', v)} placeholder="90210" hint="Required for shipping rate calculations on all platforms" />
          </div>
        </div>
      </AccordionSection>

      {/* ── SHIPPING & RETURNS ── */}
      <AccordionSection
        id="shipping" config={SECTION_CONFIG[2]} expanded={expanded} toggle={toggle}
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="field-label">Default Carrier *</label>
            <select className="form-input" value={profile.default_carrier} onChange={e => update('default_carrier', e.target.value)}>
              <option value="usps">USPS</option>
              <option value="ups">UPS</option>
              <option value="fedex">FedEx</option>
              <option value="dhl">DHL</option>
            </select>
          </div>
          <Field label="Handling Time (days)" value={String(profile.handling_time_days)} onChange={v => update('handling_time_days', parseInt(v) || 1)} placeholder="1" type="number" hint="How many business days to ship after sale" />
          <Field label="Free Shipping Threshold ($)" value={String(profile.free_shipping_threshold || '')} onChange={v => update('free_shipping_threshold', parseFloat(v) || 0)} placeholder="0 = no free shipping" type="number" />
          <div>
            <label className="field-label">Return Policy *</label>
            <select className="form-input" value={profile.return_policy} onChange={e => update('return_policy', e.target.value)}>
              <option value="no_returns">No Returns</option>
              <option value="14_days">14-Day Returns</option>
              <option value="30_days">30-Day Returns</option>
              <option value="60_days">60-Day Returns</option>
            </select>
          </div>
          <div>
            <label className="field-label">Return Shipping Paid By</label>
            <select className="form-input" value={profile.return_shipping_paid_by} onChange={e => update('return_shipping_paid_by', e.target.value)}>
              <option value="buyer">Buyer</option>
              <option value="seller">Seller</option>
            </select>
          </div>
        </div>

        {/* Platform-specific shipping info */}
        <div className="mt-4 p-3 rounded-lg" style={{ background: '#fffbeb', border: '1px solid #fef3c7' }}>
          <div className="text-xs font-semibold mb-1" style={{ color: '#d97706' }}>Platform Shipping Notes</div>
          <ul className="text-xs space-y-1" style={{ color: '#92400e' }}>
            <li><strong>eBay:</strong> Handling time, return policy, and carrier are set per-listing but default from here</li>
            <li><strong>Etsy:</strong> Shipping profiles are created from your carrier + handling time + ship-from ZIP</li>
            <li><strong>Shopify:</strong> Shipping zones configured from your address. Free shipping rules auto-applied.</li>
            <li><strong>Poshmark:</strong> Shipping is fixed ($7.97 Priority Mail). Your ZIP determines delivery estimates.</li>
          </ul>
        </div>
      </AccordionSection>

      {/* ── FINANCIAL ── */}
      <AccordionSection
        id="financial" config={SECTION_CONFIG[3]} expanded={expanded} toggle={toggle}
      >
        <div className="grid grid-cols-2 gap-4">
          <Field label="PayPal Email" value={profile.paypal_email} onChange={v => update('paypal_email', v)} placeholder="paypal@example.com" hint="Used for eBay payouts and Etsy deposits" />
          <Field label="Bank Name" value={profile.bank_name} onChange={v => update('bank_name', v)} placeholder="Bank of America" />
          <div>
            <label className="field-label">Routing Number</label>
            <input className="form-input" type="password" value={profile.bank_routing} onChange={e => update('bank_routing', e.target.value)} placeholder="XXXXXXXXX" />
          </div>
          <div>
            <label className="field-label">Account Number</label>
            <input className="form-input" type="password" value={profile.bank_account} onChange={e => update('bank_account', e.target.value)} placeholder="XXXXXXXXXXXX" />
          </div>
        </div>
        <div className="mt-3 p-3 rounded-lg flex items-start gap-2" style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
          <AlertCircle size={14} style={{ color: '#dc2626', marginTop: 2, flexShrink: 0 }} />
          <div className="text-xs" style={{ color: '#991b1b' }}>
            Banking info is stored locally on your device only. It's used to pre-fill platform payout setup forms. We never transmit this data — it stays on your machine.
          </div>
        </div>
      </AccordionSection>

      {/* ── PLATFORM PROFILES ── */}
      <AccordionSection
        id="platforms" config={SECTION_CONFIG[4]} expanded={expanded} toggle={toggle}
      >
        <div className="space-y-4">
          {PLATFORMS_FIELDS.map(pf => (
            <div key={pf.platform} className="p-4 rounded-xl" style={{ background: `${pf.color}08`, border: `1.5px solid ${pf.color}25` }}>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-md text-white text-xs font-bold flex items-center justify-center" style={{ background: pf.color }}>
                  {pf.platform[0]}
                </div>
                <span className="font-semibold text-sm">{pf.platform}</span>
                {pf.fields.every(f => profile[f.key] && String(profile[f.key]).trim() !== '') && (
                  <Check size={14} className="text-green-500" />
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                {pf.fields.map(f => (
                  <div key={f.key}>
                    <label className="field-label">{f.label}</label>
                    <div className="flex gap-1">
                      <input
                        className="form-input flex-1 text-sm"
                        value={String(profile[f.key] || '')}
                        onChange={e => update(f.key, e.target.value)}
                        placeholder={f.placeholder}
                      />
                      {f.auto_from && !profile[f.key] && profile[f.auto_from] && (
                        <button
                          onClick={() => update(f.key, profile[f.auto_from!])}
                          className="px-2 rounded-lg text-xs font-medium transition-all cursor-pointer"
                          style={{ background: '#ecfeff', color: '#06b6d4', border: '1px solid #cffafe', whiteSpace: 'nowrap' }}
                          title={`Auto-fill from ${String(f.auto_from)}`}
                        >
                          Auto
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex justify-end">
          <button onClick={autoFillPlatforms} className="btn-primary text-sm">
            <Sparkles size={14} /> Auto-Fill All From Profile
          </button>
        </div>
      </AccordionSection>

      {/* ── LISTING DEFAULTS ── */}
      <AccordionSection
        id="defaults" config={SECTION_CONFIG[5]} expanded={expanded} toggle={toggle}
      >
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="field-label">Default Condition</label>
            <select className="form-input" value={profile.default_condition} onChange={e => update('default_condition', e.target.value)}>
              <option value="new">New</option>
              <option value="like_new">Like New</option>
              <option value="good">Good</option>
              <option value="fair">Fair</option>
              <option value="poor">Poor</option>
            </select>
          </div>
          <div>
            <label className="field-label">Default Category</label>
            <select className="form-input" value={profile.default_category} onChange={e => update('default_category', e.target.value)}>
              {['Clothing', 'Electronics', 'Home', 'Books', 'Toys', 'Sports', 'Collectibles', 'Vintage', 'Jewelry', 'Other'].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <Field label="Default Tags" value={profile.default_tags} onChange={v => update('default_tags', v)} placeholder="vintage, thrift, resale" hint="Comma-separated. Applied to all new listings." />
          <Field label="Years Selling" value={String(profile.years_selling || '')} onChange={v => update('years_selling', parseInt(v) || 0)} placeholder="0" type="number" />
        </div>
        <div className="mt-3">
          <Field
            label="Listing Description Footer"
            value={profile.default_description_footer}
            onChange={v => update('default_description_footer', v)}
            placeholder="Thank you for shopping with us! We ship within 1 business day. Returns accepted within 30 days."
            multiline
            hint="Appended to the bottom of every listing description across all platforms"
          />
        </div>
      </AccordionSection>

      {/* Platform Sign-Up Guide */}
      <div className="empire-card" style={{ borderColor: '#99f6e4' }}>
        <div className="section-label mb-3">Platform Sign-Up Checklist</div>
        <p className="text-xs mb-4" style={{ color: 'var(--muted)' }}>
          When you click "Connect" on a platform, your profile data will be ready to paste. Here's what each platform requires:
        </p>
        <div className="grid grid-cols-2 gap-3">
          {[
            { name: 'eBay', color: PLATFORM_COLORS.ebay, needs: ['Business name', 'Address', 'Phone', 'Bank account or PayPal', 'Return policy', 'Tax ID (for business)'] },
            { name: 'Etsy', color: PLATFORM_COLORS.etsy, needs: ['Shop name', 'Email', 'Bank account', 'Address', 'Tax ID (for 200+ sales)', 'Shop bio'] },
            { name: 'Shopify', color: PLATFORM_COLORS.shopify, needs: ['Store name', 'Email', 'Address', 'Bank account', 'Business type'] },
            { name: 'Amazon', color: PLATFORM_COLORS.amazon, needs: ['Business name', 'Phone', 'Tax ID (required)', 'Bank account', 'Address', 'Credit card'] },
          ].map(p => (
            <div key={p.name} className="p-3 rounded-xl" style={{ background: '#f9fafb', border: '1px solid var(--border)' }}>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-5 h-5 rounded text-white text-xs font-bold flex items-center justify-center" style={{ background: p.color }}>
                  {p.name[0]}
                </div>
                <span className="text-sm font-semibold">{p.name}</span>
              </div>
              <ul className="space-y-1">
                {p.needs.map(n => {
                  const filled = checkFieldFilled(profile, n);
                  return (
                    <li key={n} className="flex items-center gap-1.5 text-xs">
                      {filled
                        ? <Check size={11} className="text-green-500 shrink-0" />
                        : <div className="w-[11px] h-[11px] rounded-full border-2 shrink-0" style={{ borderColor: '#ddd' }} />
                      }
                      <span style={{ color: filled ? 'var(--text-secondary)' : 'var(--muted)' }}>{n}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Helper: check if a requirement is filled based on profile
function checkFieldFilled(profile: SellerProfile, need: string): boolean {
  const map: Record<string, (keyof SellerProfile)[]> = {
    'Business name': ['business_name'],
    'Address': ['address_line1', 'city', 'state', 'zip'],
    'Phone': ['phone'],
    'Email': ['email'],
    'Bank account or PayPal': ['paypal_email', 'bank_account'],
    'Bank account': ['bank_account', 'paypal_email'],
    'Return policy': ['return_policy'],
    'Tax ID (for business)': ['ein_tax_id'],
    'Tax ID (required)': ['ein_tax_id'],
    'Tax ID (for 200+ sales)': ['ein_tax_id'],
    'Shop name': ['etsy_shop_name'],
    'Store name': ['shopify_store_url'],
    'Shop bio': ['seller_bio'],
    'Business type': ['business_type'],
    'Credit card': [],
  };
  const fields = map[need];
  if (!fields || fields.length === 0) return false;
  return fields.some(f => profile[f] && String(profile[f]).trim() !== '');
}

// Accordion section wrapper
function AccordionSection({ id, config, expanded, toggle, children }: {
  id: string;
  config: { label: string; icon: any; description: string };
  expanded: Record<string, boolean>;
  toggle: (id: string) => void;
  children: React.ReactNode;
}) {
  const Icon = config.icon;
  const isOpen = expanded[id];
  return (
    <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
      <button
        onClick={() => toggle(id)}
        className="w-full flex items-center gap-3 p-4 cursor-pointer transition-colors"
        style={{ background: isOpen ? '#fafffe' : 'transparent' }}
      >
        <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: '#ecfeff' }}>
          <Icon size={18} style={{ color: '#06b6d4' }} />
        </div>
        <div className="flex-1 text-left">
          <div className="text-sm font-semibold">{config.label}</div>
          <div className="text-xs" style={{ color: 'var(--muted)' }}>{config.description}</div>
        </div>
        {isOpen ? <ChevronUp size={16} style={{ color: 'var(--muted)' }} /> : <ChevronDown size={16} style={{ color: 'var(--muted)' }} />}
      </button>
      {isOpen && (
        <div className="px-4 pb-4" style={{ borderTop: '1px solid var(--border)' }}>
          <div className="pt-4">{children}</div>
        </div>
      )}
    </div>
  );
}

// Reusable field component
function Field({ label, value, onChange, placeholder, hint, type = 'text', multiline }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; hint?: string; type?: string; multiline?: boolean;
}) {
  return (
    <div>
      <label className="field-label">{label}</label>
      {multiline ? (
        <textarea
          className="form-input text-sm"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          rows={3}
          style={{ resize: 'vertical' }}
        />
      ) : (
        <input
          className="form-input text-sm"
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
        />
      )}
      {hint && <p className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{hint}</p>}
    </div>
  );
}
