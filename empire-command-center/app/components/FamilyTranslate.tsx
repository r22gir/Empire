'use client';

/**
 * Family editions only: swaps leftover English UI text in shared Empire
 * modules for Spanish. It only changes text node values and a few
 * attributes (placeholder, title, aria-label), never the DOM structure,
 * so React keeps owning every node. Workroom renders nothing here.
 */
import { useEffect } from 'react';
import { translateFamily } from '../lib/familyEs';

const EDITION = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || '').trim().toLowerCase();
const FAMILY = EDITION === 'amp' || EDITION === 'maxine';
const ATTRS = ['placeholder', 'title', 'aria-label'];
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE', 'PRE', 'NOSCRIPT']);

function skipped(el: Element | null): boolean {
  for (let cur = el; cur; cur = cur.parentElement) {
    if (SKIP_TAGS.has(cur.tagName)) return true;
    if (cur.hasAttribute('data-no-translate') || cur.hasAttribute('data-ventas-page')) return true;
    if ((cur as HTMLElement).isContentEditable) return true;
  }
  return false;
}

function fixText(node: Text) {
  const value = node.nodeValue;
  if (!value || value.length > 200 || !/[A-Za-z]/.test(value)) return;
  if (skipped(node.parentElement)) return;
  const next = translateFamily(value);
  if (next !== null && next !== value) node.nodeValue = next;
}

function fixAttrs(el: Element) {
  for (const name of ATTRS) {
    const value = el.getAttribute(name);
    if (!value || !/[A-Za-z]/.test(value)) continue;
    const next = translateFamily(value);
    if (next !== null && next !== value) el.setAttribute(name, next);
  }
}

function walk(root: Node) {
  if (root.nodeType === Node.TEXT_NODE) { fixText(root as Text); return; }
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  const el = root as Element;
  if (skipped(el)) return;
  fixAttrs(el);
  const walker = document.createTreeWalker(el, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  let cur: Node | null = walker.nextNode();
  while (cur) {
    if (cur.nodeType === Node.TEXT_NODE) fixText(cur as Text);
    else fixAttrs(cur as Element);
    cur = walker.nextNode();
  }
}

export default function FamilyTranslate() {
  useEffect(() => {
    if (!FAMILY || typeof MutationObserver === 'undefined') return;
    let pending: Set<Node> = new Set();
    let scheduled = false;
    const flush = () => {
      scheduled = false;
      const batch = pending;
      pending = new Set();
      batch.forEach((n) => { if (n.isConnected) walk(n); });
    };
    const queue = (n: Node) => {
      pending.add(n);
      if (!scheduled) { scheduled = true; requestAnimationFrame(flush); }
    };
    const observer = new MutationObserver((records) => {
      for (const r of records) {
        if (r.type === 'characterData') queue(r.target);
        else if (r.type === 'attributes') queue(r.target);
        else r.addedNodes.forEach(queue);
      }
    });
    walk(document.body);
    observer.observe(document.body, {
      subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS,
    });
    return () => observer.disconnect();
  }, []);
  return null;
}
