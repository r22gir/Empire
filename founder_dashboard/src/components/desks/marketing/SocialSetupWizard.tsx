'use client';
import { useState } from 'react';
import { Check, ChevronRight, ExternalLink, Copy, Eye, EyeOff, X } from 'lucide-react';

interface SocialPlatform {
  id: string;
  name: string;
  icon: string;
  color: string;
  steps: WizardStep[];
  connected: boolean;
}

interface WizardStep {
  title: string;
  description: string;
  action?: 'link' | 'input' | 'info';
  url?: string;
  inputLabel?: string;
  inputPlaceholder?: string;
  inputKey?: string;
}

const PLATFORMS: SocialPlatform[] = [
  {
    id: 'instagram', name: 'Instagram Business', icon: '📸', color: '#E1306C', connected: false,
    steps: [
      { title: 'Switch to Business Account', description: 'Open Instagram → Settings → Account → Switch to Professional Account → Choose Business.', action: 'link', url: 'https://www.instagram.com/' },
      { title: 'Connect Facebook Page', description: 'Link your Instagram Business account to a Facebook Page. This is required for API access and scheduling.', action: 'info' },
      { title: 'Save Account Handle', description: 'Enter your Instagram business handle so MAX can reference it.', action: 'input', inputLabel: 'Instagram Handle', inputPlaceholder: '@yourbusiness', inputKey: 'ig_handle' },
    ],
  },
  {
    id: 'facebook', name: 'Facebook Business', icon: '👤', color: '#1877F2', connected: false,
    steps: [
      { title: 'Create a Business Page', description: 'Go to Facebook → Create → Page. Choose "Business or Brand" and fill in your company details.', action: 'link', url: 'https://www.facebook.com/pages/create/' },
      { title: 'Set Up Meta Business Suite', description: 'Go to business.facebook.com to create a Business Manager account. This centralizes your ad accounts, pages, and team access.', action: 'link', url: 'https://business.facebook.com/' },
      { title: 'Save Page URL', description: 'Enter your Facebook page URL for reference.', action: 'input', inputLabel: 'Facebook Page URL', inputPlaceholder: 'https://facebook.com/yourbusiness', inputKey: 'fb_url' },
    ],
  },
  {
    id: 'tiktok', name: 'TikTok Business', icon: '🎵', color: '#000000', connected: false,
    steps: [
      { title: 'Create TikTok Business Account', description: 'Download TikTok → Sign up → Settings → Manage Account → Switch to Business Account.', action: 'link', url: 'https://www.tiktok.com/business/' },
      { title: 'Set Up TikTok Ads Manager', description: 'Go to ads.tiktok.com to create an ads account for boosted content and analytics.', action: 'link', url: 'https://ads.tiktok.com/' },
      { title: 'Save Account Handle', description: 'Enter your TikTok handle.', action: 'input', inputLabel: 'TikTok Handle', inputPlaceholder: '@yourbusiness', inputKey: 'tiktok_handle' },
    ],
  },
  {
    id: 'pinterest', name: 'Pinterest Business', icon: '📌', color: '#BD081C', connected: false,
    steps: [
      { title: 'Create Pinterest Business Account', description: 'Go to pinterest.com/business/create and create a free business account. This gives you analytics and ad tools.', action: 'link', url: 'https://www.pinterest.com/business/create/' },
      { title: 'Claim Your Website', description: 'In Settings → Claim, add your website URL. This adds your logo to all pins from your site and boosts SEO.', action: 'info' },
      { title: 'Create Boards', description: 'Create boards for: "Window Treatment Inspiration", "Before & After", "Fabric Collections", "Customer Projects". Pin at least 5 images each.', action: 'info' },
      { title: 'Save Profile URL', description: 'Enter your Pinterest profile URL.', action: 'input', inputLabel: 'Pinterest URL', inputPlaceholder: 'https://pinterest.com/yourbusiness', inputKey: 'pinterest_url' },
    ],
  },
  {
    id: 'google', name: 'Google Business Profile', icon: '🔍', color: '#4285F4', connected: false,
    steps: [
      { title: 'Create Google Business Profile', description: 'Go to business.google.com and claim or create your business listing. Add address, phone, hours, and photos.', action: 'link', url: 'https://business.google.com/' },
      { title: 'Add Photos & Services', description: 'Upload at least 10 project photos. Add all services: custom drapes, blinds, shades, shutters, motorization, installation.', action: 'info' },
      { title: 'Enable Messaging', description: 'Turn on messaging in your Google Business Profile so customers can reach you directly from Google Search and Maps.', action: 'info' },
      { title: 'Save Business Profile Link', description: 'Enter your Google Business Profile link.', action: 'input', inputLabel: 'Google Business URL', inputPlaceholder: 'https://g.page/yourbusiness', inputKey: 'google_url' },
    ],
  },
];

interface SocialSetupWizardProps {
  onClose: () => void;
}

export default function SocialSetupWizard({ onClose }: SocialSetupWizardProps) {
  const [platforms, setPlatforms] = useState(PLATFORMS);
  const [activePlatform, setActivePlatform] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [showInputs, setShowInputs] = useState<Record<string, boolean>>({});

  const platform = platforms.find(p => p.id === activePlatform);
  const step = platform?.steps[currentStep];

  const completeStep = () => {
    if (!platform) return;
    if (currentStep < platform.steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Mark platform as connected
      setPlatforms(prev => prev.map(p => p.id === platform.id ? { ...p, connected: true } : p));
      setActivePlatform(null);
      setCurrentStep(0);
    }
  };

  const connectedCount = platforms.filter(p => p.connected).length;

  // Platform list view
  if (!activePlatform) {
    return (
      <div className="rounded-xl overflow-hidden" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--gold)' }}>
              Social Media Setup
            </h3>
            <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {connectedCount}/{platforms.length} platforms configured
            </p>
          </div>
          <button onClick={onClose} className="p-1" style={{ color: 'var(--text-muted)' }}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Progress bar */}
        <div className="h-1" style={{ background: 'var(--elevated)' }}>
          <div className="h-full transition-all" style={{ width: `${(connectedCount / platforms.length) * 100}%`, background: 'var(--gold)' }} />
        </div>

        <div className="p-3 space-y-1.5">
          {platforms.map(p => (
            <button
              key={p.id}
              onClick={() => { setActivePlatform(p.id); setCurrentStep(0); }}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition text-left"
              style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = p.color; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; }}
            >
              <span className="text-lg">{p.icon}</span>
              <div className="flex-1">
                <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{p.name}</span>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{p.steps.length} steps</p>
              </div>
              {p.connected ? (
                <span className="flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>
                  <Check className="w-3 h-3" /> Done
                </span>
              ) : (
                <ChevronRight className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
              )}
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Wizard step view
  return (
    <div className="rounded-xl overflow-hidden" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: `2px solid ${platform!.color}` }}>
        <div className="flex items-center gap-2">
          <button onClick={() => { setActivePlatform(null); setCurrentStep(0); }}
            className="text-xs" style={{ color: 'var(--text-muted)' }}>
            ← Back
          </button>
          <span className="text-lg">{platform!.icon}</span>
          <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{platform!.name}</span>
        </div>
        <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
          Step {currentStep + 1}/{platform!.steps.length}
        </span>
      </div>

      {/* Step progress */}
      <div className="flex gap-1 px-4 py-2" style={{ background: 'var(--raised)' }}>
        {platform!.steps.map((_, i) => (
          <div key={i} className="flex-1 h-1 rounded-full" style={{
            background: i <= currentStep ? platform!.color : 'var(--elevated)',
            opacity: i <= currentStep ? 1 : 0.3,
          }} />
        ))}
      </div>

      <div className="p-4">
        <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
          {step!.title}
        </h4>
        <p className="text-xs leading-relaxed mb-4" style={{ color: 'var(--text-secondary)' }}>
          {step!.description}
        </p>

        {/* Action area */}
        {step!.action === 'link' && step!.url && (
          <a href={step!.url} target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition mb-4"
            style={{ background: platform!.color, color: '#fff' }}>
            Open {platform!.name} <ExternalLink className="w-3 h-3" />
          </a>
        )}

        {step!.action === 'input' && (
          <div className="mb-4">
            <label className="text-[10px] font-semibold mb-1 block" style={{ color: 'var(--text-muted)' }}>
              {step!.inputLabel}
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type={showInputs[step!.inputKey!] ? 'text' : 'password'}
                  value={inputs[step!.inputKey!] || ''}
                  onChange={e => setInputs({ ...inputs, [step!.inputKey!]: e.target.value })}
                  placeholder={step!.inputPlaceholder}
                  className="w-full rounded-lg px-3 py-2 text-xs outline-none pr-8"
                  style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                />
                <button
                  onClick={() => setShowInputs({ ...showInputs, [step!.inputKey!]: !showInputs[step!.inputKey!] })}
                  className="absolute right-2 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {showInputs[step!.inputKey!] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
              <button
                onClick={() => { if (inputs[step!.inputKey!]) navigator.clipboard.writeText(inputs[step!.inputKey!]); }}
                className="px-2 rounded-lg" style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between items-center pt-2" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => currentStep > 0 && setCurrentStep(currentStep - 1)}
            disabled={currentStep === 0}
            className="text-xs transition"
            style={{ color: currentStep === 0 ? 'var(--text-muted)' : 'var(--text-secondary)' }}
          >
            ← Previous
          </button>
          <button
            onClick={completeStep}
            className="px-4 py-2 rounded-lg text-xs font-semibold transition"
            style={{ background: platform!.color, color: '#fff' }}
          >
            {currentStep < platform!.steps.length - 1 ? 'Next Step →' : 'Complete Setup ✓'}
          </button>
        </div>
      </div>
    </div>
  );
}
