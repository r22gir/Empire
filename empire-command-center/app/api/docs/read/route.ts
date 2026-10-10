import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { resolveAllowedDoc } from '../doc-access';

export async function GET(req: NextRequest) {
  const docPath = req.nextUrl.searchParams.get('path');
  if (!docPath) {
    return NextResponse.json({ error: 'Missing path parameter' }, { status: 400 });
  }

  // SECURITY: registry-only, traversal-safe (see ../doc-access.ts).
  const resolved = resolveAllowedDoc(docPath);
  if (!resolved) {
    return NextResponse.json({ error: 'File not found' }, { status: 404 });
  }

  try {
    const content = await readFile(resolved, 'utf-8');
    // Limit to 500KB to prevent huge file loads
    const truncated = content.length > 500000 ? content.slice(0, 500000) + '\n\n... (truncated at 500KB)' : content;
    return NextResponse.json({ content: truncated, path: docPath });
  } catch (err: any) {
    return NextResponse.json({ error: 'Could not read file' }, { status: 500 });
  }
}
