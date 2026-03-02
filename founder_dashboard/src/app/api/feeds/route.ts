import { NextResponse } from 'next/server';

// Cache results for 60 seconds
let cache: { data: any; expires: number } = { data: null, expires: 0 };
const CACHE_TTL = 60_000;

interface WeatherCity {
  name: string;
  lat: number;
  lon: number;
}

const WEATHER_CITIES: WeatherCity[] = [
  { name: 'Washington DC', lat: 38.9072, lon: -77.0369 },
  { name: 'Ibague, CO', lat: 4.4389, lon: -75.2322 },
];

const WMO_ICONS: Record<number, string> = {
  0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
  45: '🌫️', 48: '🌫️',
  51: '🌦️', 53: '🌦️', 55: '🌧️',
  61: '🌧️', 63: '🌧️', 65: '🌧️',
  71: '🌨️', 73: '🌨️', 75: '🌨️',
  80: '🌧️', 81: '🌧️', 82: '🌧️',
  95: '⛈️', 96: '⛈️', 99: '⛈️',
};

export async function GET() {
  const now = Date.now();
  if (cache.data && now < cache.expires) {
    return NextResponse.json(cache.data);
  }

  const result: Record<string, any> = { crypto: [], news: [], sports: null, weather: [] };

  // 1. Crypto prices (CoinGecko free API)
  try {
    const res = await fetch(
      'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true',
      { next: { revalidate: 60 } },
    );
    if (res.ok) {
      const data = await res.json();
      const coins = [
        { id: 'bitcoin', symbol: 'BTC', icon: '₿' },
        { id: 'ethereum', symbol: 'ETH', icon: 'Ξ' },
        { id: 'solana', symbol: 'SOL', icon: '◎' },
      ];
      result.crypto = coins.map((c) => ({
        symbol: c.symbol,
        icon: c.icon,
        price: data[c.id]?.usd ?? 0,
        change24h: data[c.id]?.usd_24h_change ?? 0,
        url: `https://www.coingecko.com/en/coins/${c.id}`,
      }));
    }
  } catch { /* crypto fetch failed */ }

  // 2. Weather (Open-Meteo — free, no API key)
  try {
    const weatherResults = await Promise.all(
      WEATHER_CITIES.map(async (city) => {
        const res = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${city.lat}&longitude=${city.lon}&current=temperature_2m,relative_humidity_2m,weather_code&temperature_unit=fahrenheit`,
          { next: { revalidate: 300 } },
        );
        if (!res.ok) return null;
        const data = await res.json();
        const cur = data.current;
        return {
          city: city.name,
          tempF: Math.round(cur.temperature_2m),
          humidity: cur.relative_humidity_2m,
          icon: WMO_ICONS[cur.weather_code] || '🌡️',
          code: cur.weather_code,
        };
      }),
    );
    result.weather = weatherResults.filter(Boolean);
  } catch { /* weather fetch failed */ }

  // 3. News headlines (HackerNews top stories)
  try {
    const idsRes = await fetch(
      'https://hacker-news.firebaseio.com/v0/topstories.json?limitToFirst=8&orderBy="$key"',
      { next: { revalidate: 300 } },
    );
    if (idsRes.ok) {
      const ids: number[] = await idsRes.json();
      const stories = await Promise.all(
        ids.slice(0, 6).map(async (id) => {
          const r = await fetch(`https://hacker-news.firebaseio.com/v0/item/${id}.json`);
          return r.ok ? r.json() : null;
        }),
      );
      result.news = stories
        .filter(Boolean)
        .map((s: any) => ({
          title: s.title,
          url: s.url || `https://news.ycombinator.com/item?id=${s.id}`,
          source: 'HN',
        }));
    }
  } catch { /* news fetch failed */ }

  // 4. Sports — ESPN scoreboard (free, no key)
  try {
    const sportsRes = await fetch(
      'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
      { next: { revalidate: 300 } },
    );
    if (sportsRes.ok) {
      const sportsData = await sportsRes.json();
      const events = sportsData.events || [];
      result.sports = events.slice(0, 3).map((e: any) => {
        const comp = e.competitions?.[0];
        const teams = comp?.competitors || [];
        return {
          name: e.shortName || e.name,
          status: comp?.status?.type?.shortDetail || '',
          home: teams.find((t: any) => t.homeAway === 'home')?.team?.abbreviation || '',
          homeScore: teams.find((t: any) => t.homeAway === 'home')?.score || '0',
          away: teams.find((t: any) => t.homeAway === 'away')?.team?.abbreviation || '',
          awayScore: teams.find((t: any) => t.homeAway === 'away')?.score || '0',
          url: e.links?.[0]?.href || 'https://www.espn.com/nba/scoreboard',
        };
      });
    }
  } catch { /* sports fetch failed */ }

  cache = { data: result, expires: now + CACHE_TTL };
  return NextResponse.json(result);
}
