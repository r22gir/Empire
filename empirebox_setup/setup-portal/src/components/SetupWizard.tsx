'use client';

import { useState } from 'react';
import AccountStep from './AccountStep';
import LicenseStep from './LicenseStep';
import ProductsStep from './ProductsStep';
import AIModelsStep from './AIModelsStep';
import InstallStep from './InstallStep';

const STEPS = ['Account', 'License', 'Products', 'AI Models', 'Install'];

interface WizardState {
  accountEmail: string;
  accountToken: string;
  licenseKey: string;
  selectedProducts: string[];
  selectedModels: string[];
}

export default function SetupWizard({ deviceId }: { deviceId: string }) {
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>({
    accountEmail: '',
    accountToken: '',
    licenseKey: '',
    selectedProducts: [],
    selectedModels: [],
  });

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  const update = (patch: Partial<WizardState>) => setState((s) => ({ ...s, ...patch }));

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold" style={{ color: '#C9A84C' }}>
          EmpireBox Setup
        </h1>
        <p className="text-gray-400 mt-1">Device: {deviceId}</p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-between mb-10 px-2">
        {STEPS.map((label, i) => (
          <div key={label} className="flex flex-col items-center flex-1">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                i < step
                  ? 'bg-gold text-charcoal'
                  : i === step
                  ? 'border-2 border-gold text-gold'
                  : 'border-2 border-white/20 text-gray-500'
              }`}
              style={i < step ? { backgroundColor: '#C9A84C', color: '#2C2C2C' } : i === step ? { borderColor: '#C9A84C', color: '#C9A84C' } : {}}
            >
              {i < step ? '✓' : i + 1}
            </div>
            <span className={`text-xs mt-1 ${i === step ? 'text-white' : 'text-gray-500'}`}>{label}</span>
            {i < STEPS.length - 1 && (
              <div className={`h-px flex-1 mt-4 ${i < step ? 'bg-gold' : 'bg-white/10'}`} style={i < step ? { backgroundColor: '#C9A84C' } : {}} />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="bg-white/5 rounded-2xl p-6 min-h-64">
        {step === 0 && <AccountStep state={state} onUpdate={update} onNext={next} />}
        {step === 1 && <LicenseStep state={state} onUpdate={update} onNext={next} onPrev={prev} />}
        {step === 2 && <ProductsStep state={state} onUpdate={update} onNext={next} onPrev={prev} />}
        {step === 3 && <AIModelsStep state={state} onUpdate={update} onNext={next} onPrev={prev} />}
        {step === 4 && <InstallStep state={state} deviceId={deviceId} onPrev={prev} />}
      </div>
    </div>
  );
}
