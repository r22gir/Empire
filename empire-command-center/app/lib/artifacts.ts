/**
 * MAX Artifact Utilities — frontend parser, sanitizer, and HTML builder.
 *
 * Provides:
 * - parseArtifactBlocks(text) → { visible, artifacts }
 * - validateArtifact(data) → MaxArtifact | null
 * - stripDangerousHtml(html) → { cleaned, hadDangerous }
 * - buildArtifactHtmlDoc(artifact) → full HTML document string
 */

import { MaxArtifact, ArtifactType } from './types';

const ARTIFACT_BLOCK_RE = /MAX_ARTIFACT_JSON\s*:\s*```json\s*([\s\S]*?)```/i;

/**
 * Parse MAX_ARTIFACT_JSON fence blocks from response text.
 * Extracts artifact JSON and returns cleaned visible text + artifacts array.
 */
export function parseArtifactBlocks(text: string): { visible: string; artifacts: MaxArtifact[] } {
  const artifacts: MaxArtifact[] = [];

  // Split on artifact block boundaries, process each
  const segments = text.split(/(?=MAX_ARTIFACT_JSON\s*:)/i);

  const visible = segments
    .map(segment => {
      const match = segment.match(ARTIFACT_BLOCK_RE);
      if (match) {
        try {
          const parsed = JSON.parse(match[1]) as MaxArtifact;
          const validated = validateArtifact(parsed);
          if (validated) {
            // Enforce safety defaults on frontend as defense-in-depth
            if (validated.artifact_type === 'html_artifact') {
              validated.safety = {
                scripts_allowed: false,
                external_network_allowed: false,
                sandboxed: true,
                sanitized: true,
              };
              validated.requires_approval = true;
            }
            if (validated.artifact_type === 'react_component_proposal') {
              validated.requires_approval = true;
            }
            artifacts.push(validated);
          }
          // Remove the artifact block from visible text
          return segment.replace(ARTIFACT_BLOCK_RE, '').trim();
        } catch {
          return segment; // Fallback: show block as text if JSON invalid
        }
      }
      return segment;
    })
    .join('\n\n')
    .trim();

  return { visible, artifacts };
}

/**
 * Validate raw JSON object as a MaxArtifact.
 * Returns null if required fields are missing or type is invalid.
 */
export function validateArtifact(data: unknown): MaxArtifact | null {
  if (typeof data !== 'object' || data === null) return null;
  const a = data as Record<string, unknown>;

  const validTypes: ArtifactType[] = ['plain_text', 'markdown_report', 'html_artifact', 'react_component_proposal'];
  if (!validTypes.includes(a.artifact_type as ArtifactType)) return null;
  if (typeof a.id !== 'string' || !a.id) return null;
  if (typeof a.title !== 'string' || !a.title) return null;
  if (typeof a.content !== 'string') return null;

  return data as MaxArtifact;
}

/**
 * Strip dangerous HTML elements from content.
 * Returns both the cleaned HTML and whether dangerous content was found/removed.
 */
export function stripDangerousHtml(html: string): { cleaned: string; hadDangerous: boolean } {
  let hadDangerous = false;
  let cleaned = html;

  const before = cleaned;
  cleaned = cleaned.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
  if (cleaned !== before) hadDangerous = true;

  const before2 = cleaned;
  cleaned = cleaned.replace(/\bon\w+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]*)/gi, '');
  if (cleaned !== before2) hadDangerous = true;

  const before3 = cleaned;
  cleaned = cleaned.replace(/javascript\s*:/gi, '');
  if (cleaned !== before3) hadDangerous = true;

  const before4 = cleaned;
  cleaned = cleaned.replace(/\s(src|href)\s*=\s*["'](?:https?|ftp):\/\/[^"']+["']/gi, '');
  if (cleaned !== before4) hadDangerous = true;

  const before5 = cleaned;
  cleaned = cleaned.replace(/<(?:iframe|object|embed|form)\b[^>]*>[\s\S]*?<\/(?:iframe|object|embed|form)>/gi, '');
  cleaned = cleaned.replace(/<(?:iframe|object|embed|form)\b[^>]*\/?>/gi, '');
  if (cleaned !== before5) hadDangerous = true;

  return { cleaned, hadDangerous };
}

/**
 * Build a self-contained HTML document from an artifact for iframe srcDoc use.
 * Always strips dangerous HTML first.
 */
export function buildArtifactHtmlDoc(artifact: MaxArtifact): string {
  const { cleaned } = stripDangerousHtml(artifact.content);

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;padding:16px;min-height:100vh}
</style>
</head>
<body>${cleaned}</body>
</html>`;
}