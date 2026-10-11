'use client';
/** Tiny event bus so any screen can open the shared viewer without prop drilling. */
import { viewerHref } from '../../lib/docs-hub/types';

export interface DocRef { id?: string; src?: string; title: string; filename?: string; kind?: 'pdf' | 'image'; v?: string | null }
export const OPEN_DOC_EVENT = 'empire:open-doc';

export function openDocViewer(doc: DocRef) {
  if (typeof window === 'undefined') return;
  if ((window as any).__empireDocHost) window.dispatchEvent(new CustomEvent(OPEN_DOC_EVENT, { detail: doc }));
  else window.location.href = viewerHref({ id: doc.id, src: doc.id ? undefined : doc.src, title: doc.title });
}
