import { NextRequest, NextResponse } from 'next/server';

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function jsonResponse(data: any, status = 200) {
  return NextResponse.json(data, { status, headers: CORS_HEADERS });
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS_HEADERS });
}

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q');
  if (!q) {
    return jsonResponse({ images: [] });
  }

  const accessKey = process.env.UNSPLASH_ACCESS_KEY;
  if (!accessKey) {
    // No API key configured — presets still work without it
    return jsonResponse({ images: [] });
  }

  try {
    const url = new URL('https://api.unsplash.com/search/photos');
    url.searchParams.set('query', `${q} window treatment interior design`);
    url.searchParams.set('per_page', '12');
    url.searchParams.set('orientation', 'landscape');

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Client-ID ${accessKey}` },
    });

    if (!res.ok) {
      console.error('Unsplash API error:', res.status, await res.text());
      return jsonResponse({ images: [] });
    }

    const data = await res.json();
    const images = (data.results || []).map((photo: any) => ({
      id: photo.id,
      url: photo.urls?.regular || photo.urls?.small,
      thumb: photo.urls?.thumb || photo.urls?.small,
      description: photo.alt_description || photo.description || '',
    }));

    return jsonResponse({ images });
  } catch (err) {
    console.error('Inspiration search failed:', err);
    return jsonResponse({ images: [] });
  }
}
