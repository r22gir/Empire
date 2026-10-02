import assert from 'node:assert/strict';
import test from 'node:test';
import { historyMessage, redactSecret, toolResultPreview } from './founderPin.ts';

test('PIN digits are stripped from tool output and chat history', () => {
  const pin = '918273';
  const preview = toolResultPreview(
    { success: true, result: { stdout: `token ${pin}\n` } },
    pin,
  );
  assert.equal(preview.includes(pin), false);
  assert.equal(preview.includes('••••'), true);

  const saved = historyMessage({
    role: 'assistant',
    content: `Approved.\n${preview}`,
    timestamp: '1:00',
    pinPrompts: [{ resumeId: 'abc', tool: 'shell_execute', status: 'done' }],
  });
  assert.equal('pinPrompts' in saved, false);
  assert.equal(JSON.stringify(saved).includes(pin), false);
  assert.equal(redactSecret(`pin ${pin}`, pin), 'pin ••••');
});
