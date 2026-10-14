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
  assert.match(html, /<figcaption>/);
  assert.equal(html.includes('graph.facebook.com'), false);
});

test('maxine empresa guide uses construction screens and not Juan keys', () => {
  const html = renderEmpresaGuidePage('maxine');
  assert.equal(html.includes(AYUDA_OPENER), true);
  assert.match(html, /Portafolio/);
  assert.match(html, /Lotes/);
  assert.match(html, /construcción/i);
  assert.match(html, /Juan ni de Rafael/);
  assert.equal(html.includes('Max-e'), false);
  assert.equal(html.includes('Cibernettic'), false);
  assert.equal(html.includes('amp.empirebox.store'), false);
  assert.equal(html.includes('maxine.empirebox.store'), true);
});

test('device access also opens with manito and stays isolated', () => {
  const amp = renderDeviceAccessPage('amp');
  const maxine = renderDeviceAccessPage('maxine');
  assert.equal(amp.includes(AYUDA_OPENER), true);
  assert.equal(maxine.includes(AYUDA_OPENER), true);
  assert.equal(amp.includes('maxine.empirebox.store'), false);
  assert.equal(maxine.includes('amp.empirebox.store'), false);
});
