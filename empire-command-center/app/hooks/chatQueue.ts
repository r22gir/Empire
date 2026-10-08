/**
 * Message queueing for Max chat (Rafael 2026-10-08): the composer never locks.
 * A message sent while Max is still answering is shown at once, marked queued,
 * and runs in order after the current turn. Pure helpers so the ordering rules
 * are testable without React.
 */
import type { Message } from '../lib/types';

export interface QueuedTurn {
  msg: Message;
  imageFilename?: string | null;
  desk?: string;
  channel?: string;
}

/** Insert `item` right after the message with id `afterId` (end of list when missing). */
export function insertAfter(list: Message[], afterId: string, item: Message): Message[] {
  const i = list.findIndex(m => m.id === afterId);
  if (i < 0) return [...list, item];
  // keep any assistant/system rows already attached to that turn ahead of the new one,
  // but never jump past a later user message (queued or not)
  let j = i + 1;
  while (j < list.length && list[j].role !== 'user') j++;
  return [...list.slice(0, j), item, ...list.slice(j)];
}

/** Conversation the model sees for this turn: everything up to and including `turnId`, no queued rows. */
export function historyFor(list: Message[], turnId: string): Message[] {
  const i = list.findIndex(m => m.id === turnId);
  const upTo = i < 0 ? list : list.slice(0, i + 1);
  return upTo.filter(m => !m.queued || m.id === turnId);
}

/** Mark a queued message as active (it is the turn being answered now). */
export function markActive(list: Message[], id: string): Message[] {
  return list.map(m => (m.id === id ? { ...m, queued: false } : m));
}

/** Drop a queued message the founder cancelled (only while still queued). */
export function dropQueued(list: Message[], id: string): Message[] {
  return list.filter(m => !(m.id === id && m.queued));
}

/** Rows for the chat view: answered/active turns first, queued ones after the live reply. */
export function splitForView(list: Message[]): { settled: Message[]; queued: Message[] } {
  return { settled: list.filter(m => !m.queued), queued: list.filter(m => !!m.queued) };
}

let _seq = 0;
/** Unique, increasing ids (Date.now() alone collides when messages are sent back to back). */
export function nextId(): string {
  _seq = (_seq + 1) % 1000;
  return `${Date.now()}${String(_seq).padStart(3, '0')}`;
}
