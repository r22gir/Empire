'use client';
import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Cloud, Newspaper, Trophy, TrendingUp } from 'lucide-react';

interface CryptoItem { symbol: string; icon: string; price: number; change24h: number; url: string }
interface WeatherItem { city: string; tempF: number; humidity: number; icon: string }
interface NewsItem { title: string; url: string; source: string }
interface SportGame { name: string; status: string; home: string; homeScore: string; away: string; awayScore: string; url: string }

interface FeedData {
  crypto: CryptoItem[];
  weather: WeatherItem[];
  news: NewsItem[];
  sports: SportGame[] | null;
}

const CARD = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '10px',
  padding: '10px 14px',
};

export default function LiveTicker() {
  const [data, setData] = useState<FeedData | null>(null);
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window !== 'undefined') return localStorage.getItem('ticker-collapsed') === '1';
    return false;
  });

  useEffect(() => {
    const fetchFeeds = async () => {
      try {
        const res = await fetch('/api/feeds');
        if (res.ok) setData(await res.json());
      } catch { /* silent */ }
    };
    fetchFeeds();
    const interval = setInterval(fetchFeeds, 60_000);
    return () => clearInterval(interval);
  }, []);

  const toggleCollapse = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem('ticker-collapsed', next ? '1' : '0');
  };

  if (!data) return null;

  const formatPrice = (p: number) =>
    p >= 1000 ? `$${(p / 1000).toFixed(1)}K` : `$${p.toFixed(2)}`;

  // Collapsed: thin bar
  if (collapsed) {
    return (
      <div
        className="flex items-center justify-center gap-2 px-4 cursor-pointer select-none"
        style={{
          background: 'rgba(255,255,255,0.02)',
          borderTop: '1px solid rgba(255,255,255,0.04)',
          height: '28px',
          fontSize: '10px',
          color: 'var(--text-muted)',
        }}
        onClick={toggleCollapse}
      >
        <span>Live Data</span>
        <ChevronUp className="w-3 h-3" />
        {/* Show mini crypto inline when collapsed */}
        {data.crypto.map((c) => (
          <span key={c.symbol} className="flex items-center gap-0.5 ml-2">
            <span style={{ opacity: 0.5 }}>{c.icon}</span>
            <span>{formatPrice(c.price)}</span>
            <span style={{ color: c.change24h >= 0 ? '#22c55e' : '#ef4444', fontSize: '9px' }}>
              {c.change24h >= 0 ? '▲' : '▼'}{Math.abs(c.change24h).toFixed(1)}%
            </span>
          </span>
        ))}
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.015)',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        padding: '8px 12px',
      }}
    >
      {/* Collapse toggle */}
      <div className="flex items-center justify-between mb-2">
        <span style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Live Data
        </span>
        <button onClick={toggleCollapse} className="flex items-center gap-1" style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
          <ChevronDown className="w-3 h-3" />
        </button>
      </div>

      {/* Grid: 4 sections */}
      <div className="grid grid-cols-4 gap-2" style={{ fontSize: '11px' }}>

        {/* CRYPTO */}
        <div style={CARD}>
          <div className="flex items-center gap-1 mb-2">
            <TrendingUp className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span style={{ color: 'var(--gold)', fontSize: '9px', fontWeight: 600, textTransform: 'uppercase' }}>Crypto</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {data.crypto.map((c) => (
              <a
                key={c.symbol}
                href={c.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between hover:opacity-80 transition-opacity"
              >
                <span className="flex items-center gap-1">
                  <span style={{ opacity: 0.6 }}>{c.icon}</span>
                  <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{c.symbol}</span>
                </span>
                <span className="flex items-center gap-1.5">
                  <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{formatPrice(c.price)}</span>
                  <span style={{ color: c.change24h >= 0 ? '#22c55e' : '#ef4444', fontSize: '10px' }}>
                    {c.change24h >= 0 ? '▲' : '▼'}{Math.abs(c.change24h).toFixed(1)}%
                  </span>
                </span>
              </a>
            ))}
          </div>
        </div>

        {/* WEATHER */}
        <div style={CARD}>
          <div className="flex items-center gap-1 mb-2">
            <Cloud className="w-3 h-3" style={{ color: 'var(--cyan)' }} />
            <span style={{ color: 'var(--cyan)', fontSize: '9px', fontWeight: 600, textTransform: 'uppercase' }}>Weather</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {data.weather?.map((w) => (
              <div key={w.city} className="flex items-center justify-between">
                <span style={{ color: 'var(--text-secondary)' }}>{w.city}</span>
                <span className="flex items-center gap-1">
                  <span>{w.icon}</span>
                  <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{w.tempF}°F</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '9px' }}>{w.humidity}%</span>
                </span>
              </div>
            ))}
            {(!data.weather || data.weather.length === 0) && (
              <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>Loading...</span>
            )}
          </div>
        </div>

        {/* NEWS */}
        <div style={CARD}>
          <div className="flex items-center gap-1 mb-2">
            <Newspaper className="w-3 h-3" style={{ color: 'var(--purple)' }} />
            <span style={{ color: 'var(--purple)', fontSize: '9px', fontWeight: 600, textTransform: 'uppercase' }}>Headlines</span>
          </div>
          <div className="flex flex-col gap-1">
            {data.news.slice(0, 3).map((n, i) => (
              <a
                key={i}
                href={n.url}
                target="_blank"
                rel="noreferrer"
                className="block truncate hover:opacity-80 transition-opacity"
                style={{ color: 'var(--text-muted)', lineHeight: '1.3' }}
                title={n.title}
              >
                <span style={{ color: 'var(--cyan)', opacity: 0.5, fontSize: '8px', marginRight: '4px' }}>{n.source}</span>
                {n.title}
              </a>
            ))}
          </div>
        </div>

        {/* SPORTS */}
        <div style={CARD}>
          <div className="flex items-center gap-1 mb-2">
            <Trophy className="w-3 h-3" style={{ color: '#f59e0b' }} />
            <span style={{ color: '#f59e0b', fontSize: '9px', fontWeight: 600, textTransform: 'uppercase' }}>Sports</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {data.sports && data.sports.length > 0 ? (
              data.sports.slice(0, 3).map((g, i) => (
                <a
                  key={i}
                  href={g.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between hover:opacity-80 transition-opacity"
                >
                  <span style={{ color: 'var(--text-secondary)' }}>{g.away} <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{g.awayScore}</span></span>
                  <span style={{ opacity: 0.3 }}>-</span>
                  <span style={{ color: 'var(--text-secondary)' }}><span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{g.homeScore}</span> {g.home}</span>
                  <span style={{ fontSize: '8px', color: 'var(--text-muted)' }}>{g.status}</span>
                </a>
              ))
            ) : (
              <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>No live games</span>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
