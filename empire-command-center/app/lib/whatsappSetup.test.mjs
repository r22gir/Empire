import assert from 'node:assert/strict';
import test from 'node:test';
import { AYUDA_OPENER, renderWhatsAppSetupPage, setupConfig } from './whatsappSetup.mjs';

const BANNED_SENDS = [
  'graph.facebook.com',
  'fetch(',
  'XMLHttpRequest',
  'navigator.sendBeacon',
];

function render(edition) {
  return renderWhatsAppSetupPage(edition);
}

test('amp WhatsApp guide opens with manito, no first name, own webhook', () => {
  const html = render('amp');
  assert.equal(html.includes(AYUDA_OPENER), true);
  assert.equal(/¡Quiubo manito![\s\S]{0,120}(Juan|Camilo)/.test(html), false);
  assert.equal(html.includes('Hola Juan'), false);
  assert.equal(html.includes('Juan Diego'), false);
  assert.equal(html.includes('https://amp.empirebox.store/api/v1/whatsapp/webhook'), true);
  assert.equal(html.includes('maxine.empirebox.store'), false);
  assert.equal(html.includes('Maxine'), false);
  assert.match(html, /[Nn]unca escribe a clientes/);
  assert.match(html, /id="wa-0"/);
  assert.match(html, /id="wa-9"/);
  assert.match(html, /formulario seguro/);
  assert.match(html, /solicitud segura/);
  assert.match(html, /token permanente/);
  assert.match(html, /ventana/i);
  assert.match(html, /plantillas/i);
  assert.match(html, /número real/i);
  assert.match(html, /<figcaption>/);
  assert.match(html, /Ilustración/);
  for (const banned of BANNED_SENDS) {
    assert.equal(html.includes(banned), false, banned);
  }
});

test('maxine WhatsApp guide is construction and warns about Juan and Rafael keys', () => {
  const html = render('maxine');
  assert.equal(html.includes(AYUDA_OPENER), true);
  assert.equal(html.includes('Camilo'), false);
  assert.equal(html.includes('construcción'), true);
  assert.equal(html.includes('inmuebles'), true);
  assert.equal(html.includes('lote 12'), true);
  assert.match(html, /Juan ni de Rafael/);
  assert.equal(html.includes('https://maxine.empirebox.store/api/v1/whatsapp/webhook'), true);
  assert.equal(html.includes('amp.empirebox.store'), false);
  assert.equal(html.includes('Max-e'), false);
  assert.equal(html.includes('Juan Diego'), false);
  assert.match(html, /<figcaption>/);
  for (const banned of BANNED_SENDS) {
    assert.equal(html.includes(banned), false, banned);
  }
});

test('setup config stays isolated and tests never send', () => {
  assert.equal(setupConfig('amp').webhookUrl.includes('amp.empirebox.store'), true);
  assert.equal(setupConfig('maxine').webhookUrl.includes('maxine.empirebox.store'), true);
  assert.equal(setupConfig('workroom'), null);
  assert.equal(renderWhatsAppSetupPage.toString().includes('graph.facebook.com'), false);
});
