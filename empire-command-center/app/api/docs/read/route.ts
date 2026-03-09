import { NextRequest, NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

const REPO_ROOT = path.resolve(process.cwd(), '..');
const HOME = process.env.HOME || '/home/rg';

function resolveDocPath(docPath: string): string {
  // Handle ~ paths
  if (docPath.startsWith('~/')) {
    return path.join(HOME, docPath.slice(2));
  }
  // Handle absolute paths
  if (docPath.startsWith('/')) {
    return docPath;
  }
  // Relative to repo root
  return path.join(REPO_ROOT, docPath);
}

export async function GET(req: NextRequest) {
  const docPath = req.nextUrl.searchParams.get('path');
  if (!docPath) {
    return NextResponse.json({ error: 'Missing path parameter' }, { status: 400 });
  }

  const resolved = resolveDocPath(docPath);

  // Security: only allow reading from empire-repo, Empire data, Downloads, Documents, .claude
  const allowed = [
    REPO_ROOT,
    path.join(HOME, 'Empire'),
    path.join(HOME, 'Downloads'),
    path.join(HOME, 'Documents'),
    path.join(HOME, '.claude'),
  ];

  const isAllowed = allowed.some(dir => resolved.startsWith(dir));
  if (!isAllowed) {
    return NextResponse.json({ error: 'Access denied' }, { status: 403 });
  }

  if (!existsSync(resolved)) {
    return NextResponse.json({ error: 'File not found', path: resolved }, { status: 404 });
  }

  try {
    const content = await readFile(resolved, 'utf-8');
    // Limit to 500KB to prevent huge file loads
    const truncated = content.length > 500000 ? content.slice(0, 500000) + '\n\n... (truncated at 500KB)' : content;
    return NextResponse.json({ content: truncated, path: resolved });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
