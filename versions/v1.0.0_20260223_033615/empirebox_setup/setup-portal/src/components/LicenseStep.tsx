'use client';

import { useState } from 'react';

interface Props {
  state: { licenseKey: string };
  onUpdate: (patch: { licenseKey: string }) => void;
  onNext: () => void;
  onPrev: () => void;
}

export default function LicenseStep({ state, onUpdate, onNext, onPrev }: Props) {
  const [key, setKey] = useState(state.licenseKey);
  const [error, setError] = useState('');

  const validate = () => {
    const parts = key.trim().toUpperCase().split('-');
    return parts.length === 5 && parts[0] === 'EMPIRE' && parts.slice(1).every((p) => /^[A-Z0-9]{4}$/.test(p));
  };

  const handleNext = () => {
    if (!validate()) {
      setError('Invalid license key. Expected format: EMPIRE-XXXX-XXXX-XXXX-XXXX');
      return;
    }
    onUpdate({ licenseKey: key.trim().toUpperCase() });
    onNext();
  };

  const formatKey = (value: string) => {
    const clean = value.toUpperCase().replace(/[^A-Z0-9]/g, '');
    if (clean.startsWith('EMPIRE')) {
      const rest = clean.slice(6).replace(/(.{4})/g, '$1-').replace(/-$/, '');
      return rest ? `EMPIRE-${rest}` : 'EMPIRE';
    }
    return clean;
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-1">License</h2>
      <p className="text-gray-400 mb-6 text-sm">Enter your EmpireBox license key</p>

      <div className="mb-6">
        <input
          type="text"
          placeholder="EMPIRE-XXXX-XXXX-XXXX-XXXX"
          value={key}
          onChange={(e) => { setKey(formatKey(e.target.value)); setError(''); }}
          className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-500 focus:outline-none font-mono text-lg tracking-widest"
          maxLength={24}
        />
        {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
      </div>

      <p className="text-gray-500 text-sm mb-8">
        Don&apos;t have a license?{' '}
        <a href="https://empirebox.com/pricing" className="underline" style={{ color: '#C9A84C' }}>
          Purchase one
        </a>
      </p>

      <div className="flex gap-3">
        <button onClick={onPrev} className="flex-1 py-3 rounded-lg bg-white/10 text-white font-medium">
          Back
        </button>
        <button
          onClick={handleNext}
          className="flex-1 py-3 rounded-lg font-semibold transition-opacity hover:opacity-90"
          style={{ backgroundColor: '#C9A84C', color: '#2C2C2C' }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
