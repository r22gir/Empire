'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Zap } from 'lucide-react';
import Link from 'next/link';
import { signup } from '../../lib/intake-auth';

export default function IntakeSignup() {
  const router = useRouter();
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '', company: '', role: 'client' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const set = (field: string, val: string) => setForm(f => ({ ...f, [field]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 6) { setError('Password must be at least 6 characters.'); return; }
    setLoading(true);
    try {
      await signup(form);
      router.push('/intake/dashboard');
    } catch (_err) {
      setError('Could not create account. Email may already be registered.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#faf9f7] flex flex-col">
      <nav className="bg-white border-b border-[#e5e0d8]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center h-14">
          <Link href="/intake" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#c9a84c] flex items-center justify-center">
              <Zap size={16} className="text-white" />
            </div>
            <span className="font-bold text-[14px]">Empire</span>
            <span className="text-[10px] text-[#aaa] ml-1">Design Portal</span>
          </Link>
        </div>
      </nav>

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold text-[#1a1a1a] text-center mb-1">Create Your Account</h1>
          <p className="text-sm text-[#777] text-center mb-8">Free — no credit card required</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="text-xs text-[#dc2626] bg-[#fef2f2] border border-[#fecaca] rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">Full Name *</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={e => set('name', e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                placeholder="Jane Smith"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">Email *</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={e => set('email', e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                placeholder="jane@studio.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">Phone</label>
              <input
                type="tel"
                value={form.phone}
                onChange={e => set('phone', e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                placeholder="(555) 123-4567"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">Password *</label>
              <input
                type="password"
                required
                value={form.password}
                onChange={e => set('password', e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                placeholder="6+ characters"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">Company / Studio</label>
              <input
                type="text"
                value={form.company}
                onChange={e => set('company', e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                placeholder="Optional"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">I am a...</label>
              <select
                value={form.role}
                onChange={e => set('role', e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
              >
                <option value="client">Homeowner / Client</option>
                <option value="designer">Interior Designer</option>
                <option value="contractor">Contractor</option>
              </select>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 text-sm font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors disabled:opacity-50"
            >
              {loading ? 'Creating Account...' : 'Create Free Account'}
            </button>
          </form>

          <p className="text-xs text-[#777] text-center mt-6">
            Already have an account?{' '}
            <Link href="/intake/login" className="text-[#c9a84c] font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
