'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { Building2, Save, Loader2, CheckCircle, MapPin, Phone, Mail, Globe, User, Calendar, Palette, Target, Sparkles, FileText } from 'lucide-react';

const PROFILE_API = `${API}/socialforge/profile`;

interface ProfileData {
  business_name: string;
  tagline: string;
  phone: string;
  email: string;
  website: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  bio_short: string;
  bio_long: string;
  services: string;
  target_audience: string;
  style_keywords: string;
  brand_colors: string;
  logo_url: string;
  owner_name: string;
  founded_year: string;
  service_area: string;
}

const FIELD_CONFIG: { key: keyof ProfileData; label: string; icon: any; type: 'text' | 'textarea'; group: string; placeholder: string }[] = [
  { key: 'business_name', label: 'Business Name', icon: Building2, type: 'text', group: 'basics', placeholder: "RG's Drapery & Upholstery" },
  { key: 'owner_name', label: 'Owner Name', icon: User, type: 'text', group: 'basics', placeholder: 'Your name' },
  { key: 'tagline', label: 'Tagline', icon: Sparkles, type: 'text', group: 'basics', placeholder: 'Premium Custom Window Treatments' },
  { key: 'founded_year', label: 'Founded Year', icon: Calendar, type: 'text', group: 'basics', placeholder: '2024' },
  { key: 'phone', label: 'Phone', icon: Phone, type: 'text', group: 'contact', placeholder: '(202) 555-0100' },
  { key: 'email', label: 'Email', icon: Mail, type: 'text', group: 'contact', placeholder: 'info@yourbusiness.com' },
  { key: 'website', label: 'Website', icon: Globe, type: 'text', group: 'contact', placeholder: 'https://studio.empirebox.store' },
  { key: 'address', label: 'Street Address', icon: MapPin, type: 'text', group: 'location', placeholder: '123 Main St' },
  { key: 'city', label: 'City', icon: MapPin, type: 'text', group: 'location', placeholder: 'Washington' },
  { key: 'state', label: 'State', icon: MapPin, type: 'text', group: 'location', placeholder: 'DC' },
  { key: 'zip', label: 'ZIP Code', icon: MapPin, type: 'text', group: 'location', placeholder: '20001' },
  { key: 'service_area', label: 'Service Area', icon: MapPin, type: 'text', group: 'location', placeholder: 'Washington DC, Northern Virginia, Maryland' },
  { key: 'bio_short', label: 'Short Bio', icon: FileText, type: 'textarea', group: 'branding', placeholder: 'One-liner for social media profiles...' },
  { key: 'bio_long', label: 'Full Bio', icon: FileText, type: 'textarea', group: 'branding', placeholder: 'Detailed business description for websites and directories...' },
  { key: 'services', label: 'Services', icon: Target, type: 'text', group: 'branding', placeholder: 'Custom Drapery, Shades, Blinds, Upholstery' },
  { key: 'target_audience', label: 'Target Audience', icon: Target, type: 'text', group: 'branding', placeholder: 'Homeowners, Interior Designers' },
  { key: 'style_keywords', label: 'Style Keywords', icon: Sparkles, type: 'text', group: 'branding', placeholder: 'Premium, Custom, Luxury, Handcrafted' },
  { key: 'brand_colors', label: 'Brand Colors', icon: Palette, type: 'text', group: 'branding', placeholder: '#c9a84c, #1a1a1a, #faf9f7' },
  { key: 'logo_url', label: 'Logo URL', icon: Globe, type: 'text', group: 'branding', placeholder: 'https://...' },
];

const GROUPS = [
  { id: 'basics', label: 'Business Basics' },
  { id: 'contact', label: 'Contact Info' },
  { id: 'location', label: 'Location & Service Area' },
  { id: 'branding', label: 'Branding & Description' },
];

export default function BusinessProfileScreen() {
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [formData, setFormData] = useState<Partial<ProfileData>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    fetch(PROFILE_API)
      .then(r => r.json())
      .then(data => {
        setProfile(data);
        setFormData(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleChange = (key: keyof ProfileData, value: string) => {
    setFormData(prev => ({ ...prev, [key]: value }));
    setDirty(true);
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(PROFILE_API, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const updated = await res.json();
      setProfile(updated);
      setFormData(updated);
      setDirty(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save profile:', err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ background: '#f5f2ed' }}>
        <Loader2 size={24} className="animate-spin text-[#b8960c]" />
      </div>
    );
  }

  const filled = FIELD_CONFIG.filter(f => formData[f.key]?.trim()).length;
  const total = FIELD_CONFIG.length;
  const pct = Math.round((filled / total) * 100);

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <Building2 size={20} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Business Profile</h1>
            <p style={{ fontSize: 12, color: '#888', margin: 0 }}>
              Used by SocialForge, LuxeForge, quotes, invoices, and AI agents
            </p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saving || !dirty}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-white font-semibold text-sm transition-all"
          style={{
            background: saved ? '#16a34a' : dirty ? 'linear-gradient(135deg, #b8960c, #d4af37)' : '#ccc',
            cursor: dirty ? 'pointer' : 'default',
            boxShadow: dirty ? '0 4px 12px rgba(184,150,12,0.3)' : 'none',
          }}
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : saved ? <CheckCircle size={16} /> : <Save size={16} />}
          {saving ? 'Saving...' : saved ? 'Saved' : 'Save Profile'}
        </button>
      </div>

      {/* Completion bar */}
      <div className="mb-6 p-4 rounded-xl" style={{ background: 'white', border: '1px solid #e8e4de' }}>
        <div className="flex items-center justify-between mb-2">
          <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>Profile Completion</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: pct === 100 ? '#16a34a' : '#b8960c' }}>{pct}%</span>
        </div>
        <div className="w-full h-2 rounded-full" style={{ background: '#f0ece6' }}>
          <div className="h-2 rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: pct === 100 ? '#16a34a' : 'linear-gradient(90deg, #b8960c, #d4af37)' }} />
        </div>
        <p style={{ fontSize: 11, color: '#999', marginTop: 6 }}>{filled} of {total} fields filled — complete your profile so AI agents can generate accurate content for all platforms</p>
      </div>

      {/* Form groups */}
      <div style={{ maxWidth: 700 }} className="space-y-6 pb-12">
        {GROUPS.map(group => (
          <div key={group.id} className="rounded-xl overflow-hidden" style={{ background: 'white', border: '1px solid #e8e4de' }}>
            <div className="px-5 py-3" style={{ background: '#faf8f4', borderBottom: '1px solid #e8e4de' }}>
              <h2 style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>{group.label}</h2>
            </div>
            <div className="p-5 space-y-4">
              {FIELD_CONFIG.filter(f => f.group === group.id).map(field => {
                const Icon = field.icon;
                return (
                  <div key={field.key}>
                    <label className="flex items-center gap-2 mb-1.5" style={{ fontSize: 12, fontWeight: 500, color: '#666' }}>
                      <Icon size={14} className="text-[#b8960c]" />
                      {field.label}
                    </label>
                    {field.type === 'textarea' ? (
                      <textarea
                        value={formData[field.key] || ''}
                        onChange={e => handleChange(field.key, e.target.value)}
                        placeholder={field.placeholder}
                        rows={field.key === 'bio_long' ? 4 : 2}
                        className="w-full px-3 py-2 rounded-lg text-sm resize-none"
                        style={{ border: '1px solid #e0dcd6', background: '#faf9f7', color: '#1a1a1a', outline: 'none' }}
                        onFocus={e => e.target.style.borderColor = '#b8960c'}
                        onBlur={e => e.target.style.borderColor = '#e0dcd6'}
                      />
                    ) : (
                      <input
                        type="text"
                        value={formData[field.key] || ''}
                        onChange={e => handleChange(field.key, e.target.value)}
                        placeholder={field.placeholder}
                        className="w-full px-3 py-2 rounded-lg text-sm"
                        style={{ border: '1px solid #e0dcd6', background: '#faf9f7', color: '#1a1a1a', outline: 'none', height: 40 }}
                        onFocus={e => e.target.style.borderColor = '#b8960c'}
                        onBlur={e => e.target.style.borderColor = '#e0dcd6'}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
