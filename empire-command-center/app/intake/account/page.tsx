'use client';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, intakeFetch } from '../../lib/intake-auth';
import IntakeNav from '../../components/intake/IntakeNav';
import { User, Save, Lock, ArrowLeft } from 'lucide-react';

export default function AccountPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [form, setForm] = useState({ name: '', phone: '', company: '' });
  const [passwordForm, setPasswordForm] = useState({ password: '', confirm: '' });

  useEffect(() => {
    if (!getToken()) { router.push('/intake/login'); return; }
    intakeFetch('/me').then(u => {
      setUser(u);
      setForm({ name: u.name || '', phone: u.phone || '', company: u.company || '' });
      setLoading(false);
    }).catch(() => router.push('/intake/login'));
  }, [router]);

  const saveProfile = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await intakeFetch('/me', {
        method: 'PUT',
        body: JSON.stringify(form),
      });
      setUser(updated);
      setMessage({ type: 'success', text: 'Profile updated successfully' });
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message || 'Failed to update' });
    }
    setSaving(false);
  };

  const changePassword = async () => {
    if (passwordForm.password.length < 6) {
      setMessage({ type: 'error', text: 'Password must be at least 6 characters' });
      return;
    }
    if (passwordForm.password !== passwordForm.confirm) {
      setMessage({ type: 'error', text: 'Passwords do not match' });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      await intakeFetch('/me', {
        method: 'PUT',
        body: JSON.stringify({ password: passwordForm.password }),
      });
      setPasswordForm({ password: '', confirm: '' });
      setMessage({ type: 'success', text: 'Password changed successfully' });
    } catch (e: any) {
      setMessage({ type: 'error', text: e.message || 'Failed to change password' });
    }
    setSaving(false);
  };

  if (loading) return (
    <div data-intake-page className="min-h-screen bg-[#f5f2ed]">
      <IntakeNav />
      <div className="flex items-center justify-center h-[60vh] text-[#888]">Loading...</div>
    </div>
  );

  return (
    <div data-intake-page className="min-h-screen bg-[#f5f2ed]">
      <IntakeNav user={user} />
      <div className="max-w-xl mx-auto px-4 py-8">
        <button onClick={() => router.push('/intake/dashboard')}
          className="flex items-center gap-2 text-sm text-[#888] hover:text-[#b8960c] mb-6 transition-colors cursor-pointer">
          <ArrowLeft size={14} /> Back to Dashboard
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-11 h-11 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <User size={20} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[#1a1a1a]">My Account</h1>
            <p className="text-xs text-[#888]">{user?.email} · {user?.role}</p>
          </div>
        </div>

        {message && (
          <div className={`mb-4 p-3 rounded-lg text-sm font-medium ${
            message.type === 'success' ? 'bg-[#dcfce7] text-[#16a34a]' : 'bg-[#fef2f2] text-[#dc2626]'
          }`}>
            {message.text}
          </div>
        )}

        {/* Profile Info */}
        <div className="empire-card" style={{ padding: 20, marginBottom: 16 }}>
          <h2 className="text-sm font-bold text-[#1a1a1a] mb-4">Profile Information</h2>
          <div className="flex flex-col gap-3">
            <div>
              <label className="section-label">Name</label>
              <input className="form-input" value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div>
              <label className="section-label">Phone</label>
              <input className="form-input" value={form.phone} placeholder="Phone number"
                onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
            </div>
            <div>
              <label className="section-label">Company</label>
              <input className="form-input" value={form.company} placeholder="Company name"
                onChange={e => setForm(f => ({ ...f, company: e.target.value }))} />
            </div>
            <button onClick={saveProfile} disabled={saving}
              className="mt-1 flex items-center justify-center gap-2 text-sm font-bold text-white rounded-xl py-2.5 min-h-[44px] cursor-pointer transition-all"
              style={{ background: '#b8960c', border: '2px solid #a08509', opacity: saving ? 0.6 : 1 }}>
              <Save size={14} /> {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* Password Change */}
        <div className="empire-card" style={{ padding: 20 }}>
          <h2 className="text-sm font-bold text-[#1a1a1a] mb-4 flex items-center gap-2">
            <Lock size={14} /> Change Password
          </h2>
          <div className="flex flex-col gap-3">
            <div>
              <label className="section-label">New Password</label>
              <input className="form-input" type="password" value={passwordForm.password}
                placeholder="Min 6 characters"
                onChange={e => setPasswordForm(f => ({ ...f, password: e.target.value }))} />
            </div>
            <div>
              <label className="section-label">Confirm Password</label>
              <input className="form-input" type="password" value={passwordForm.confirm}
                placeholder="Confirm new password"
                onChange={e => setPasswordForm(f => ({ ...f, confirm: e.target.value }))} />
            </div>
            <button onClick={changePassword} disabled={saving || !passwordForm.password}
              className="mt-1 flex items-center justify-center gap-2 text-sm font-bold rounded-xl py-2.5 min-h-[44px] cursor-pointer transition-all"
              style={{ background: '#1a1a1a', color: '#fff', border: '2px solid #333', opacity: (saving || !passwordForm.password) ? 0.4 : 1 }}>
              <Lock size={14} /> Update Password
            </button>
          </div>
        </div>

        <p className="text-xs text-[#aaa] text-center mt-6">
          Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
        </p>
      </div>
    </div>
  );
}
