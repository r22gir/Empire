import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { AYUDA_OPENER, KEYS_HANDOFF, renderWhatsAppSetupPage, setupConfig } from './whatsappSetup.mjs';

const BANNED_SENDS = [
  'graph.facebook.com',
  'fetch(',
  'XMLHttpRequest',
  'navigator.sendBeacon',
];

const HANDOFF = 'Las llaves no van en el chat ni en esta página. Cuando las tengas, avísale a Rafael y él te dice cómo entregárselas de forma segura.';

test('amp WhatsApp guide opens with manito and the Rafael handoff', () => {
  const html = renderWhatsAppSetupPage('amp');
  assert.equal(html.includes(AYUDA_OPENER), true);
  assert.equal(html.includes(KEYS_HANDOFF), true);
  assert.equal(html.includes(HANDOFF), true);
  assert.equal(html.includes('Entrega de las llaves'), true);
  assert.equal(html.includes('formulario seguro'), false);
  assert.equal(html.includes('solicitud segura'), false);
  assert.equal(html.includes('/home/rg/'), false);
  assert.equal(html.includes('8011'), false);
  assert.equal(html.includes('8012'), false);
  assert.equal(html.includes('Juan Diego'), false);
  assert.equal(html.includes('Maxine'), false);
  assert.equal(html.includes('https://amp.empirebox.store/api/v1/whatsapp/webhook'), true);
  assert.equal(html.includes('Conectar con clientes por WhatsApp'), true);
  assert.equal(html.includes('Business Settings → System users'), true);
  assert.equal(html.includes('whatsapp_business_messaging'), true);
  assert.equal(html.includes('whatsapp_business_management'), true);
  assert.equal(html.includes('App settings → Basic'), true);
  assert.equal(html.includes('/amp/whatsapp/chats'), true);
  assert.match(html, /[Nn]unca escribe a clientes/);
  assert.match(html, /id="wa-0"/);
  assert.match(html, /id="wa-9"/);
  assert.match(html, /<figcaption>/);
  for (const banned of BANNED_SENDS) {
    assert.equal(html.includes(banned), false, banned);
  }
});

test('this tree ships only the Max-e edition file', () => {
  const src = readFileSync(new URL('./familyEdition.mjs', import.meta.url), 'utf8');
  assert.match(src, /id: 'amp'/);
  assert.equal(src.includes('Juan Diego'), false);
  assert.equal(src.includes('empire-amp.env'), false);
  assert.equal(src.includes('8011'), false);
  assert.equal(src.includes('Maxine'), false);
  assert.equal(src.includes('Camilo'), false);
  assert.equal(setupConfig('amp').webhookUrl.includes('amp.empirebox.store'), true);
  assert.equal(setupConfig('maxine'), null);
  assert.equal(setupConfig('workroom'), null);
  const other = renderWhatsAppSetupPage('maxine');
  assert.match(other, /tu propio centro de mando/);
  assert.equal(other.includes('amp.empirebox.store'), false);
});
