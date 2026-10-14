import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { AYUDA_OPENER, renderEmpresaGuidePage } from './empresaGuide.mjs';
import { renderDeviceAccessPage } from './deviceAccess.mjs';

const CONSTRUCTION = [
  '/?product=construction',
  '/?product=construction&amp;section=lotmap',
  '/?product=construction&amp;section=construction',
  '/?product=construction&amp;section=buyers',
  '/?product=construction&amp;section=payments',
];

test('maxine empresa guide links to construction screens, not /amp/', () => {
  const html = renderEmpresaGuidePage('maxine');
  assert.equal(html.includes(AYUDA_OPENER), true);
  for (const href of CONSTRUCTION) {
    assert.equal(html.includes(href), true, href);
  }
  assert.equal(html.includes('/whatsapp/chats'), true);
  assert.equal(html.includes('/amp/'), false);
  assert.equal(html.includes('Max-e'), false);
  assert.equal(html.includes('Cibernettic'), false);
  assert.equal(html.includes('amp.empirebox.store'), false);
  assert.equal(html.includes('Juan'), false);

  const forge = readFileSync(new URL('../components/screens/ConstructionForgePage.tsx', import.meta.url), 'utf8');
  assert.match(forge, /id: 'lotmap'/);
  assert.match(forge, /case 'lotmap'/);
  assert.match(forge, /case 'buyers'/);
  assert.match(forge, /case 'payments'/);
  assert.match(forge, /case 'construction'/);
});

test('device access opens with manito and one WhatsApp link', () => {
  const maxine = renderDeviceAccessPage('maxine');
  assert.equal(maxine.includes(AYUDA_OPENER), true);
  assert.equal(maxine.includes('/ayuda/whatsapp'), true);
  assert.equal(maxine.includes('/amp/'), false);
  assert.equal(maxine.includes('amp.empirebox.store'), false);
  const other = renderDeviceAccessPage('amp');
  assert.equal(other.includes('maxine.empirebox.store'), false);
  assert.equal(other.includes('amp.empirebox.store'), false);
});
