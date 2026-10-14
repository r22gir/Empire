import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { AYUDA_OPENER, KEYS_HANDOFF, renderWhatsAppSetupPage, setupConfig } from './whatsappSetup.mjs';

const HANDOFF = 'Las llaves no van en el chat ni en esta página. Cuando las tengas, avísale a Rafael y él te dice cómo entregárselas de forma segura.';

test('maxine WhatsApp guide is construction, handoff, and own chats path', () => {
  const html = renderWhatsAppSetupPage('maxine');
  assert.equal(html.includes(AYUDA_OPENER), true);
  assert.equal(html.includes(KEYS_HANDOFF), true);
  assert.equal(html.includes(HANDOFF), true);
  assert.equal(html.includes('Entrega de las llaves'), true);
  assert.equal(html.includes('No reutilices llaves ni números de otra instancia.'), true);
  assert.equal(html.includes('formulario seguro'), false);
  assert.equal(html.includes('solicitud segura'), false);
  assert.equal(html.includes('/home/rg/'), false);
  assert.equal(html.includes('8011'), false);
  assert.equal(html.includes('8012'), false);
  assert.equal(html.includes('Juan'), false);
  assert.equal(html.includes('Camilo'), false);
  assert.equal(html.includes('Max-e'), false);
  assert.equal(html.includes('/amp/'), false);
  assert.equal(html.includes('amp.empirebox.store'), false);
  assert.equal(html.includes('https://maxine.empirebox.store/api/v1/whatsapp/webhook'), true);
  assert.equal(html.includes('/whatsapp/chats'), true);
  assert.equal(html.includes('lote 12'), true);
  assert.equal(html.includes('construcción'), true);
  assert.equal(html.includes('Conectar con clientes por WhatsApp'), true);
  assert.equal(html.includes('Business Settings → System users'), true);
  assert.equal(html.includes('App settings → Basic'), true);
});

test('this tree ships only the Maxine edition file', () => {
  const src = readFileSync(new URL('./familyEdition.mjs', import.meta.url), 'utf8');
  assert.match(src, /id: 'maxine'/);
  assert.equal(src.includes('Juan'), false);
  assert.equal(src.includes('Juan Diego'), false);
  assert.equal(src.includes('empire-amp.env'), false);
  assert.equal(src.includes('8011'), false);
  assert.equal(src.includes('Max-e'), false);
  assert.equal(src.includes('/amp/'), false);
  assert.equal(setupConfig('maxine').webhookUrl.includes('maxine.empirebox.store'), true);
  assert.equal(setupConfig('amp'), null);
  const other = renderWhatsAppSetupPage('amp');
  assert.match(other, /tu propio centro de mando/);
  assert.equal(other.includes('maxine.empirebox.store'), false);
});
