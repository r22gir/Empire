import assert from 'node:assert/strict';
import test from 'node:test';
import { AYUDA_OPENER, renderEmpresaGuidePage } from './empresaGuide.mjs';
import { renderDeviceAccessPage } from './deviceAccess.mjs';

test('amp empresa guide links to Max-e screens only', () => {
  const html = renderEmpresaGuidePage('amp');
  assert.equal(html.includes(AYUDA_OPENER), true);
  assert.match(html, /\/amp\/dashboard/);
  assert.match(html, /\/amp\/empresas/);
  assert.match(html, /\/amp\/cursos/);
  assert.match(html, /\/ayuda\/whatsapp/);
  assert.equal(html.includes('Maxine'), false);
  assert.equal(html.includes('amp.empirebox.store'), true);
  assert.equal(html.includes('maxine.empirebox.store'), false);
  assert.equal(html.includes('/home/rg/'), false);
  assert.match(html, /<figcaption>/);
});

test('device access opens with manito and one WhatsApp link', () => {
  const amp = renderDeviceAccessPage('amp');
  assert.equal(amp.includes(AYUDA_OPENER), true);
  assert.equal(amp.includes('/ayuda/whatsapp'), true);
  assert.equal(amp.includes('/amp/whatsapp'), false);
  assert.equal(amp.includes('maxine.empirebox.store'), false);
  const other = renderDeviceAccessPage('maxine');
  assert.equal(other.includes('amp.empirebox.store'), false);
  assert.equal(other.includes('maxine.empirebox.store'), false);
});
