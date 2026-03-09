'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  Instagram, Facebook, Sparkles, Calendar, PenTool, BarChart3,
  Plus, Send, Clock, CheckCircle, FileText, Trash2, RefreshCw,
  Settings, ExternalLink, CircleDot, SkipForward, Loader2, ChevronRight,
  TrendingUp, Users, Heart, Eye, Share2, MessageCircle, Image,
  ChevronDown, ChevronUp, ArrowUpRight, ArrowDownRight, Hash,
  LinkIcon, Globe, Zap, Target, Award, ThumbsUp, Video, BookOpen, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

const SF_API = `${API}/socialforge`;

// ============ PLATFORM CONFIG ============

const PLATFORMS = [
  { id: 'instagram', label: 'Instagram', icon: Instagram, color: '#E1306C', bgLight: '#fdf2f8' },
  { id: 'facebook', label: 'Facebook', icon: Facebook, color: '#1877F2', bgLight: '#eff6ff' },
  { id: 'x', label: 'X (Twitter)', icon: Globe, color: '#000000', bgLight: '#f5f5f5' },
  { id: 'tiktok', label: 'TikTok', icon: Video, color: '#00f2ea', bgLight: '#f0fdfa' },
  { id: 'linkedin', label: 'LinkedIn', icon: LinkIcon, color: '#0A66C2', bgLight: '#eff6ff' },
];

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  draft: { bg: '#f5f3ef', text: '#777' },
  scheduled: { bg: '#dbeafe', text: '#2563eb' },
  posted: { bg: '#dcfce7', text: '#16a34a' },
  failed: { bg: '#fef2f2', text: '#dc2626' },
};

// ============ MOCK DATA ============

const MOCK_CONNECTED_ACCOUNTS = [
  { id: 'ig-1', platform: 'instagram', handle: '@empire_workroom', displayName: 'Empire Workroom', avatar: 'E', followers: 2847, connected: true, lastSync: '2026-03-09T10:30:00Z', status: 'active' },
  { id: 'fb-1', platform: 'facebook', handle: 'EmpireWorkroom', displayName: 'Empire Workroom LLC', avatar: 'E', followers: 1203, connected: true, lastSync: '2026-03-09T10:30:00Z', status: 'active' },
  { id: 'x-1', platform: 'x', handle: '@empireworkroom', displayName: 'Empire Workroom', avatar: 'E', followers: 892, connected: true, lastSync: '2026-03-09T09:15:00Z', status: 'active' },
  { id: 'tt-1', platform: 'tiktok', handle: '@empire.workroom', displayName: 'Empire Workroom', avatar: 'E', followers: 5621, connected: true, lastSync: '2026-03-09T08:00:00Z', status: 'active' },
  { id: 'li-1', platform: 'linkedin', handle: 'empire-workroom', displayName: 'Empire Workroom', avatar: 'E', followers: 412, connected: false, lastSync: null, status: 'disconnected' },
];

const MOCK_SCHEDULED_POSTS = [
  { id: 'sp-1', platform: 'instagram', content: 'Transform your living room with our handcrafted Roman shades. Every fold tells a story of precision and luxury. #CustomDrapes #InteriorDesign #LuxuryLiving', scheduledFor: '2026-03-10T09:00:00Z', status: 'scheduled', mediaType: 'image', engagement: null },
  { id: 'sp-2', platform: 'facebook', content: 'Spring Sale: 20% off all custom window treatments! Book your free consultation today. Limited time offer for the DC Metro area.', scheduledFor: '2026-03-10T12:00:00Z', status: 'scheduled', mediaType: 'image', engagement: null },
  { id: 'sp-3', platform: 'x', content: 'Nothing beats natural light filtered through premium linen drapes. What\'s your favorite window treatment style? #HomeDecor #WindowTreatments', scheduledFor: '2026-03-11T08:30:00Z', status: 'scheduled', mediaType: 'text', engagement: null },
  { id: 'sp-4', platform: 'tiktok', content: 'Watch us transform this bay window from boring to breathtaking in 60 seconds! Full custom drapery installation timelapse.', scheduledFor: '2026-03-11T17:00:00Z', status: 'scheduled', mediaType: 'video', engagement: null },
  { id: 'sp-5', platform: 'instagram', content: 'Behind the scenes at the Empire Workroom: Hand-stitching the perfect pleat. Quality takes time, and we never rush perfection.', scheduledFor: '2026-03-12T10:00:00Z', status: 'scheduled', mediaType: 'image', engagement: null },
  { id: 'sp-6', platform: 'instagram', content: 'Client reveal day is always the best day! This Georgetown townhouse went from dated to stunning with our custom silk drapes.', scheduledFor: '2026-03-13T11:00:00Z', status: 'draft', mediaType: 'image', engagement: null },
  { id: 'sp-7', platform: 'facebook', content: 'Meet our team! We are a family of artisans dedicated to crafting the finest custom window treatments in the DC Metro area.', scheduledFor: '2026-03-14T09:00:00Z', status: 'draft', mediaType: 'image', engagement: null },
  { id: 'sp-8', platform: 'linkedin', content: 'How we built Empire Workroom from a single sewing machine to a full-service luxury window treatment studio. Our entrepreneurship story.', scheduledFor: '2026-03-15T08:00:00Z', status: 'draft', mediaType: 'text', engagement: null },
];

const MOCK_PAST_POSTS = [
  { id: 'pp-1', platform: 'instagram', content: 'Our latest motorized sheer installation in Bethesda. Swipe to see the before & after!', postedAt: '2026-03-08T10:00:00Z', status: 'posted', engagement: { likes: 234, comments: 18, shares: 12, reach: 3420, impressions: 4890 } },
  { id: 'pp-2', platform: 'facebook', content: 'Happy client spotlight! The Johnson family loves their new custom plantation shutters.', postedAt: '2026-03-07T12:00:00Z', status: 'posted', engagement: { likes: 89, comments: 7, shares: 5, reach: 1230, impressions: 1890 } },
  { id: 'pp-3', platform: 'tiktok', content: 'POV: You ordered custom drapes and installation day finally arrives #satisfying #homedecor', postedAt: '2026-03-07T17:00:00Z', status: 'posted', engagement: { likes: 1892, comments: 143, shares: 267, reach: 28400, impressions: 42100 } },
  { id: 'pp-4', platform: 'x', content: 'Pro tip: Measure twice, order once. Our free in-home consultation ensures perfect fit every time. Book yours today!', postedAt: '2026-03-06T09:00:00Z', status: 'posted', engagement: { likes: 45, comments: 3, shares: 8, reach: 890, impressions: 1240 } },
  { id: 'pp-5', platform: 'instagram', content: 'Fabric Friday! This week we are working with a stunning Belgian linen in oatmeal. Perfect for that relaxed luxury look.', postedAt: '2026-03-05T10:00:00Z', status: 'posted', engagement: { likes: 312, comments: 24, shares: 19, reach: 4100, impressions: 5670 } },
  { id: 'pp-6', platform: 'instagram', content: 'Spring collection preview: Soft pastels meet clean lines. Our new curated fabric collection drops next week!', postedAt: '2026-03-04T10:00:00Z', status: 'posted', engagement: { likes: 278, comments: 31, shares: 22, reach: 3890, impressions: 5230 } },
];

const MOCK_ANALYTICS = {
  overview: {
    totalFollowers: 10975,
    followerGrowth: 342,
    followerGrowthPct: 3.2,
    engagementRate: 4.7,
    engagementChange: 0.8,
    totalReach: 42930,
    reachChange: 12.3,
    totalImpressions: 61020,
    impressionsChange: 8.7,
    postsThisWeek: 6,
    postsLastWeek: 4,
  },
  platformBreakdown: [
    { platform: 'instagram', followers: 2847, engagement: 5.2, reach: 16080, posts: 12, topTime: '10:00 AM' },
    { platform: 'facebook', followers: 1203, engagement: 3.1, reach: 5120, posts: 8, topTime: '12:00 PM' },
    { platform: 'x', followers: 892, engagement: 2.4, reach: 3130, posts: 10, topTime: '8:30 AM' },
    { platform: 'tiktok', followers: 5621, engagement: 8.9, reach: 15600, posts: 4, topTime: '5:00 PM' },
    { platform: 'linkedin', followers: 412, engagement: 1.8, reach: 3000, posts: 2, topTime: '9:00 AM' },
  ],
  weeklyData: [
    { day: 'Mon', posts: 2, engagement: 156, reach: 4200 },
    { day: 'Tue', posts: 1, engagement: 89, reach: 2100 },
    { day: 'Wed', posts: 1, engagement: 234, reach: 5800 },
    { day: 'Thu', posts: 0, engagement: 0, reach: 0 },
    { day: 'Fri', posts: 2, engagement: 312, reach: 7200 },
    { day: 'Sat', posts: 0, engagement: 45, reach: 890 },
    { day: 'Sun', posts: 0, engagement: 23, reach: 450 },
  ],
  topHashtags: [
    { tag: '#CustomDrapes', uses: 18, avgEngagement: 4.8 },
    { tag: '#InteriorDesign', uses: 24, avgEngagement: 5.1 },
    { tag: '#LuxuryLiving', uses: 15, avgEngagement: 4.2 },
    { tag: '#WindowTreatments', uses: 20, avgEngagement: 3.9 },
    { tag: '#HomeDecor', uses: 22, avgEngagement: 4.5 },
    { tag: '#DCMetro', uses: 10, avgEngagement: 3.2 },
  ],
};

// ============ TAB CONFIG ============

type Tab = 'dashboard' | 'calendar' | 'compose' | 'analytics' | 'accounts' | 'payments' | 'docs';

const NAV_TABS: { id: Tab; label: string; icon: any }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'calendar', label: 'Calendar', icon: Calendar },
  { id: 'compose', label: 'Compose', icon: PenTool },
  { id: 'analytics', label: 'Analytics', icon: TrendingUp },
  { id: 'accounts', label: 'Accounts', icon: Users },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
];

// ============ MAIN COMPONENT ============

export default function SocialForgePage() {
  const [tab, setTab] = useState<Tab>('dashboard');
  const [loading, setLoading] = useState(false);

  // Dashboard state
  const [connectedAccounts, setConnectedAccounts] = useState(MOCK_CONNECTED_ACCOUNTS);
  const [scheduledPosts, setScheduledPosts] = useState(MOCK_SCHEDULED_POSTS);
  const [pastPosts, setPastPosts] = useState(MOCK_PAST_POSTS);
  const [analytics, setAnalytics] = useState(MOCK_ANALYTICS);

  // Compose state
  const [composeText, setComposeText] = useState('');
  const [composeHashtags, setComposeHashtags] = useState('');
  const [composePlatforms, setComposePlatforms] = useState<string[]>(['instagram']);
  const [composeScheduleDate, setComposeScheduleDate] = useState('');
  const [composeScheduleTime, setComposeScheduleTime] = useState('');
  const [composeSaving, setComposeSaving] = useState(false);
  const [composeMediaName, setComposeMediaName] = useState('');

  // Calendar state
  const [calendarMonth, setCalendarMonth] = useState(new Date().getMonth());
  const [calendarYear, setCalendarYear] = useState(new Date().getFullYear());

  // Try to load real data, fall back to mock
  const loadData = async () => {
    setLoading(true);
    try {
      const [dash, postList] = await Promise.all([
        fetch(`${SF_API}/dashboard`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${SF_API}/posts`).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      if (dash) {
        // Merge real data if available
      }
      if (postList && Array.isArray(postList) && postList.length > 0) {
        // Could merge with mock data
      }
    } catch (_err) {
      // Use mock data
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  // Compose handlers
  const togglePlatform = (platformId: string) => {
    setComposePlatforms(prev =>
      prev.includes(platformId)
        ? prev.filter(p => p !== platformId)
        : [...prev, platformId]
    );
  };

  const handleCompose = async () => {
    if (!composeText.trim() || composePlatforms.length === 0) return;
    setComposeSaving(true);
    const scheduledFor = composeScheduleDate && composeScheduleTime
      ? `${composeScheduleDate}T${composeScheduleTime}:00Z`
      : null;

    // Create a post for each selected platform
    const newPosts = composePlatforms.map(plat => ({
      id: `sp-${Date.now()}-${plat}`,
      platform: plat,
      content: composeText + (composeHashtags ? '\n\n' + composeHashtags : ''),
      scheduledFor: scheduledFor || '',
      status: scheduledFor ? 'scheduled' : 'draft',
      mediaType: composeMediaName ? 'image' : 'text',
      engagement: null,
    }));

    // Try API first
    try {
      for (const post of newPosts) {
        await fetch(`${SF_API}/posts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            platform: post.platform,
            content: post.content,
            hashtags: composeHashtags,
            scheduled_for: scheduledFor,
            status: post.status,
          }),
        });
      }
    } catch (_err) {
      // Use local state
    }

    setScheduledPosts(prev => [...newPosts, ...prev]);
    setComposeText('');
    setComposeHashtags('');
    setComposeScheduleDate('');
    setComposeScheduleTime('');
    setComposeMediaName('');
    setComposeSaving(false);
    setTab('calendar');
  };

  const handleDeletePost = (id: string) => {
    setScheduledPosts(prev => prev.filter(p => p.id !== id));
    setPastPosts(prev => prev.filter(p => p.id !== id));
    fetch(`${SF_API}/posts/${id}`, { method: 'DELETE' }).catch(() => {});
  };

  const handleStatusChange = (id: string, status: string) => {
    setScheduledPosts(prev => prev.map(p => p.id === id ? { ...p, status } : p));
    fetch(`${SF_API}/posts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }).catch(() => {});
  };

  const handleDisconnectAccount = (id: string) => {
    setConnectedAccounts(prev =>
      prev.map(a => a.id === id ? { ...a, connected: false, status: 'disconnected' } : a)
    );
  };

  const handleConnectAccount = (id: string) => {
    setConnectedAccounts(prev =>
      prev.map(a => a.id === id ? { ...a, connected: true, status: 'active', lastSync: new Date().toISOString() } : a)
    );
  };

  // Helpers
  const allPosts = [...scheduledPosts, ...pastPosts];
  const totalFollowers = connectedAccounts.filter(a => a.connected).reduce((s, a) => s + a.followers, 0);
  const queueCount = scheduledPosts.filter(p => p.status === 'scheduled').length;
  const draftCount = scheduledPosts.filter(p => p.status === 'draft').length;

  // Calendar helpers
  const getDaysInMonth = (month: number, year: number) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (month: number, year: number) => new Date(year, month, 1).getDay();
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  const getPostsForDate = (day: number) => {
    const dateStr = `${calendarYear}-${String(calendarMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return allPosts.filter(p => {
      const pDate = (p as any).scheduledFor || (p as any).postedAt || '';
      return pDate.startsWith(dateStr);
    });
  };

  return (
    <div className="h-full flex flex-col overflow-auto" style={{ background: '#f5f2ed' }}>
      {/* Header */}
      <div style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0', padding: '16px 36px' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#ec4899] to-[#a855f7] flex items-center justify-center">
              <Sparkles size={18} className="text-white" />
            </div>
            <div>
              <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>SocialForge</h1>
              <p style={{ fontSize: 13, color: '#aaa', margin: 0 }}>AI-Powered Social Media Manager</p>
            </div>
          </div>
          <button onClick={loadData} className="text-[#aaa] hover:text-[#ec4899] transition-colors">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mt-4">
          {NAV_TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`filter-tab ${tab === t.id ? 'active' : ''}`}
              style={tab === t.id ? { background: '#ec4899', borderColor: '#ec4899' } : {}}
            >
              <t.icon size={14} style={{ marginRight: 4 }} /> {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto" style={{ padding: '24px 36px' }}>

        {/* ==================== DASHBOARD TAB ==================== */}
        {tab === 'dashboard' && (
          <div>
            {/* KPI Row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <DashKpi label="Total Followers" value={totalFollowers.toLocaleString()} icon={Users} change="+3.2%" positive />
              <DashKpi label="Engagement Rate" value={`${analytics.overview.engagementRate}%`} icon={Heart} change={`+${analytics.overview.engagementChange}%`} positive />
              <DashKpi label="Post Queue" value={queueCount.toString()} icon={Clock} sublabel={`${draftCount} drafts`} />
              <DashKpi label="Weekly Reach" value={analytics.overview.totalReach.toLocaleString()} icon={Eye} change={`+${analytics.overview.reachChange}%`} positive />
            </div>

            {/* Connected Accounts Strip */}
            <div className="empire-card" style={{ marginBottom: 16 }}>
              <div className="section-label" style={{ marginBottom: 12 }}>Connected Accounts</div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {connectedAccounts.map(acc => {
                  const plat = PLATFORMS.find(p => p.id === acc.platform);
                  const Icon = plat?.icon || Globe;
                  return (
                    <div key={acc.id} style={{
                      padding: '12px',
                      borderRadius: 12,
                      background: acc.connected ? plat?.bgLight || '#f5f5f5' : '#f9f9f9',
                      border: `1px solid ${acc.connected ? plat?.color + '30' : '#e5e5e5'}`,
                      opacity: acc.connected ? 1 : 0.6,
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        <Icon size={16} style={{ color: plat?.color }} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{plat?.label}</span>
                        {acc.connected && <CheckCircle size={12} style={{ color: '#16a34a' }} />}
                      </div>
                      <div style={{ fontSize: 11, color: '#777' }}>{acc.handle}</div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', marginTop: 4 }}>
                        {acc.followers.toLocaleString()}
                      </div>
                      <div style={{ fontSize: 10, color: '#aaa' }}>followers</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Upcoming Posts */}
            <div className="empire-card" style={{ marginBottom: 16 }}>
              <div className="flex items-center justify-between mb-3">
                <div className="section-label">Upcoming Scheduled Posts</div>
                <button
                  onClick={() => setTab('compose')}
                  style={{ padding: '6px 14px', fontSize: 11, fontWeight: 600, background: '#ec4899', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                  className="hover:bg-[#db2777] transition-colors"
                >
                  <Plus size={12} /> New Post
                </button>
              </div>
              {scheduledPosts.filter(p => p.status === 'scheduled').length === 0 ? (
                <div style={{ padding: '24px 0', textAlign: 'center' }}>
                  <Calendar size={28} className="mx-auto mb-2" style={{ color: '#ddd' }} />
                  <p style={{ fontSize: 12, color: '#aaa' }}>No scheduled posts. Create one to get started!</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {scheduledPosts.filter(p => p.status === 'scheduled').slice(0, 5).map(post => (
                    <PostRow key={post.id} post={post} onDelete={handleDeletePost} onStatusChange={handleStatusChange} />
                  ))}
                </div>
              )}
            </div>

            {/* Recent Performance */}
            <div className="empire-card">
              <div className="section-label" style={{ marginBottom: 12 }}>Recent Post Performance</div>
              <div className="space-y-2">
                {pastPosts.slice(0, 4).map(post => {
                  const plat = PLATFORMS.find(p => p.id === post.platform);
                  const Icon = plat?.icon || Globe;
                  const eng = post.engagement;
                  return (
                    <div key={post.id} style={{ padding: '12px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Icon size={14} style={{ color: plat?.color }} />
                            <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }} className="capitalize">{post.platform}</span>
                            <SFStatusBadge status={post.status} />
                            <span style={{ fontSize: 10, color: '#aaa' }}>
                              {new Date(post.postedAt!).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </span>
                          </div>
                          <p style={{ fontSize: 12, color: '#555' }} className="line-clamp-1">{post.content.slice(0, 120)}</p>
                        </div>
                        {eng && (
                          <div className="flex items-center gap-3 ml-3 shrink-0" style={{ fontSize: 11 }}>
                            <span className="flex items-center gap-1 text-[#777]"><Heart size={11} /> {eng.likes}</span>
                            <span className="flex items-center gap-1 text-[#777]"><MessageCircle size={11} /> {eng.comments}</span>
                            <span className="flex items-center gap-1 text-[#777]"><Share2 size={11} /> {eng.shares}</span>
                            <span className="flex items-center gap-1 text-[#777]"><Eye size={11} /> {eng.reach.toLocaleString()}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ==================== CALENDAR TAB ==================== */}
        {tab === 'calendar' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Content Calendar</h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    if (calendarMonth === 0) { setCalendarMonth(11); setCalendarYear(y => y - 1); }
                    else setCalendarMonth(m => m - 1);
                  }}
                  style={{ padding: '6px 12px', fontSize: 12, border: '1px solid #ece8e0', borderRadius: 8, background: '#fff', cursor: 'pointer' }}
                  className="hover:border-[#ec4899] transition-colors"
                >
                  &larr;
                </button>
                <span style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a', minWidth: 140, textAlign: 'center' }}>
                  {monthNames[calendarMonth]} {calendarYear}
                </span>
                <button
                  onClick={() => {
                    if (calendarMonth === 11) { setCalendarMonth(0); setCalendarYear(y => y + 1); }
                    else setCalendarMonth(m => m + 1);
                  }}
                  style={{ padding: '6px 12px', fontSize: 12, border: '1px solid #ece8e0', borderRadius: 8, background: '#fff', cursor: 'pointer' }}
                  className="hover:border-[#ec4899] transition-colors"
                >
                  &rarr;
                </button>
              </div>
            </div>

            <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
              {/* Day headers */}
              <div className="grid grid-cols-7" style={{ borderBottom: '1px solid #ece8e0' }}>
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(d => (
                  <div key={d} style={{ padding: '10px 8px', fontSize: 11, fontWeight: 600, color: '#aaa', textAlign: 'center', background: '#faf9f7' }}>
                    {d}
                  </div>
                ))}
              </div>

              {/* Calendar grid */}
              <div className="grid grid-cols-7">
                {/* Empty cells for days before month starts */}
                {Array.from({ length: getFirstDayOfMonth(calendarMonth, calendarYear) }).map((_, i) => (
                  <div key={`empty-${i}`} style={{ minHeight: 90, borderRight: '1px solid #f0ece5', borderBottom: '1px solid #f0ece5', background: '#faf9f7' }} />
                ))}

                {/* Actual days */}
                {Array.from({ length: getDaysInMonth(calendarMonth, calendarYear) }).map((_, i) => {
                  const day = i + 1;
                  const dayPosts = getPostsForDate(day);
                  const isToday = day === new Date().getDate() && calendarMonth === new Date().getMonth() && calendarYear === new Date().getFullYear();
                  return (
                    <div key={day} style={{
                      minHeight: 90,
                      padding: '6px',
                      borderRight: '1px solid #f0ece5',
                      borderBottom: '1px solid #f0ece5',
                      background: isToday ? '#fdf2f8' : '#fff',
                    }}>
                      <div style={{
                        fontSize: 11,
                        fontWeight: isToday ? 700 : 500,
                        color: isToday ? '#ec4899' : '#1a1a1a',
                        marginBottom: 4,
                      }}>
                        {day}
                      </div>
                      <div className="space-y-1">
                        {dayPosts.slice(0, 3).map(post => {
                          const plat = PLATFORMS.find(p => p.id === post.platform);
                          return (
                            <div key={post.id} style={{
                              padding: '2px 6px',
                              fontSize: 9,
                              borderRadius: 4,
                              background: plat?.color + '18',
                              color: plat?.color,
                              fontWeight: 600,
                              overflow: 'hidden',
                              whiteSpace: 'nowrap',
                              textOverflow: 'ellipsis',
                              border: `1px solid ${plat?.color}30`,
                            }}>
                              {plat?.label?.slice(0, 2)} - {post.content.slice(0, 20)}...
                            </div>
                          );
                        })}
                        {dayPosts.length > 3 && (
                          <div style={{ fontSize: 9, color: '#aaa' }}>+{dayPosts.length - 3} more</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Scheduled list below calendar */}
            <div className="empire-card" style={{ marginTop: 16 }}>
              <div className="section-label" style={{ marginBottom: 10 }}>All Scheduled & Draft Posts</div>
              {scheduledPosts.length === 0 ? (
                <p style={{ fontSize: 12, color: '#aaa', textAlign: 'center', padding: '20px 0' }}>No posts in the queue.</p>
              ) : (
                <div className="space-y-2">
                  {scheduledPosts
                    .sort((a, b) => (a.scheduledFor || '').localeCompare(b.scheduledFor || ''))
                    .map(post => (
                      <PostRow key={post.id} post={post} onDelete={handleDeletePost} onStatusChange={handleStatusChange} />
                    ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ==================== COMPOSE TAB ==================== */}
        {tab === 'compose' && (
          <div style={{ maxWidth: 680 }}>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', marginBottom: 16 }}>Compose Post</h2>

            <div className="empire-card space-y-5">
              {/* Platform Selection */}
              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 8 }}>Platforms</label>
                <div className="flex flex-wrap gap-2">
                  {PLATFORMS.map(p => {
                    const selected = composePlatforms.includes(p.id);
                    const account = connectedAccounts.find(a => a.platform === p.id);
                    const isConnected = account?.connected;
                    return (
                      <button
                        key={p.id}
                        onClick={() => isConnected && togglePlatform(p.id)}
                        disabled={!isConnected}
                        style={{
                          padding: '8px 14px',
                          fontSize: 12,
                          fontWeight: 600,
                          borderRadius: 10,
                          border: `2px solid ${selected ? p.color : '#ece8e0'}`,
                          background: selected ? p.bgLight : '#fff',
                          color: selected ? p.color : isConnected ? '#777' : '#ccc',
                          cursor: isConnected ? 'pointer' : 'not-allowed',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          transition: 'all 0.15s',
                          opacity: isConnected ? 1 : 0.5,
                        }}
                      >
                        <p.icon size={14} />
                        {p.label}
                        {selected && <CheckCircle size={12} />}
                      </button>
                    );
                  })}
                </div>
                <p style={{ fontSize: 10, color: '#aaa', marginTop: 6 }}>Select one or more platforms to post to</p>
              </div>

              {/* Post Text */}
              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Post Content</label>
                <textarea
                  value={composeText}
                  onChange={e => setComposeText(e.target.value)}
                  rows={6}
                  style={{ width: '100%', padding: '12px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 12, outline: 'none', resize: 'none', lineHeight: 1.6 }}
                  className="focus:border-[#ec4899]"
                  placeholder="Write your post content here. Be engaging, authentic, and include a call to action..."
                />
                <div className="flex items-center justify-between mt-1">
                  <span style={{ fontSize: 10, color: '#aaa' }}>{composeText.length} characters</span>
                  <div className="flex gap-2" style={{ fontSize: 10, color: '#aaa' }}>
                    {composePlatforms.includes('x') && (
                      <span style={{ color: composeText.length > 280 ? '#dc2626' : '#aaa' }}>X limit: {280 - composeText.length}</span>
                    )}
                    {composePlatforms.includes('instagram') && (
                      <span style={{ color: composeText.length > 2200 ? '#dc2626' : '#aaa' }}>IG limit: {2200 - composeText.length}</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Hashtags */}
              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Hashtags</label>
                <textarea
                  value={composeHashtags}
                  onChange={e => setComposeHashtags(e.target.value)}
                  rows={2}
                  style={{ width: '100%', padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 12, outline: 'none', resize: 'none' }}
                  className="focus:border-[#ec4899]"
                  placeholder="#CustomDrapes #InteriorDesign #LuxuryLiving #HomeDecor"
                />
              </div>

              {/* Media Upload Placeholder */}
              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Media</label>
                <div
                  style={{
                    border: '2px dashed #ece8e0',
                    borderRadius: 12,
                    padding: '24px 16px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    background: composeMediaName ? '#fdf2f8' : '#faf9f7',
                    transition: 'all 0.15s',
                  }}
                  className="hover:border-[#ec4899]"
                  onClick={() => {
                    if (!composeMediaName) {
                      setComposeMediaName('photo_upload_placeholder.jpg');
                    } else {
                      setComposeMediaName('');
                    }
                  }}
                >
                  {composeMediaName ? (
                    <div className="flex items-center justify-center gap-2">
                      <Image size={18} style={{ color: '#ec4899' }} />
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#ec4899' }}>{composeMediaName}</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); setComposeMediaName(''); }}
                        style={{ fontSize: 10, color: '#aaa', background: 'none', border: 'none', cursor: 'pointer' }}
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <>
                      <Image size={24} className="mx-auto mb-2" style={{ color: '#ddd' }} />
                      <p style={{ fontSize: 12, color: '#777', margin: 0 }}>Click to add image or video</p>
                      <p style={{ fontSize: 10, color: '#aaa', margin: '4px 0 0' }}>JPG, PNG, MP4 up to 50MB</p>
                    </>
                  )}
                </div>
              </div>

              {/* Schedule */}
              <div>
                <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Schedule (optional)</label>
                <div className="flex gap-3">
                  <input
                    type="date"
                    value={composeScheduleDate}
                    onChange={e => setComposeScheduleDate(e.target.value)}
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, outline: 'none', flex: 1 }}
                    className="focus:border-[#ec4899]"
                  />
                  <input
                    type="time"
                    value={composeScheduleTime}
                    onChange={e => setComposeScheduleTime(e.target.value)}
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, outline: 'none', flex: 1 }}
                    className="focus:border-[#ec4899]"
                  />
                </div>
                <p style={{ fontSize: 10, color: '#aaa', marginTop: 4 }}>Leave empty to save as draft</p>
              </div>

              {/* Preview */}
              {composeText.trim() && (
                <div style={{ padding: 16, background: '#fdf2f8', border: '1px solid rgba(236,72,153,0.15)', borderRadius: 14 }}>
                  <div className="section-label" style={{ marginBottom: 8, color: '#ec4899' }}>Preview</div>
                  <div className="flex gap-2 mb-2">
                    {composePlatforms.map(platId => {
                      const p = PLATFORMS.find(pp => pp.id === platId);
                      return p ? (
                        <span key={platId} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6, background: p.color + '18', color: p.color, fontWeight: 600 }}>
                          {p.label}
                        </span>
                      ) : null;
                    })}
                  </div>
                  <p style={{ fontSize: 12, color: '#555', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                    {composeText}
                  </p>
                  {composeHashtags && (
                    <p style={{ fontSize: 11, color: '#0A66C2', marginTop: 8 }}>{composeHashtags}</p>
                  )}
                </div>
              )}

              {/* Submit */}
              <div className="flex items-center gap-3">
                <button
                  onClick={handleCompose}
                  disabled={composeSaving || !composeText.trim() || composePlatforms.length === 0}
                  style={{
                    padding: '12px 28px',
                    fontSize: 13,
                    fontWeight: 600,
                    background: '#ec4899',
                    color: '#fff',
                    borderRadius: 10,
                    border: 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    opacity: composeSaving || !composeText.trim() || composePlatforms.length === 0 ? 0.5 : 1,
                  }}
                  className="hover:bg-[#db2777] transition-colors"
                >
                  {composeSaving ? (
                    <><Loader2 size={14} className="animate-spin" /> Saving...</>
                  ) : composeScheduleDate ? (
                    <><Clock size={14} /> Schedule Post</>
                  ) : (
                    <><Send size={14} /> Save as Draft</>
                  )}
                </button>
                <span style={{ fontSize: 11, color: '#aaa' }}>
                  Posting to {composePlatforms.length} platform{composePlatforms.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ==================== ANALYTICS TAB ==================== */}
        {tab === 'analytics' && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', marginBottom: 16 }}>Analytics</h2>

            {/* Overview KPIs */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <DashKpi label="Total Followers" value={analytics.overview.totalFollowers.toLocaleString()} icon={Users} change={`+${analytics.overview.followerGrowth}`} positive />
              <DashKpi label="Engagement Rate" value={`${analytics.overview.engagementRate}%`} icon={Heart} change={`+${analytics.overview.engagementChange}%`} positive />
              <DashKpi label="Total Reach" value={analytics.overview.totalReach.toLocaleString()} icon={Eye} change={`+${analytics.overview.reachChange}%`} positive />
              <DashKpi label="Impressions" value={analytics.overview.totalImpressions.toLocaleString()} icon={Target} change={`+${analytics.overview.impressionsChange}%`} positive />
            </div>

            {/* Platform Breakdown */}
            <div className="empire-card" style={{ marginBottom: 16 }}>
              <div className="section-label" style={{ marginBottom: 12 }}>Platform Breakdown</div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #ece8e0' }}>
                      <th style={{ textAlign: 'left', padding: '10px 12px', color: '#aaa', fontWeight: 500 }}>Platform</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: '#aaa', fontWeight: 500 }}>Followers</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: '#aaa', fontWeight: 500 }}>Engagement</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: '#aaa', fontWeight: 500 }}>Reach</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: '#aaa', fontWeight: 500 }}>Posts</th>
                      <th style={{ textAlign: 'right', padding: '10px 12px', color: '#aaa', fontWeight: 500 }}>Best Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.platformBreakdown.map(row => {
                      const plat = PLATFORMS.find(p => p.id === row.platform);
                      const Icon = plat?.icon || Globe;
                      return (
                        <tr key={row.platform} style={{ borderBottom: '1px solid #f5f3ef' }} className="hover:bg-[#faf9f7] transition-colors">
                          <td style={{ padding: '12px' }}>
                            <div className="flex items-center gap-2">
                              <Icon size={14} style={{ color: plat?.color }} />
                              <span style={{ fontWeight: 600, color: '#1a1a1a' }}>{plat?.label}</span>
                            </div>
                          </td>
                          <td style={{ textAlign: 'right', padding: '12px', fontWeight: 600 }}>{row.followers.toLocaleString()}</td>
                          <td style={{ textAlign: 'right', padding: '12px' }}>
                            <span style={{
                              padding: '2px 8px',
                              borderRadius: 6,
                              background: row.engagement > 4 ? '#dcfce7' : row.engagement > 2 ? '#fef9c3' : '#fef2f2',
                              color: row.engagement > 4 ? '#16a34a' : row.engagement > 2 ? '#ca8a04' : '#dc2626',
                              fontWeight: 600,
                            }}>
                              {row.engagement}%
                            </span>
                          </td>
                          <td style={{ textAlign: 'right', padding: '12px', color: '#555' }}>{row.reach.toLocaleString()}</td>
                          <td style={{ textAlign: 'right', padding: '12px', color: '#555' }}>{row.posts}</td>
                          <td style={{ textAlign: 'right', padding: '12px', color: '#777' }}>{row.topTime}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Weekly Activity Chart (Bar visualization) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <div className="empire-card">
                <div className="section-label" style={{ marginBottom: 12 }}>Weekly Engagement</div>
                <div className="flex items-end gap-2" style={{ height: 120 }}>
                  {analytics.weeklyData.map(d => {
                    const maxEng = Math.max(...analytics.weeklyData.map(x => x.engagement), 1);
                    const height = d.engagement > 0 ? Math.max((d.engagement / maxEng) * 100, 4) : 4;
                    return (
                      <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                        <span style={{ fontSize: 9, color: '#777', fontWeight: 600 }}>{d.engagement || '-'}</span>
                        <div style={{
                          width: '100%',
                          height: `${height}px`,
                          background: d.engagement > 0 ? 'linear-gradient(to top, #ec4899, #f472b6)' : '#f0ece5',
                          borderRadius: '4px 4px 0 0',
                          transition: 'height 0.3s',
                        }} />
                        <span style={{ fontSize: 10, color: '#aaa' }}>{d.day}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="empire-card">
                <div className="section-label" style={{ marginBottom: 12 }}>Weekly Reach</div>
                <div className="flex items-end gap-2" style={{ height: 120 }}>
                  {analytics.weeklyData.map(d => {
                    const maxReach = Math.max(...analytics.weeklyData.map(x => x.reach), 1);
                    const height = d.reach > 0 ? Math.max((d.reach / maxReach) * 100, 4) : 4;
                    return (
                      <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                        <span style={{ fontSize: 9, color: '#777', fontWeight: 600 }}>{d.reach > 0 ? (d.reach / 1000).toFixed(1) + 'k' : '-'}</span>
                        <div style={{
                          width: '100%',
                          height: `${height}px`,
                          background: d.reach > 0 ? 'linear-gradient(to top, #a855f7, #c084fc)' : '#f0ece5',
                          borderRadius: '4px 4px 0 0',
                          transition: 'height 0.3s',
                        }} />
                        <span style={{ fontSize: 10, color: '#aaa' }}>{d.day}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Top Posts & Hashtags */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="empire-card">
                <div className="section-label" style={{ marginBottom: 12 }}>Top Performing Posts</div>
                <div className="space-y-3">
                  {[...pastPosts]
                    .sort((a, b) => (b.engagement?.likes || 0) - (a.engagement?.likes || 0))
                    .slice(0, 4)
                    .map((post, idx) => {
                      const plat = PLATFORMS.find(p => p.id === post.platform);
                      const Icon = plat?.icon || Globe;
                      return (
                        <div key={post.id} className="flex items-start gap-3" style={{ padding: '10px 12px', borderRadius: 10, background: '#faf9f7', border: '1px solid #f0ece5' }}>
                          <div style={{
                            width: 24, height: 24, borderRadius: 6,
                            background: idx === 0 ? '#fef9c3' : idx === 1 ? '#f5f5f5' : idx === 2 ? '#fff7ed' : '#f5f3ef',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 11, fontWeight: 700,
                            color: idx === 0 ? '#ca8a04' : idx === 1 ? '#737373' : idx === 2 ? '#ea580c' : '#aaa',
                          }}>
                            {idx + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <Icon size={12} style={{ color: plat?.color }} />
                              <span style={{ fontSize: 11, fontWeight: 600 }} className="capitalize">{post.platform}</span>
                            </div>
                            <p style={{ fontSize: 11, color: '#555' }} className="line-clamp-2">{post.content.slice(0, 80)}...</p>
                            <div className="flex gap-3 mt-1" style={{ fontSize: 10, color: '#aaa' }}>
                              <span>{post.engagement?.likes} likes</span>
                              <span>{post.engagement?.comments} comments</span>
                              <span>{post.engagement?.reach.toLocaleString()} reach</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              <div className="empire-card">
                <div className="section-label" style={{ marginBottom: 12 }}>Top Hashtags</div>
                <div className="space-y-2">
                  {analytics.topHashtags.map(ht => {
                    const maxUses = Math.max(...analytics.topHashtags.map(h => h.uses));
                    return (
                      <div key={ht.tag} style={{ padding: '10px 12px', borderRadius: 10, background: '#faf9f7', border: '1px solid #f0ece5' }}>
                        <div className="flex items-center justify-between mb-1">
                          <span style={{ fontSize: 12, fontWeight: 600, color: '#0A66C2' }}>{ht.tag}</span>
                          <span style={{ fontSize: 10, color: '#aaa' }}>{ht.uses} uses</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div style={{ flex: 1, height: 6, background: '#f0ece5', borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{
                              height: '100%',
                              width: `${(ht.uses / maxUses) * 100}%`,
                              background: 'linear-gradient(to right, #ec4899, #a855f7)',
                              borderRadius: 3,
                            }} />
                          </div>
                          <span style={{ fontSize: 10, color: '#16a34a', fontWeight: 600 }}>{ht.avgEngagement}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Follower Growth */}
            <div className="empire-card" style={{ marginTop: 16 }}>
              <div className="section-label" style={{ marginBottom: 12 }}>Follower Growth (Last 30 Days)</div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                {analytics.platformBreakdown.map(row => {
                  const plat = PLATFORMS.find(p => p.id === row.platform);
                  const Icon = plat?.icon || Globe;
                  const growth = Math.floor(Math.random() * 80) + 20; // Mock growth number
                  return (
                    <div key={row.platform} style={{ padding: '14px 12px', borderRadius: 10, background: plat?.bgLight || '#f5f5f5', border: `1px solid ${plat?.color}20` }}>
                      <div className="flex items-center gap-2 mb-2">
                        <Icon size={14} style={{ color: plat?.color }} />
                        <span style={{ fontSize: 11, fontWeight: 600 }}>{plat?.label}</span>
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{row.followers.toLocaleString()}</div>
                      <div className="flex items-center gap-1 mt-1">
                        <ArrowUpRight size={11} style={{ color: '#16a34a' }} />
                        <span style={{ fontSize: 10, color: '#16a34a', fontWeight: 600 }}>+{growth}</span>
                        <span style={{ fontSize: 10, color: '#aaa' }}>this month</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ==================== ACCOUNTS TAB ==================== */}
        {tab === 'accounts' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Connected Accounts</h2>
              <button
                style={{ padding: '8px 16px', fontSize: 12, fontWeight: 600, background: '#ec4899', color: '#fff', borderRadius: 10, border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}
                className="hover:bg-[#db2777] transition-colors"
              >
                <Plus size={14} /> Connect Account
              </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
              <div className="empire-card">
                <div className="kpi-label">Connected</div>
                <div className="kpi-value" style={{ color: '#16a34a' }}>{connectedAccounts.filter(a => a.connected).length}</div>
              </div>
              <div className="empire-card">
                <div className="kpi-label">Disconnected</div>
                <div className="kpi-value" style={{ color: '#dc2626' }}>{connectedAccounts.filter(a => !a.connected).length}</div>
              </div>
              <div className="empire-card">
                <div className="kpi-label">Total Followers</div>
                <div className="kpi-value" style={{ color: '#ec4899' }}>{totalFollowers.toLocaleString()}</div>
              </div>
            </div>

            {/* Accounts Table */}
            <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #ece8e0', background: '#faf9f7' }}>
                    <th style={{ textAlign: 'left', padding: '12px 16px', color: '#aaa', fontWeight: 500 }}>Platform</th>
                    <th style={{ textAlign: 'left', padding: '12px 16px', color: '#aaa', fontWeight: 500 }}>Handle</th>
                    <th style={{ textAlign: 'right', padding: '12px 16px', color: '#aaa', fontWeight: 500 }}>Followers</th>
                    <th style={{ textAlign: 'center', padding: '12px 16px', color: '#aaa', fontWeight: 500 }}>Status</th>
                    <th style={{ textAlign: 'right', padding: '12px 16px', color: '#aaa', fontWeight: 500 }}>Last Sync</th>
                    <th style={{ textAlign: 'right', padding: '12px 16px', color: '#aaa', fontWeight: 500 }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {connectedAccounts.map(acc => {
                    const plat = PLATFORMS.find(p => p.id === acc.platform);
                    const Icon = plat?.icon || Globe;
                    return (
                      <tr key={acc.id} style={{ borderBottom: '1px solid #f5f3ef' }} className="hover:bg-[#faf9f7] transition-colors">
                        <td style={{ padding: '14px 16px' }}>
                          <div className="flex items-center gap-3">
                            <div style={{
                              width: 32, height: 32, borderRadius: 8,
                              background: plat?.bgLight || '#f5f5f5',
                              display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                              <Icon size={16} style={{ color: plat?.color }} />
                            </div>
                            <div>
                              <div style={{ fontWeight: 600, color: '#1a1a1a' }}>{plat?.label}</div>
                              <div style={{ fontSize: 10, color: '#aaa' }}>{acc.displayName}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <span style={{ fontWeight: 600, color: '#ec4899' }}>{acc.handle}</span>
                        </td>
                        <td style={{ textAlign: 'right', padding: '14px 16px', fontWeight: 600 }}>
                          {acc.followers.toLocaleString()}
                        </td>
                        <td style={{ textAlign: 'center', padding: '14px 16px' }}>
                          <span style={{
                            padding: '4px 10px',
                            borderRadius: 6,
                            fontSize: 10,
                            fontWeight: 600,
                            background: acc.connected ? '#dcfce7' : '#fef2f2',
                            color: acc.connected ? '#16a34a' : '#dc2626',
                          }}>
                            {acc.connected ? 'Active' : 'Disconnected'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right', padding: '14px 16px', color: '#777', fontSize: 11 }}>
                          {acc.lastSync
                            ? new Date(acc.lastSync).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                            : '--'}
                        </td>
                        <td style={{ textAlign: 'right', padding: '14px 16px' }}>
                          <div className="flex items-center justify-end gap-2">
                            {acc.connected ? (
                              <>
                                <button
                                  onClick={() => handleDisconnectAccount(acc.id)}
                                  style={{ padding: '5px 10px', fontSize: 10, fontWeight: 600, color: '#dc2626', border: '1px solid #fecaca', borderRadius: 6, background: '#fff', cursor: 'pointer' }}
                                  className="hover:bg-[#fef2f2] transition-colors"
                                >
                                  Disconnect
                                </button>
                                <button
                                  style={{ padding: '5px 10px', fontSize: 10, fontWeight: 600, color: '#777', border: '1px solid #ece8e0', borderRadius: 6, background: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                                  className="hover:border-[#ec4899] hover:text-[#ec4899] transition-colors"
                                >
                                  <RefreshCw size={10} /> Sync
                                </button>
                              </>
                            ) : (
                              <button
                                onClick={() => handleConnectAccount(acc.id)}
                                style={{ padding: '5px 12px', fontSize: 10, fontWeight: 600, color: '#fff', background: '#ec4899', borderRadius: 6, border: 'none', cursor: 'pointer' }}
                                className="hover:bg-[#db2777] transition-colors"
                              >
                                Connect
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Account Details Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
              {connectedAccounts.filter(a => a.connected).map(acc => {
                const plat = PLATFORMS.find(p => p.id === acc.platform);
                const Icon = plat?.icon || Globe;
                const platAnalytics = analytics.platformBreakdown.find(pb => pb.platform === acc.platform);
                return (
                  <div key={acc.id} className="empire-card" style={{ borderColor: plat?.color + '30' }}>
                    <div className="flex items-center gap-3 mb-3">
                      <div style={{
                        width: 40, height: 40, borderRadius: 10,
                        background: `linear-gradient(135deg, ${plat?.color}20, ${plat?.color}08)`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        <Icon size={20} style={{ color: plat?.color }} />
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>{plat?.label}</div>
                        <div style={{ fontSize: 12, color: '#ec4899', fontWeight: 600 }}>{acc.handle}</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div style={{ padding: '8px', borderRadius: 8, background: '#faf9f7', textAlign: 'center' }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{acc.followers.toLocaleString()}</div>
                        <div style={{ fontSize: 9, color: '#aaa' }}>Followers</div>
                      </div>
                      <div style={{ padding: '8px', borderRadius: 8, background: '#faf9f7', textAlign: 'center' }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{platAnalytics?.engagement || 0}%</div>
                        <div style={{ fontSize: 9, color: '#aaa' }}>Engagement</div>
                      </div>
                      <div style={{ padding: '8px', borderRadius: 8, background: '#faf9f7', textAlign: 'center' }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{platAnalytics?.posts || 0}</div>
                        <div style={{ fontSize: 9, color: '#aaa' }}>Posts</div>
                      </div>
                    </div>
                    {platAnalytics?.topTime && (
                      <div className="flex items-center gap-2 mt-3" style={{ fontSize: 11, color: '#777' }}>
                        <Clock size={11} />
                        <span>Best posting time: <strong style={{ color: '#1a1a1a' }}>{platAnalytics.topTime}</strong></span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {tab === 'payments' && (
          <PaymentModule product="social" />
        )}

        {tab === 'docs' && (
          <div style={{ padding: 24 }}><ProductDocs product="social" /></div>
        )}

      </div>
    </div>
  );
}

// ============ SUB-COMPONENTS ============

function DashKpi({ label, value, icon: Icon, change, positive, sublabel }: {
  label: string; value: string; icon: any; change?: string; positive?: boolean; sublabel?: string;
}) {
  return (
    <div className="empire-card">
      <div className="flex items-center justify-between mb-2">
        <div className="kpi-label">{label}</div>
        <Icon size={16} style={{ color: '#ec4899' }} />
      </div>
      <div className="kpi-value" style={{ fontSize: 22, color: '#1a1a1a' }}>{value}</div>
      {change && (
        <div className="flex items-center gap-1 mt-1">
          {positive ? <ArrowUpRight size={11} style={{ color: '#16a34a' }} /> : <ArrowDownRight size={11} style={{ color: '#dc2626' }} />}
          <span style={{ fontSize: 10, fontWeight: 600, color: positive ? '#16a34a' : '#dc2626' }}>{change}</span>
        </div>
      )}
      {sublabel && (
        <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>{sublabel}</div>
      )}
    </div>
  );
}

function SFStatusBadge({ status }: { status: string }) {
  const s = STATUS_COLORS[status] || STATUS_COLORS.draft;
  const Icon = status === 'posted' ? CheckCircle : status === 'scheduled' ? Clock : FileText;
  return (
    <span className="status-pill" style={{ background: s.bg, color: s.text, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
      <Icon size={10} /> {status}
    </span>
  );
}

function PostRow({ post, onDelete, onStatusChange }: {
  post: any; onDelete: (id: string) => void; onStatusChange: (id: string, status: string) => void;
}) {
  const plat = PLATFORMS.find(p => p.id === post.platform);
  const Icon = plat?.icon || Globe;
  const date = post.scheduledFor || post.postedAt;
  return (
    <div className="flex items-start gap-3" style={{
      padding: '12px',
      borderRadius: 10,
      background: '#faf9f7',
      border: '1px solid #ece8e0',
      transition: 'border-color 0.15s',
    }}>
      {date && (
        <div className="text-center shrink-0" style={{ minWidth: 44 }}>
          <div style={{ fontSize: 10, color: '#aaa' }}>
            {new Date(date).toLocaleDateString('en-US', { month: 'short' })}
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>
            {new Date(date).getDate()}
          </div>
          <div style={{ fontSize: 9, color: '#aaa' }}>
            {new Date(date).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Icon size={13} style={{ color: plat?.color }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }} className="capitalize">{post.platform}</span>
          <SFStatusBadge status={post.status} />
          {post.mediaType && post.mediaType !== 'text' && (
            <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, background: '#f0ece5', color: '#777' }}>
              {post.mediaType === 'video' ? 'VIDEO' : 'IMAGE'}
            </span>
          )}
        </div>
        <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5 }} className="line-clamp-2">{post.content?.slice(0, 160)}</p>
      </div>
      <div className="flex items-center gap-1 shrink-0 ml-2">
        {post.status === 'draft' && (
          <button
            onClick={() => onStatusChange(post.id, 'scheduled')}
            style={{ fontSize: 10, fontWeight: 600, color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px' }}
            className="hover:underline"
          >
            Schedule
          </button>
        )}
        {post.status === 'scheduled' && (
          <button
            onClick={() => onStatusChange(post.id, 'posted')}
            style={{ fontSize: 10, fontWeight: 600, color: '#16a34a', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px' }}
            className="hover:underline"
          >
            Mark Posted
          </button>
        )}
        <button onClick={() => onDelete(post.id)} style={{ color: '#ccc', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }} className="hover:text-[#dc2626] transition-colors">
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}
