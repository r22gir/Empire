import path from 'path';

/**
 * Parent of this Next app (the Empire repo).
 *
 * Do not write this as path.resolve(process.cwd(), '..'). Turbopack file
 * tracing treats that literal parent as a root and walks docs/, including
 * local virtualenvs. docs/reports/pdf_venv/bin/python is a symlink that
 * crashes `next build`. Optional EMPIRE_REPO_ROOT overrides the parent.
 */
export function empireRepoRoot(): string {
  const fromEnv = process.env.EMPIRE_REPO_ROOT?.trim();
  if (fromEnv) return path.resolve(fromEnv);
  const cwd = process.cwd();
  const splitAt = cwd.lastIndexOf(path.sep);
  if (splitAt <= 0) return cwd;
  return cwd.slice(0, splitAt);
}
