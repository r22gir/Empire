import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('family editions skip system/health and OpenClaw status polls', () => {
  const hook = readFileSync(new URL('../hooks/useSystemData.ts', import.meta.url), 'utf8');
  assert.match(hook, /isFamilyEdition/);
  assert.match(hook, /if \(isFamilyEdition\(\)\) return/);

  const chat = readFileSync(new URL('../components/screens/ChatScreen.tsx', import.meta.url), 'utf8');
  assert.match(chat, /if \(family\) return/);
  assert.match(chat, /fileViewUrl/);
  assert.equal(chat.includes('`${API}/files/view/images/${encodeURIComponent(msg.image)}`'), false);
});
