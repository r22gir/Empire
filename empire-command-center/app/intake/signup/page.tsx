'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';
import { signup } from '../../lib/intake-auth';
import { IntakeFooter, IntakePublicHeader, IntakeStepper } from '../../components/intake/IntakeChrome';

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
    <div data-intake-page className="min-h-screen flex flex-col">
      <IntakePublicHeader />

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          <IntakeStepper current="signup" />
          <div className="intake-card">
            <h1 className="text-3xl font-semibold text-center mb-1">Create Your Account</h1>
            <p className="text-sm text-center mb-6" style={{ color: '#4f4a40' }}>Free — no credit card required</p>

            <form onSubmit={handleSubmit} className="space-y-3.5">
              {error && (
                <div className="text-sm text-[#9b1c1c] bg-[#fef2f2] border border-[#fecaca] rounded-[10px] px-3 py-2.5" role="alert">
                  {error}
                </div>
              )}
              <div>
                <label className="intake-label block mb-1.5">Full Name *</label>
                <input type="text" required value={form.name} onChange={e => set('name', e.target.value)}
                  className="form-input" placeholder="Jane Smith" />
              </div>
              <div>
                <label className="intake-label block mb-1.5">Email *</label>
                <input type="email" required value={form.email} onChange={e => set('email', e.target.value)}
                  className="form-input" placeholder="jane@studio.com" />
              </div>
              <div>
                <label className="intake-label block mb-1.5">Phone</label>
                <input type="tel" value={form.phone} onChange={e => set('phone', e.target.value)}
                  className="form-input" placeholder="(555) 123-4567" />
              </div>
              <div>
                <label className="intake-label block mb-1.5">Password *</label>
                <div className="relative">
                  <input type={showPassword ? 'text' : 'password'} required value={form.password} onChange={e => set('password', e.target.value)}
                    className="form-input" style={{ paddingRight: 44 }} placeholder="6+ characters" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-0 top-0 h-full px-3 flex items-center"
                    style={{ color: '#4f4a40' }}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <div>
                <label className="intake-label block mb-1.5">Company / Studio</label>
                <input type="text" value={form.company} onChange={e => set('company', e.target.value)}
                  className="form-input" placeholder="Optional" />
              </div>
              <div>
                <label className="intake-label block mb-1.5">I am a...</label>
                <select value={form.role} onChange={e => set('role', e.target.value)} className="form-input">
                  <option value="client">Homeowner / Client</option>
                  <option value="designer">Interior Designer</option>
                  <option value="contractor">Contractor</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="intake-btn intake-btn-charcoal w-full"
              >
                {loading ? 'Creating Account...' : 'Create Free Account'}
              </button>
            </form>
          </div>

          <p className="text-sm text-center mt-5" style={{ color: '#4f4a40' }}>
            Already have an account?{' '}
            <Link href="/intake/login" className="font-semibold" style={{ color: '#6b5408' }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
      <IntakeFooter />
    </div>
  );
}
