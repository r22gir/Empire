'use client';

import { useState } from 'react';

interface Props {
  state: { accountEmail: string; accountToken: string };
  onUpdate: (patch: { accountEmail?: string; accountToken?: string }) => void;
  onNext: () => void;
}

export default function AccountStep({ state, onUpdate, onNext }: Props) {
  const [mode, setMode] = useState<'login' | 'create'>('login');
  const [email, setEmail] = useState(state.accountEmail);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }
    // In production, call the real auth API
    onUpdate({ accountEmail: email, accountToken: 'demo-token' });
    onNext();
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-1">Account</h2>
      <p className="text-gray-400 mb-6 text-sm">Sign in or create your EmpireBox account</p>

      <div className="flex gap-2 mb-6">
        {(['login', 'create'] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === m ? 'text-charcoal' : 'bg-white/10 text-white'
            }`}
            style={mode === m ? { backgroundColor: '#C9A84C', color: '#2C2C2C' } : {}}
          >
            {m === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="email"
          placeholder="Email address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-500 focus:outline-none focus:ring-2"
          style={{ '--tw-ring-color': '#C9A84C' } as React.CSSProperties}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-500 focus:outline-none"
        />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        <button
          type="submit"
          className="w-full py-3 rounded-lg font-semibold text-charcoal transition-opacity hover:opacity-90"
          style={{ backgroundColor: '#C9A84C', color: '#2C2C2C' }}
        >
          {mode === 'login' ? 'Sign In & Continue' : 'Create Account & Continue'}
        </button>
      </form>
    </div>
  );
}
