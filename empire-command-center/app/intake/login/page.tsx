'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Zap } from 'lucide-react';
import Link from 'next/link';
import { login } from '../../lib/intake-auth';

export default function IntakeLogin() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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

      <div className="flex-1 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold text-[#1a1a1a] text-center mb-1">Welcome Back</h1>
          <p className="text-sm text-[#777] text-center mb-8">Sign in to your design portal</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="text-xs text-[#dc2626] bg-[#fef2f2] border border-[#fecaca] rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#555] mb-1.5">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none"
                placeholder="••••••••"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 text-sm font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="text-xs text-[#777] text-center mt-6">
            Don&apos;t have an account?{' '}
            <Link href="/intake/signup" className="text-[#c9a84c] font-semibold hover:underline">
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
