'use client';
import { useState, useEffect } from 'react';
import {
  Instagram, Facebook, Sparkles, Calendar, PenTool, BarChart3,
  Plus, Send, Clock, CheckCircle, FileText, Trash2, RefreshCw,
  Settings, ExternalLink, CircleDot, SkipForward, Loader2, ChevronRight,
} from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const SF_API = `${API}/socialforge`;

const PLATFORMS = [
  { id: 'instagram', label: 'Instagram', icon: Instagram, color: '#E1306C' },
  { id: 'facebook', label: 'Facebook', icon: Facebook, color: '#1877F2' },
  { id: 'pinterest', label: 'Pinterest', icon: FileText, color: '#E60023' },
  { id: 'linkedin', label: 'LinkedIn', icon: FileText, color: '#0A66C2' },
  { id: 'tiktok', label: 'TikTok', icon: FileText, color: '#000000' },
];

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  draft: { bg: '#f5f3ef', text: '#777' },
  scheduled: { bg: '#dbeafe', text: '#2563eb' },
  posted: { bg: '#dcfce7', text: '#16a34a' },
  failed: { bg: '#fef2f2', text: '#dc2626' },
};

type Tab = 'dashboard' | 'compose' | 'posts' | 'calendar' | 'generate' | 'setup';

export default function SocialForgePage() {
  const [tab, setTab] = useState<Tab>('setup');
  const [dashboard, setDashboard] = useState<any>(null);
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Compose state
  const [platform, setPlatform] = useState('instagram');
  const [content, setContent] = useState('');
  const [hashtags, setHashtags] = useState('');
  const [scheduledFor, setScheduledFor] = useState('');
  const [saving, setSaving] = useState(false);

  // AI Generate state
  const [aiTopic, setAiTopic] = useState('');
  const [aiStyle, setAiStyle] = useState('professional');
  const [aiPlatform, setAiPlatform] = useState('instagram');
  const [aiResult, setAiResult] = useState('');
  const [generating, setGenerating] = useState(false);

  const loadData = async () => {
    try {
      const [dash, postList] = await Promise.all([
        fetch(`${SF_API}/dashboard`).then(r => r.json()),
        fetch(`${SF_API}/posts`).then(r => r.json()),
      ]);
      setDashboard(dash);
      setPosts(postList);
    } catch (_err) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleCreatePost = async () => {
    setSaving(true);
    try {
      await fetch(`${SF_API}/posts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          content,
          hashtags,
          scheduled_for: scheduledFor || null,
          status: scheduledFor ? 'scheduled' : 'draft',
        }),
      });
      setContent('');
      setHashtags('');
      setScheduledFor('');
      setTab('posts');
      await loadData();
    } catch (_err) {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setAiResult('');
    try {
      const res = await fetch(`${SF_API}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: aiPlatform,
          topic: aiTopic,
          style: aiStyle,
          include_hashtags: true,
        }),
      });
      const data = await res.json();
      setAiResult(data.generated_content || data.detail || 'No content generated');
    } catch (_err) {
      setAiResult('Generation failed. Check backend connection.');
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (id: string) => {
    await fetch(`${SF_API}/posts/${id}`, { method: 'DELETE' });
    await loadData();
  };

  const handleStatusChange = async (id: string, status: string) => {
    await fetch(`${SF_API}/posts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    await loadData();
  };

  // Setup state
  const [accounts, setAccounts] = useState<any[]>([]);
  const [accountCategories, setAccountCategories] = useState<any>({});
  const [setupProgress, setSetupProgress] = useState<any>({ done: 0, total: 0, pct: 0 });
  const [activeGuide, setActiveGuide] = useState<string | null>(null);
  const [guideContent, setGuideContent] = useState('');
  const [loadingGuide, setLoadingGuide] = useState(false);
  const [profile, setProfile] = useState<any>({});
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileExpanded, setProfileExpanded] = useState(false);

  const loadAccounts = async () => {
    try {
      const res = await fetch(`${SF_API}/accounts`);
      const data = await res.json();
      setAccounts(data.accounts || []);
      setAccountCategories(data.categories || {});
      setSetupProgress(data.progress || { done: 0, total: 0, pct: 0 });
    } catch (_err) { /* ignore */ }
  };

  const loadProfile = async () => {
    try {
      const res = await fetch(`${SF_API}/profile`);
      setProfile(await res.json());
    } catch (_err) { /* ignore */ }
  };

  const saveProfile = async () => {
    setProfileSaving(true);
    try {
      await fetch(`${SF_API}/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
    } catch (_err) { /* ignore */ }
    setProfileSaving(false);
  };

  const setField = (key: string, val: string) => setProfile((p: any) => ({ ...p, [key]: val }));

  useEffect(() => { loadAccounts(); loadProfile(); }, []);

  const updateAccount = async (id: string, updates: any) => {
    await fetch(`${SF_API}/accounts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    await loadAccounts();
  };

  const getAIGuide = async (account: any) => {
    setActiveGuide(account.id);
    setLoadingGuide(true);
    setGuideContent('');
    try {
      const res = await fetch(`${SF_API}/accounts/ai-guide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform: account.platform, topic: account.name, style: 'professional' }),
      });
      const data = await res.json();
      setGuideContent(data.guide || 'Could not generate guide.');
    } catch (_err) {
      setGuideContent('Failed to generate guide. Check backend connection.');
    } finally {
      setLoadingGuide(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: any }[] = [
    { id: 'setup', label: `Setup (${setupProgress.done}/${setupProgress.total})`, icon: Settings },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'compose', label: 'Compose', icon: PenTool },
    { id: 'generate', label: 'AI Generate', icon: Sparkles },
    { id: 'posts', label: 'All Posts', icon: FileText },
    { id: 'calendar', label: 'Calendar', icon: Calendar },
  ];

  return (
    <div className="h-full flex flex-col bg-[#faf9f7] overflow-auto">
      {/* Header */}
      <div className="bg-white border-b border-[#e5e0d8] px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#ec4899] to-[#a855f7] flex items-center justify-center">
              <Sparkles size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-[#1a1a1a]">SocialForge</h1>
              <p className="text-[10px] text-[#aaa]">AI-Powered Social Media Manager</p>
            </div>
          </div>
          <button onClick={loadData} className="text-[#aaa] hover:text-[#ec4899] transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg transition-colors ${
                tab === t.id
                  ? 'bg-[#ec4899] text-white'
                  : 'text-[#777] hover:bg-[#f5f3ef]'
              }`}
            >
              <t.icon size={14} /> {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6">
        {/* Dashboard */}
        {tab === 'dashboard' && (
          <div>
            {loading ? (
              <div className="text-sm text-[#aaa]">Loading...</div>
            ) : dashboard ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                  <KPI label="Total Posts" value={dashboard.total_posts} />
                  <KPI label="Drafts" value={dashboard.drafts} color="#777" />
                  <KPI label="Scheduled" value={dashboard.scheduled} color="#2563eb" />
                  <KPI label="Posted" value={dashboard.posted} color="#16a34a" />
                </div>

                {dashboard.by_platform && Object.keys(dashboard.by_platform).length > 0 && (
                  <div className="bg-white border border-[#e5e0d8] rounded-xl p-4 mb-4">
                    <h3 className="text-sm font-bold text-[#1a1a1a] mb-3">By Platform</h3>
                    <div className="flex gap-4">
                      {Object.entries(dashboard.by_platform).map(([plat, count]) => {
                        const p = PLATFORMS.find(pp => pp.id === plat);
                        return (
                          <div key={plat} className="flex items-center gap-2 text-xs">
                            <span className="w-3 h-3 rounded-full" style={{ background: p?.color || '#999' }} />
                            <span className="font-semibold capitalize">{plat}</span>
                            <span className="text-[#aaa]">{count as number}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {dashboard.recent_posts?.length > 0 && (
                  <div className="bg-white border border-[#e5e0d8] rounded-xl p-4">
                    <h3 className="text-sm font-bold text-[#1a1a1a] mb-3">Recent Posts</h3>
                    <div className="space-y-2">
                      {dashboard.recent_posts.map((p: any) => (
                        <PostRow key={p.id} post={p} onDelete={handleDelete} onStatusChange={handleStatusChange} />
                      ))}
                    </div>
                  </div>
                )}

                {(!dashboard.recent_posts || dashboard.recent_posts.length === 0) && (
                  <div className="bg-white border border-[#e5e0d8] rounded-xl p-8 text-center">
                    <Sparkles size={32} className="mx-auto text-[#ddd] mb-3" />
                    <h3 className="text-sm font-semibold text-[#1a1a1a] mb-1">No posts yet</h3>
                    <p className="text-xs text-[#777] mb-3">Create your first post or let AI generate one.</p>
                    <button onClick={() => setTab('generate')} className="px-4 py-2 text-xs font-semibold bg-[#ec4899] text-white rounded-lg hover:bg-[#db2777] transition-colors">
                      AI Generate Post
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="text-sm text-[#aaa]">Could not load dashboard</div>
            )}
          </div>
        )}

        {/* Compose */}
        {tab === 'compose' && (
          <div className="max-w-2xl">
            <h2 className="text-lg font-bold text-[#1a1a1a] mb-4">Compose Post</h2>
            <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Platform</label>
                <div className="flex gap-2">
                  {PLATFORMS.map(p => (
                    <button
                      key={p.id}
                      onClick={() => setPlatform(p.id)}
                      className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border transition-colors ${
                        platform === p.id
                          ? 'border-[#ec4899] bg-[#fdf2f8] text-[#ec4899]'
                          : 'border-[#e5e0d8] text-[#777] hover:border-[#ec4899]'
                      }`}
                    >
                      <p.icon size={14} /> {p.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Caption</label>
                <textarea
                  value={content}
                  onChange={e => setContent(e.target.value)}
                  rows={5}
                  className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none resize-none"
                  placeholder="Write your post caption..."
                />
                <div className="text-[10px] text-[#aaa] mt-1">{content.length} characters</div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Hashtags</label>
                <textarea
                  value={hashtags}
                  onChange={e => setHashtags(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none resize-none"
                  placeholder="#customdrapes #interiordesign #luxuryliving..."
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Schedule (optional)</label>
                <input
                  type="datetime-local"
                  value={scheduledFor}
                  onChange={e => setScheduledFor(e.target.value)}
                  className="px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none"
                />
              </div>
              <button
                onClick={handleCreatePost}
                disabled={saving || !content.trim()}
                className="px-6 py-2.5 text-xs font-semibold bg-[#ec4899] text-white rounded-lg hover:bg-[#db2777] transition-colors disabled:opacity-50 flex items-center gap-1.5"
              >
                {saving ? 'Saving...' : (<><Send size={14} /> {scheduledFor ? 'Schedule Post' : 'Save Draft'}</>)}
              </button>
            </div>
          </div>
        )}

        {/* AI Generate */}
        {tab === 'generate' && (
          <div className="max-w-2xl">
            <h2 className="text-lg font-bold text-[#1a1a1a] mb-4">AI Content Generator</h2>
            <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#555] mb-1.5">Topic</label>
                <input
                  type="text"
                  value={aiTopic}
                  onChange={e => setAiTopic(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none"
                  placeholder="e.g., Custom roman shades for modern homes"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-[#555] mb-1.5">Platform</label>
                  <select
                    value={aiPlatform}
                    onChange={e => setAiPlatform(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none"
                  >
                    {PLATFORMS.map(p => <option key={p.id} value={p.id}>{p.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#555] mb-1.5">Style</label>
                  <select
                    value={aiStyle}
                    onChange={e => setAiStyle(e.target.value)}
                    className="w-full px-3 py-2.5 text-sm border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none"
                  >
                    <option value="professional">Professional</option>
                    <option value="casual">Casual</option>
                    <option value="luxury">Luxury</option>
                    <option value="educational">Educational</option>
                  </select>
                </div>
              </div>
              <button
                onClick={handleGenerate}
                disabled={generating || !aiTopic.trim()}
                className="px-6 py-2.5 text-xs font-semibold bg-gradient-to-r from-[#ec4899] to-[#a855f7] text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-1.5"
              >
                {generating ? 'Generating...' : (<><Sparkles size={14} /> Generate with AI</>)}
              </button>

              {aiResult && (
                <div className="mt-4 p-4 bg-[#fdf2f8] border border-[#ec4899]/20 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-bold text-[#1a1a1a]">Generated Content</h3>
                    <button
                      onClick={() => {
                        setContent(aiResult);
                        setPlatform(aiPlatform);
                        setTab('compose');
                      }}
                      className="text-[10px] font-semibold text-[#ec4899] hover:underline"
                    >
                      Use as Post &rarr;
                    </button>
                  </div>
                  <pre className="text-xs text-[#555] whitespace-pre-wrap font-sans leading-relaxed">
                    {aiResult}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {/* All Posts */}
        {tab === 'posts' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-[#1a1a1a]">All Posts</h2>
              <button
                onClick={() => setTab('compose')}
                className="px-4 py-2 text-xs font-semibold bg-[#ec4899] text-white rounded-lg hover:bg-[#db2777] transition-colors flex items-center gap-1.5"
              >
                <Plus size={14} /> New Post
              </button>
            </div>
            {posts.length === 0 ? (
              <div className="bg-white border border-[#e5e0d8] rounded-xl p-8 text-center">
                <FileText size={32} className="mx-auto text-[#ddd] mb-3" />
                <p className="text-sm text-[#777]">No posts yet. Create or generate one!</p>
              </div>
            ) : (
              <div className="space-y-2">
                {posts.map((p: any) => (
                  <PostRow key={p.id} post={p} onDelete={handleDelete} onStatusChange={handleStatusChange} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Setup / Accounts */}
        {tab === 'setup' && (
          <div>
            {/* Business Profile — Single source of truth */}
            <div className="bg-white border border-[#e5e0d8] rounded-xl mb-4 overflow-hidden">
              <button
                onClick={() => setProfileExpanded(!profileExpanded)}
                className="w-full flex items-center justify-between p-5 text-left hover:bg-[#faf9f7] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#c9a84c] to-[#a87c1e] flex items-center justify-center">
                    <span className="text-white font-bold text-sm">E</span>
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-[#1a1a1a]">Business Profile</h2>
                    <p className="text-[10px] text-[#777]">Fill this once — AI uses it to generate all your platform bios, descriptions, and setup guides</p>
                  </div>
                </div>
                <ChevronRight size={16} className={`text-[#aaa] transition-transform ${profileExpanded ? 'rotate-90' : ''}`} />
              </button>

              {profileExpanded && (
                <div className="px-5 pb-5 border-t border-[#e5e0d8] pt-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <ProfileField label="Business Name" value={profile.business_name} onChange={v => setField('business_name', v)} />
                    <ProfileField label="Tagline" value={profile.tagline} onChange={v => setField('tagline', v)} placeholder="e.g., Luxury Custom Window Treatments" />
                    <ProfileField label="Owner Name" value={profile.owner_name} onChange={v => setField('owner_name', v)} />
                    <ProfileField label="Phone" value={profile.phone} onChange={v => setField('phone', v)} placeholder="(555) 123-4567" />
                    <ProfileField label="Business Email" value={profile.email} onChange={v => setField('email', v)} placeholder="hello@empirebox.store" />
                    <ProfileField label="Website" value={profile.website} onChange={v => setField('website', v)} />
                    <ProfileField label="Street Address" value={profile.address} onChange={v => setField('address', v)} />
                    <div className="grid grid-cols-3 gap-2">
                      <ProfileField label="City" value={profile.city} onChange={v => setField('city', v)} />
                      <ProfileField label="State" value={profile.state} onChange={v => setField('state', v)} />
                      <ProfileField label="ZIP" value={profile.zip} onChange={v => setField('zip', v)} />
                    </div>
                    <ProfileField label="Service Area" value={profile.service_area} onChange={v => setField('service_area', v)} placeholder="Washington DC Metro Area" />
                    <ProfileField label="Founded Year" value={profile.founded_year} onChange={v => setField('founded_year', v)} placeholder="2026" />
                  </div>
                  <div className="grid grid-cols-1 gap-3 mt-3">
                    <ProfileField label="Services (comma-separated)" value={profile.services} onChange={v => setField('services', v)} />
                    <ProfileField label="Target Audience" value={profile.target_audience} onChange={v => setField('target_audience', v)} />
                    <ProfileField label="Style Keywords" value={profile.style_keywords} onChange={v => setField('style_keywords', v)} placeholder="Premium, Custom, Luxury, Handcrafted" />
                    <div>
                      <label className="block text-[10px] font-medium text-[#555] mb-1">Short Bio (160 chars — for Instagram, Twitter)</label>
                      <textarea
                        value={profile.bio_short || ''}
                        onChange={e => setField('bio_short', e.target.value)}
                        rows={2}
                        maxLength={160}
                        className="w-full px-3 py-2 text-xs border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none resize-none"
                        placeholder="Premium custom drapery, shades & upholstery in Washington DC. Transforming spaces one window at a time."
                      />
                      <span className="text-[9px] text-[#aaa]">{(profile.bio_short || '').length}/160</span>
                    </div>
                    <div>
                      <label className="block text-[10px] font-medium text-[#555] mb-1">Long Bio (for Facebook, LinkedIn, Google Business)</label>
                      <textarea
                        value={profile.bio_long || ''}
                        onChange={e => setField('bio_long', e.target.value)}
                        rows={4}
                        className="w-full px-3 py-2 text-xs border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none resize-none"
                        placeholder="Empire Workroom is a premium custom window treatment studio serving the Washington DC metro area..."
                      />
                    </div>
                    <ProfileField label="Brand Colors (hex)" value={profile.brand_colors} onChange={v => setField('brand_colors', v)} />
                    <ProfileField label="Logo URL (optional)" value={profile.logo_url} onChange={v => setField('logo_url', v)} />
                  </div>
                  <div className="flex items-center gap-3 mt-4">
                    <button
                      onClick={saveProfile}
                      disabled={profileSaving}
                      className="px-6 py-2.5 text-xs font-semibold bg-[#c9a84c] text-white rounded-lg hover:bg-[#b8960c] transition-colors disabled:opacity-50"
                    >
                      {profileSaving ? 'Saving...' : 'Save Profile'}
                    </button>
                    <span className="text-[10px] text-[#aaa]">All AI guides will use this info to generate ready-to-paste text</span>
                  </div>
                </div>
              )}
            </div>

            {/* Progress bar */}
            <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 mb-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-bold text-[#1a1a1a]">Empire Marketing Setup</h2>
                <span className="text-sm font-bold text-[#ec4899]">{setupProgress.pct}% Complete</span>
              </div>
              <div className="w-full h-3 bg-[#f5f3ef] rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-[#ec4899] to-[#a855f7] rounded-full transition-all" style={{ width: `${setupProgress.pct}%` }} />
              </div>
              <p className="text-xs text-[#777] mt-2">
                {setupProgress.done} of {setupProgress.total} accounts set up. Click each to get an AI setup guide and open the signup page.
              </p>
            </div>

            {/* Account categories */}
            {Object.entries(accountCategories).map(([cat, accts]) => {
              const catLabels: Record<string, string> = {
                email: 'Email & Communications',
                social: 'Social Media',
                local: 'Local & Maps',
                directory: 'Industry Directories',
                email_marketing: 'Email Marketing',
                tools: 'Design & Scheduling Tools',
              };
              return (
                <div key={cat} className="mb-4">
                  <h3 className="text-xs font-bold text-[#aaa] uppercase tracking-wider mb-2 px-1">
                    {catLabels[cat] || cat}
                  </h3>
                  <div className="space-y-2">
                    {(accts as any[]).map((a: any) => {
                      const isDone = a.status === 'done';
                      const isActive = a.status === 'in_progress';
                      const isSkipped = a.status === 'skipped';
                      return (
                        <div key={a.id} className={`bg-white border rounded-xl overflow-hidden transition-all ${
                          isDone ? 'border-[#16a34a]/30' : isActive ? 'border-[#ec4899]/40' : 'border-[#e5e0d8]'
                        }`}>
                          <div className="p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3 flex-1 min-w-0">
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                                  isDone ? 'bg-[#dcfce7]' : isActive ? 'bg-[#fdf2f8]' : isSkipped ? 'bg-[#f5f3ef]' : 'bg-[#f5f3ef]'
                                }`}>
                                  {isDone ? <CheckCircle size={16} className="text-[#16a34a]" /> :
                                   isActive ? <CircleDot size={16} className="text-[#ec4899]" /> :
                                   isSkipped ? <SkipForward size={16} className="text-[#aaa]" /> :
                                   <CircleDot size={16} className="text-[#ddd]" />}
                                </div>
                                <div className="min-w-0">
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-semibold text-[#1a1a1a]">{a.name}</span>
                                    <span className="text-[10px] text-[#aaa]">{a.platform}</span>
                                  </div>
                                  <p className="text-[11px] text-[#777] truncate">{a.description}</p>
                                  {a.handle && <p className="text-[11px] text-[#ec4899] font-semibold mt-0.5">{a.handle}</p>}
                                </div>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0 ml-2">
                                {!isDone && !isSkipped && (
                                  <a
                                    href={a.setup_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-3 py-1.5 text-[10px] font-semibold bg-[#ec4899] text-white rounded-lg hover:bg-[#db2777] transition-colors flex items-center gap-1"
                                  >
                                    <ExternalLink size={11} /> Open
                                  </a>
                                )}
                                <button
                                  onClick={() => getAIGuide(a)}
                                  className="px-3 py-1.5 text-[10px] font-semibold border border-[#e5e0d8] text-[#777] rounded-lg hover:border-[#ec4899] hover:text-[#ec4899] transition-colors flex items-center gap-1"
                                >
                                  <Sparkles size={11} /> Guide
                                </button>
                                {!isDone && (
                                  <select
                                    value={a.status}
                                    onChange={e => updateAccount(a.id, { status: e.target.value })}
                                    className="text-[10px] px-2 py-1.5 border border-[#e5e0d8] rounded-lg outline-none"
                                  >
                                    <option value="not_started">Not Started</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="done">Done</option>
                                    <option value="skipped">Skip</option>
                                  </select>
                                )}
                                {isDone && (
                                  <span className="text-[10px] font-bold text-[#16a34a]">Done</span>
                                )}
                              </div>
                            </div>

                            {/* Handle input for in_progress or done */}
                            {(isActive || isDone) && (
                              <div className="mt-3 flex gap-2">
                                <input
                                  type="text"
                                  placeholder="Username / handle / URL"
                                  defaultValue={a.handle}
                                  onBlur={e => {
                                    if (e.target.value !== a.handle) updateAccount(a.id, { handle: e.target.value });
                                  }}
                                  className="flex-1 text-xs px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none"
                                />
                                <input
                                  type="text"
                                  placeholder="Notes"
                                  defaultValue={a.notes}
                                  onBlur={e => {
                                    if (e.target.value !== a.notes) updateAccount(a.id, { notes: e.target.value });
                                  }}
                                  className="flex-1 text-xs px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#ec4899] outline-none"
                                />
                              </div>
                            )}

                            {/* AI Guide panel */}
                            {activeGuide === a.id && (
                              <div className="mt-3 p-4 bg-[#fdf2f8] border border-[#ec4899]/20 rounded-xl">
                                <div className="flex items-center justify-between mb-2">
                                  <h4 className="text-xs font-bold text-[#1a1a1a] flex items-center gap-1">
                                    <Sparkles size={12} className="text-[#ec4899]" /> AI Setup Guide — {a.name}
                                  </h4>
                                  <button onClick={() => setActiveGuide(null)} className="text-[10px] text-[#aaa] hover:text-[#dc2626]">Close</button>
                                </div>
                                {loadingGuide ? (
                                  <div className="flex items-center gap-2 text-xs text-[#777] py-4">
                                    <Loader2 size={14} className="animate-spin" /> Generating setup guide...
                                  </div>
                                ) : (
                                  <pre className="text-[11px] text-[#555] whitespace-pre-wrap font-sans leading-relaxed max-h-[400px] overflow-auto">
                                    {guideContent}
                                  </pre>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Calendar */}
        {tab === 'calendar' && (
          <div>
            <h2 className="text-lg font-bold text-[#1a1a1a] mb-4">Content Calendar</h2>
            <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
              {posts.filter(p => p.scheduled_for || p.posted_at).length === 0 ? (
                <p className="text-sm text-[#aaa] text-center py-8">No scheduled or posted content yet.</p>
              ) : (
                <div className="space-y-3">
                  {posts
                    .filter(p => p.scheduled_for || p.posted_at)
                    .sort((a, b) => (b.scheduled_for || b.posted_at || '').localeCompare(a.scheduled_for || a.posted_at || ''))
                    .map((p: any) => {
                      const date = p.scheduled_for || p.posted_at || p.created_at;
                      return (
                        <div key={p.id} className="flex items-start gap-3 p-3 rounded-lg bg-[#faf9f7] border border-[#e5e0d8]">
                          <div className="text-center min-w-[48px]">
                            <div className="text-[10px] text-[#aaa]">
                              {new Date(date).toLocaleDateString('en-US', { month: 'short' })}
                            </div>
                            <div className="text-lg font-bold text-[#1a1a1a]">
                              {new Date(date).getDate()}
                            </div>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="capitalize text-xs font-semibold">{p.platform}</span>
                              <StatusBadge status={p.status} />
                            </div>
                            <p className="text-xs text-[#555] truncate">{p.content?.slice(0, 120)}</p>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function KPI({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-4">
      <div className="text-[10px] text-[#aaa] mb-1">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color || '#1a1a1a' }}>{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_COLORS[status] || STATUS_COLORS.draft;
  const Icon = status === 'posted' ? CheckCircle : status === 'scheduled' ? Clock : FileText;
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: s.bg, color: s.text }}>
      <Icon size={10} /> {status}
    </span>
  );
}

function PostRow({ post, onDelete, onStatusChange }: { post: any; onDelete: (id: string) => void; onStatusChange: (id: string, status: string) => void }) {
  const plat = PLATFORMS.find(p => p.id === post.platform);
  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-4 hover:border-[#ec4899] transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: plat?.color || '#999' }} />
            <span className="text-xs font-semibold capitalize">{post.platform}</span>
            <StatusBadge status={post.status} />
            <span className="text-[10px] text-[#aaa]">{post.code}</span>
          </div>
          <p className="text-xs text-[#555] line-clamp-2">{post.content?.slice(0, 200)}</p>
          {post.hashtags && <p className="text-[10px] text-[#aaa] mt-1 truncate">{post.hashtags.slice(0, 100)}</p>}
        </div>
        <div className="flex items-center gap-1 ml-2 shrink-0">
          {post.status === 'draft' && (
            <button
              onClick={() => onStatusChange(post.id, 'posted')}
              className="text-[10px] font-semibold text-[#16a34a] hover:underline"
            >
              Mark Posted
            </button>
          )}
          <button onClick={() => onDelete(post.id)} className="text-[#ccc] hover:text-[#dc2626] transition-colors ml-1">
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ProfileField({ label, value, onChange, placeholder, textarea }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; textarea?: boolean;
}) {
  const cls = "w-full px-3 py-2 border border-[#e0dbd4] rounded-lg text-xs bg-white outline-none focus:border-[#ec4899] focus:shadow-[0_0_0_3px_rgba(236,72,153,0.1)] placeholder:text-[#ccc]";
  return (
    <div>
      <label className="text-[10px] font-semibold text-[#888] uppercase tracking-wide">{label}</label>
      {textarea ? (
        <textarea value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className={`${cls} min-h-[60px] resize-y mt-0.5`} />
      ) : (
        <input value={value || ''} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className={`${cls} min-h-[36px] mt-0.5`} />
      )}
    </div>
  );
}
