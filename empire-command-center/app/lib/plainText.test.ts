import assert from 'node:assert/strict';
import test from 'node:test';
import { stripTelegramHtml } from './plainText.ts';

test('strips Telegram <b> tags for the Studio inbox', () => {
  assert.equal(
    stripTelegramHtml('\n📥 <b>194 inbox items</b> piling up'),
    '📥 194 inbox items piling up',
  );
});

test('leaves plain text alone', () => {
  assert.equal(stripTelegramHtml('No overdue tasks'), 'No overdue tasks');
});
