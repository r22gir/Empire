'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Crown, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';
import { login, intakeFetch } from '../../lib/intake-auth';

export default function IntakeLogin() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [resetMode, setResetMode] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      router.push('/intake/dashboard');
    } catch (_err) {
      setError('Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    if (newPassword.length < 6) { setError('Password must be at least 6 characters.'); return; }
    setResetLoading(true);
    try {
      await intakeFetch('/reset-password', {
        method: 'POST',
        body: JSON.stringify({ email: resetEmail, new_password: newPassword }),
      });
      setSuccess('Password reset! You can now sign in.');
      setResetMode(false);
      setEmail(resetEmail);
      setPassword('');
    } catch (_err) {
      setError('Could not reset password. Check your email address.');
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f2ed] flex flex-col">
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

      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="bg-[#faf9f7] border border-[#ece8e0] rounded-[14px] p-6 shadow-[0_2px_12px_rgba(0,0,0,0.04)]">
            {!resetMode ? (
              <>
                <h1 className="text-xl font-bold text-[#1a1a1a] text-center mb-1">Welcome Back</h1>
                <p className="text-[12px] text-[#888] text-center mb-6">Sign in to your design portal</p>

                <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
                    <div className="text-sm text-[#dc2626] bg-[#fef2f2] border border-[#fecaca] rounded-[10px] px-3 py-2.5">
                      {error}
                    </div>
                  )}
                  {success && (
                    <div className="text-sm text-[#16a34a] bg-[#f0fdf4] border border-[#bbf7d0] rounded-[10px] px-3 py-2.5">
                      {success}
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Email</label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      className="form-input"
                      placeholder="you@example.com"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Password</label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        className="form-input"
                        style={{ paddingRight: 44 }}
                        placeholder="••••••••"
                      />
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
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 min-h-[44px] text-sm font-bold bg-[#1a1a1a] text-white rounded-[10px] hover:bg-[#333] transition-colors disabled:opacity-50"
                  >
                    {loading ? 'Signing in...' : 'Sign In'}
                  </button>
                </form>

                <button
                  onClick={() => { setResetMode(true); setResetEmail(email); setError(''); setSuccess(''); }}
                  className="w-full text-[12px] text-[#b8960c] font-semibold mt-4 hover:underline"
                >
                  Forgot password?
                </button>
              </>
            ) : (
              <>
                <h1 className="text-xl font-bold text-[#1a1a1a] text-center mb-1">Reset Password</h1>
                <p className="text-[12px] text-[#888] text-center mb-6">Enter your email and a new password</p>

                <form onSubmit={handleReset} className="space-y-4">
                  {error && (
                    <div className="text-sm text-[#dc2626] bg-[#fef2f2] border border-[#fecaca] rounded-[10px] px-3 py-2.5">
                      {error}
                    </div>
                  )}
                  <div>
                    <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">Email</label>
                    <input
                      type="email"
                      required
                      value={resetEmail}
                      onChange={e => setResetEmail(e.target.value)}
                      className="form-input"
                      placeholder="you@example.com"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#999] uppercase tracking-[0.5px] mb-1.5">New Password</label>
                    <div className="relative">
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        required
                        value={newPassword}
                        onChange={e => setNewPassword(e.target.value)}
                        className="form-input"
                        style={{ paddingRight: 44 }}
                        placeholder="6+ characters"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword(!showNewPassword)}
                        className="absolute right-0 top-0 h-full px-3 flex items-center text-[#999] hover:text-[#666] transition-colors"
                        tabIndex={-1}
                      >
                        {showNewPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={resetLoading}
                    className="w-full py-3 min-h-[44px] text-sm font-bold bg-[#1a1a1a] text-white rounded-[10px] hover:bg-[#333] transition-colors disabled:opacity-50"
                  >
                    {resetLoading ? 'Resetting...' : 'Reset Password'}
                  </button>
                </form>

                <button
                  onClick={() => { setResetMode(false); setError(''); }}
                  className="w-full text-[12px] text-[#b8960c] font-semibold mt-4 hover:underline"
                >
                  Back to sign in
                </button>
              </>
            )}
          </div>

          <p className="text-sm text-[#888] text-center mt-5">
            Don&apos;t have an account?{' '}
            <Link href="/intake/signup" className="text-[#b8960c] font-semibold hover:underline">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
