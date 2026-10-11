'use client';
/** Mount once (CommandCenterApp). Listens for openDocViewer() and shows the modal viewer. */
import { useEffect, useState } from 'react';
import DocViewer from './DocViewer';
import { OPEN_DOC_EVENT, type DocRef } from './viewerBus';

export default function DocViewerHost() {
  const [doc, setDoc] = useState<DocRef | null>(null);
  useEffect(() => {
    (window as any).__empireDocHost = true;
    const on = (e: Event) => setDoc((e as CustomEvent<DocRef>).detail);
    window.addEventListener(OPEN_DOC_EVENT, on);
    return () => { (window as any).__empireDocHost = false; window.removeEventListener(OPEN_DOC_EVENT, on); };
  }, []);
  useEffect(() => {
    if (!doc) return;
    const prev = document.body.style.overflow; document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [doc]);
  if (!doc) return null;
  return <DocViewer initial={doc} mode="modal" onClose={() => setDoc(null)} />;
}
