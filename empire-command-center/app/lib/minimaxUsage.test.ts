import assert from 'node:assert/strict';
import test from 'node:test';
import { minimaxUsageLabels } from './minimaxUsageCopy.ts';

test('MiniMax usage view is bilingual and founder-only', () => {
  const es = minimaxUsageLabels('es');
  assert.equal(es.nav, 'Uso MiniMax');
  assert.match(es.intro, /20%/);
  assert.match(es.intro, /tope combinado/);
  assert.match(es.family, /20%/);
  assert.match(es.credits, /créditos de regalo/);
  assert.match(es.credits, /Auto credit usage/);
  assert.match(es.remainsDown, /bloque/i);
  assert.equal(es.denied, 'Solo el Max personal de Rafael ve este medidor.');
  const en = minimaxUsageLabels('en');
  assert.equal(en.nav, 'MiniMax usage');
  assert.match(en.intro, /20% each/);
  assert.match(en.intro, /No combined family cap/);
  assert.match(en.credits, /Gift credits/);
  assert.match(en.credits, /Auto credit usage/);
  assert.match(en.remainsDown, /Personal text continues/);
  assert.match(en.remainsDown, /blocked/);
  assert.match(en.aiLabel, /AI-generated/);
});
