'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Crown, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';
import { signup } from '../../lib/intake-auth';

export default function IntakeSignup() {
  const router = useRouter();
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '', company: '', role: 'client' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

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
    <div data-intake-page className="min-h-screen bg-[#f5f2ed] flex flex-col">
      <nav className="bg-[#1a1a1a] border-b border-[#2a2a2a]">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 flex items-center h-12">
          <Link href="/intake" className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#b8960c] flex items-center justify-center">
              <Crown size={13} className="text-white" />
            </div>
            <span className="font-bold text-[13px] text-white tracking-wide">Empire</span>
            <span className="text-[9px] text-[#888] font-medium tracking-wider uppercase">LuxeForge</span>
          </Link>
        </div>
      </nav>

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-sm">
          <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-6 shadow-[0_2px_12px_rgba(0,0,0,0.04)]">
            <h1 className="text-xl font-bold text-[#1a1a1a] text-center mb-1">Create Your Account</h1>
            <p className="text-[12px] text-[#888] text-center mb-6">Free — no credit card required</p>

            <form onSubmit={handleSubmit} className="space-y-3.5">
              {error && (
                <div className="text-[11px] text-[#dc2626] bg-[#fef2f2] border border-[#fecaca] rounded-[10px] px-3 py-2">
                  {error}
                </div>
              )}
              <div>
                <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Full Name *</label>
                <input type="text" required value={form.name} onChange={e => set('name', e.target.value)}
                  className="form-input" placeholder="Jane Smith" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Email *</label>
                <input type="email" required value={form.email} onChange={e => set('email', e.target.value)}
                  className="form-input" placeholder="jane@studio.com" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Phone</label>
                <input type="tel" value={form.phone} onChange={e => set('phone', e.target.value)}
                  className="form-input" placeholder="(555) 123-4567" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Password *</label>
                <div className="relative">
                  <input type={showPassword ? 'text' : 'password'} required value={form.password} onChange={e => set('password', e.target.value)}
                    className="form-input" style={{ paddingRight: 44 }} placeholder="6+ characters" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-0 top-0 h-full px-3 flex items-center text-[#999] hover:text-[#666] transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Company / Studio</label>
                <input type="text" value={form.company} onChange={e => set('company', e.target.value)}
                  className="form-input" placeholder="Optional" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">I am a...</label>
                <select value={form.role} onChange={e => set('role', e.target.value)} className="form-input">
                  <option value="client">Homeowner / Client</option>
                  <option value="designer">Interior Designer</option>
                  <option value="contractor">Contractor</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 min-h-[44px] text-sm font-bold bg-[#1a1a1a] text-white rounded-[10px] hover:bg-[#333] transition-colors disabled:opacity-50"
              >
                {loading ? 'Creating Account...' : 'Create Free Account'}
              </button>
            </form>
          </div>

          <p className="text-sm text-[#888] text-center mt-5">
            Already have an account?{' '}
            <Link href="/intake/login" className="text-[#b8960c] font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
