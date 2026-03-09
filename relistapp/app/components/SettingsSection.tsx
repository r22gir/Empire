'use client';

import { useState } from 'react';
import { Save, Zap, Bell, Link2, Key, User, ToggleLeft, ToggleRight } from 'lucide-react';

export default function SettingsSection() {
  const [markup, setMarkup] = useState(35);
  const [defaultPlatforms, setDefaultPlatforms] = useState(['ebay', 'etsy']);
  const [aiAutoDescribe, setAiAutoDescribe] = useState(true);
  const [aiAutoPrice, setAiAutoPrice] = useState(true);
  const [notifyOnSale, setNotifyOnSale] = useState(true);
  const [notifyOnError, setNotifyOnError] = useState(true);
  const [notifyOnRelist, setNotifyOnRelist] = useState(false);

  const togglePlatform = (p: string) => {
    if (defaultPlatforms.includes(p)) {
      setDefaultPlatforms(defaultPlatforms.filter(x => x !== p));
    } else {
      setDefaultPlatforms([...defaultPlatforms, p]);
    }
  };

  const ToggleSwitch = ({ value, onChange, label }: { value: boolean; onChange: (v: boolean) => void; label: string }) => (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm">{label}</span>
      <button onClick={() => onChange(!value)}>
        {value ? (
          <ToggleRight size={28} style={{ color: '#06b6d4' }} />
        ) : (
          <ToggleLeft size={28} style={{ color: 'var(--muted)' }} />
        )}
      </button>
    </div>
  );

  const services = [
    { name: 'ShipForge', status: 'connected', port: 3007 },
    { name: 'SocialForge', status: 'connected', port: 3008 },
    { name: 'ForgeCRM', status: 'disconnected', port: 3010 },
    { name: 'Vision API (MAX)', status: 'connected', port: 8000 },
    { name: 'Empire Backend', status: 'connected', port: 8000 },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Settings</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Configure RelistApp preferences</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Pricing Defaults */}
        <div className="empire-card">
          <div className="flex items-center gap-2 mb-4">
            <Zap size={18} style={{ color: 'var(--gold)' }} />
            <h3 className="font-semibold">Pricing Defaults</h3>
          </div>

          <div className="space-y-3">
            <div>
              <label className="section-label">Default Markup %</label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={markup}
                  onChange={e => setMarkup(Number(e.target.value))}
                  className="flex-1 accent-cyan-500"
                />
                <span className="text-sm font-bold w-12 text-right">{markup}%</span>
              </div>
            </div>

            <div>
              <label className="section-label">Default Platforms for New Listings</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {['ebay', 'etsy', 'shopify', 'facebook', 'mercari', 'poshmark', 'amazon', 'depop'].map(p => (
                  <label
                    key={p}
                    className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border cursor-pointer"
                    style={{
                      borderColor: defaultPlatforms.includes(p) ? '#06b6d4' : 'var(--border)',
                      background: defaultPlatforms.includes(p) ? '#ecfeff' : 'transparent',
                    }}
                  >
                    <input
                      type="checkbox"
                      className="accent-cyan-500"
                      checked={defaultPlatforms.includes(p)}
                      onChange={() => togglePlatform(p)}
                    />
                    <span className="capitalize">{p}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* AI Features */}
        <div className="empire-card">
          <div className="flex items-center gap-2 mb-4">
            <Zap size={18} style={{ color: '#06b6d4' }} />
            <h3 className="font-semibold">AI Features</h3>
          </div>

          <div className="space-y-1">
            <ToggleSwitch value={aiAutoDescribe} onChange={setAiAutoDescribe} label="Auto-generate descriptions from photos" />
            <ToggleSwitch value={aiAutoPrice} onChange={setAiAutoPrice} label="AI price suggestions on new listings" />
          </div>

          <div className="mt-3 p-3 rounded-lg text-sm" style={{ background: 'var(--gold-light)' }}>
            <p style={{ color: 'var(--gold)' }}>AI features use MAX (Empire AI) via the backend API. Ensure the Empire backend is running on port 8000.</p>
          </div>
        </div>

        {/* Notifications */}
        <div className="empire-card">
          <div className="flex items-center gap-2 mb-4">
            <Bell size={18} style={{ color: 'var(--orange)' }} />
            <h3 className="font-semibold">Notifications</h3>
          </div>

          <div className="space-y-1">
            <ToggleSwitch value={notifyOnSale} onChange={setNotifyOnSale} label="Notify on sale" />
            <ToggleSwitch value={notifyOnError} onChange={setNotifyOnError} label="Notify on listing errors" />
            <ToggleSwitch value={notifyOnRelist} onChange={setNotifyOnRelist} label="Notify on auto-relist" />
          </div>
        </div>

        {/* Connected Services */}
        <div className="empire-card">
          <div className="flex items-center gap-2 mb-4">
            <Link2 size={18} style={{ color: 'var(--blue)' }} />
            <h3 className="font-semibold">Connected Services</h3>
          </div>

          <div className="space-y-2">
            {services.map(svc => (
              <div key={svc.name} className="flex items-center justify-between py-1.5">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ background: svc.status === 'connected' ? 'var(--green)' : 'var(--muted)' }}
                  />
                  <span className="text-sm font-medium">{svc.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: 'var(--muted)' }}>:{svc.port}</span>
                  <span
                    className={`status-pill ${svc.status === 'connected' ? 'active' : 'draft'}`}
                    style={{ fontSize: '11px' }}
                  >
                    {svc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* API Keys */}
        <div className="empire-card">
          <div className="flex items-center gap-2 mb-4">
            <Key size={18} style={{ color: 'var(--purple)' }} />
            <h3 className="font-semibold">API Keys</h3>
          </div>

          <div className="space-y-3">
            {['eBay API Key', 'Etsy API Key', 'Shopify API Key'].map(key => (
              <div key={key}>
                <label className="section-label">{key}</label>
                <input
                  type="password"
                  className="form-input text-sm"
                  placeholder="Enter API key..."
                  defaultValue="sk-****************************"
                />
              </div>
            ))}
          </div>

          <p className="text-xs mt-3" style={{ color: 'var(--muted)' }}>
            API keys are stored securely in the Empire backend. Changes require a restart.
          </p>
        </div>

        {/* Account Info */}
        <div className="empire-card">
          <div className="flex items-center gap-2 mb-4">
            <User size={18} style={{ color: 'var(--text-secondary)' }} />
            <h3 className="font-semibold">Account</h3>
          </div>

          <div className="space-y-3">
            <div>
              <label className="section-label">Business Name</label>
              <input type="text" className="form-input text-sm" defaultValue="Empire Resells" />
            </div>
            <div>
              <label className="section-label">Email</label>
              <input type="email" className="form-input text-sm" defaultValue="admin@empirebox.store" />
            </div>
            <div>
              <label className="section-label">Default Shipping Location</label>
              <input type="text" className="form-input text-sm" defaultValue="United States" />
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button className="btn-gold">
          <Save size={15} /> Save All Settings
        </button>
      </div>
    </div>
  );
}
