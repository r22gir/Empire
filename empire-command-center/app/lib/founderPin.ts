/** Chat PIN card helpers. The PIN value never belongs in history or logs. */

export function redactSecret(text: string, secret: string): string {
  if (!secret) return text;
  return text.split(secret).join('••••');
}

export function toolResultPreview(
  data: { success?: boolean; result?: unknown; error?: string },
  secret: string,
): string {
  const raw = data.success
    ? (typeof data.result === 'string' ? data.result : JSON.stringify(data.result ?? ''))
    : (data.error || 'The tool did not finish.');
  const clipped = raw.length > 1200 ? raw.slice(0, 1200) + '…' : raw;
  return redactSecret(clipped, secret);
}

/** Fields persisted to chat history. PIN prompts and the PIN itself stay out. */
export function historyMessage(message: {
  role: string;
  content: string;
  timestamp: string;
  pinPrompts?: unknown;
}): { role: string; content: string; timestamp: string } {
  return {
    role: message.role,
    content: message.content,
    timestamp: message.timestamp,
  };
}
