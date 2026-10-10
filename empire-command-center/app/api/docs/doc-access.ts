/**
 * Shared access check for /api/docs/read and /api/docs/serve.
 *
 * SECURITY (2026-10-03): these routes used to accept any absolute or
 * relative path with a plain `startsWith` check, so `..` segments, absolute
 * paths and repo files such as backend/.env could be read. Now:
 *   - only paths listed in the Docs registry (app/lib/docs-registry.ts) are
 *     served, plus the derived relist PDF pattern ProductDocs links to;
 *   - `..`, backslashes, NUL bytes are rejected outright;
 *   - the real (symlink-resolved) file must sit inside an allowed root,
 *     checked with a path separator, and must not be a secrets-looking file.
 * Anything else gets the same answer as a missing file (404).
 */
import { existsSync, realpathSync, statSync } from 'fs';
import path from 'path';
import { DOCS_REGISTRY } from '../../lib/docs-registry';

const REPO_ROOT = path.resolve(process.cwd(), '..');
const HOME = process.env.HOME || '/home/rg';

const REGISTRY_PATHS: Set<string> = new Set(
  Object.values(DOCS_REGISTRY).flat().map((d) => d.path),
);

const RELIST_PDF = /^docs\/relist\/pdf\/[A-Za-z0-9_.-]+\.pdf$/;

function safeReal(p: string): string | null {
  try {
    return realpathSync(p);
  } catch {
    return null;
  }
}

const ALLOWED_ROOTS: string[] = [
  REPO_ROOT,
  path.join(HOME, 'Empire'),
  path.join(HOME, 'Downloads'),
  path.join(HOME, 'Documents'),
]
  .flatMap((r) => [path.resolve(r), safeReal(r)])
  .filter((r): r is string => !!r);

const SECRET_NAME = /(^\.env)|(\.(pem|key|p12|pfx|kdbx)$)|(^\.?credentials)|(^id_(rsa|ed25519|ecdsa|dsa))/i;

function isUnder(p: string, root: string): boolean {
  return p === root || p.startsWith(root.endsWith(path.sep) ? root : root + path.sep);
}

function isRequestShapeOk(docPath: string): boolean {
  if (!docPath || docPath.length > 512) return false;
  if (docPath.includes('\0') || docPath.includes('\\')) return false;
  if (docPath.startsWith('/')) return false;
  const segs = docPath.replace(/^~\//, '').split('/');
  if (segs.some((s) => s === '..' || s === '.')) return false;
  return REGISTRY_PATHS.has(docPath) || RELIST_PDF.test(docPath);
}

function resolveDocPath(docPath: string): string {
  if (docPath.startsWith('~/')) return path.resolve(HOME, docPath.slice(2));
  return path.resolve(REPO_ROOT, docPath);
}

/** Registry paths say `data/...`; canonical files live in `backend/data/...`. */
function candidatePaths(docPath: string): string[] {
  const primary = resolveDocPath(docPath);
  const extra: string[] = [];
  if (!docPath.startsWith('~/')) {
    if (docPath.startsWith('data/')) {
      extra.push(path.resolve(REPO_ROOT, 'backend', docPath));
    } else if (docPath.startsWith('backend/data/')) {
      extra.push(path.resolve(REPO_ROOT, docPath.slice('backend/'.length)));
    }
  }
  return [primary, ...extra];
}

/** Returns the real file path to read, or null (treat as not found). */
export function resolveAllowedDoc(docPath: string | null): string | null {
  if (!docPath || !isRequestShapeOk(docPath)) return null;
  for (const candidate of candidatePaths(docPath)) {
    if (!ALLOWED_ROOTS.some((r) => isUnder(candidate, r))) continue;
    if (!existsSync(candidate)) continue;
    const real = safeReal(candidate);
    if (!real) continue;
    if (!ALLOWED_ROOTS.some((r) => isUnder(real, r))) continue;
    if (SECRET_NAME.test(path.basename(real))) continue;
    if (real.split(path.sep).some((s) => s === '.ssh' || s === '.claude' || s === '.config' || s === '.git')) continue;
    try {
      if (!statSync(real).isFile()) continue;
    } catch {
      continue;
    }
    return real;
  }
  return null;
}
