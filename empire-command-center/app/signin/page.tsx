'use client';

import { FormEvent, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Crown, Eye, EyeOff, Smartphone } from 'lucide-react';
import SignInBackground from '../components/auth/SignInBackground';
import { rememberThisDevice, studioLogin } from '../lib/studio-auth';

type Step = 'credentials' | 'remember';
type Mode = 'pin' | 'email';

function safeNext(raw: string | null): string {
  if (!raw) return '/';
  if (!raw.startsWith('/') || raw.startsWith('//')) return '/';
  if (raw.startsWith('/signin')) return '/';
  return raw;
}

export default function StudioSignInPage() {
  const router = useRouter();
  const nextPath = useMemo(() => {
    if (typeof window === 'undefined') return '/';
    return safeNext(new URLSearchParams(window.location.search).get('next'));
  }, []);

  const [mode, setMode] = useState<Mode>('pin');
  const [step, setStep] = useState<Step>('credentials');
  const [pin, setPin] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [remembering, setRemembering] = useState(false);

  const goHome = () => {
    router.replace(nextPath);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'pin') {
        await studioLogin({ pin });
      } else {
        await studioLogin({ email, password });
      }
      setStep('remember');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed');
    } finally {
      setLoading(false);
    }
  };

  const onRemember = async (yes: boolean) => {
    if (!yes) {
      goHome();
      return;
    }
    setRemembering(true);
    setError('');
    try {
      await rememberThisDevice();
      goHome();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remember this device');
      setRemembering(false);
    }
  };

  return (
    <div data-signin-page className="signin-page">
      <SignInBackground />
      <div className="signin-veil" />

      <main className="signin-shell">
        <section className="signin-card" aria-labelledby="signin-title">
          <div className="signin-brand">
            <img
              src="/brand/empire-icon.png"
              alt="Empire"
              width={48}
              height={48}
              className="signin-logo"
            />
            <div>
              <p className="signin-eyebrow">
                <Crown size={12} />
                Empire Command Center
              </p>
              <h1 id="signin-title">Studio</h1>
            </div>
          </div>

          {step === 'credentials' ? (
            <>
              <p className="signin-lede">Sign in to open the Command Center on this device.</p>

              <div className="signin-tabs" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'pin'}
                  className={mode === 'pin' ? 'is-on' : ''}
                  onClick={() => { setMode('pin'); setError(''); }}
                >
                  Founder PIN
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={mode === 'email'}
                  className={mode === 'email' ? 'is-on' : ''}
                  onClick={() => { setMode('email'); setError(''); }}
                >
                  Email
                </button>
              </div>

              <form onSubmit={onSubmit} className="signin-form">
                {error && <div className="signin-error" role="alert">{error}</div>}

                {mode === 'pin' ? (
                  <label className="signin-field">
                    <span>PIN</span>
                    <input
                      data-testid="studio-pin"
                      type="password"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={pin}
                      onChange={(e) => setPin(e.target.value)}
                      required
                      autoFocus
                      placeholder="••••"
                    />
                  </label>
                ) : (
                  <>
                    <label className="signin-field">
                      <span>Email</span>
                      <input
                        type="email"
                        autoComplete="username"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoFocus
                        placeholder="you@empirebox.store"
                      />
                    </label>
                    <label className="signin-field">
                      <span>Password</span>
                      <div className="signin-password">
                        <input
                          type={showPassword ? 'text' : 'password'}
                          autoComplete="current-password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required
                          placeholder="••••••••"
                        />
                        <button
                          type="button"
                          className="signin-eye"
                          onClick={() => setShowPassword((v) => !v)}
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                        >
                          {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                    </label>
                  </>
                )}

                <button type="submit" data-testid="studio-signin" className="signin-submit" disabled={loading}>
                  {loading ? 'Signing in…' : 'Sign in'}
                </button>
              </form>
            </>
          ) : (
            <div className="signin-remember">
              <div className="signin-remember-icon">
                <Smartphone size={22} />
              </div>
              <h2>Remember this device?</h2>
              <p>
                Stay signed in on this phone or computer for 90 days. You can revoke it anytime from Settings → My devices.
              </p>
              {error && <div className="signin-error" role="alert">{error}</div>}
              <button
                type="button"
                data-testid="remember-device"
                className="signin-submit"
                disabled={remembering}
                onClick={() => onRemember(true)}
              >
                {remembering ? 'Saving…' : 'Remember this device'}
              </button>
              <button
                type="button"
                className="signin-ghost"
                disabled={remembering}
                onClick={() => onRemember(false)}
              >
                Not now
              </button>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
