import assert from 'node:assert/strict';
import test from 'node:test';
import {
  FABRICS_STORE_INDEX,
  fabricsHostDecision,
  isFabricsHost,
} from './fabricsHost.ts';

const HOST = 'fabrics.empirebox.store';

test('fabrics host root rewrites to the store', () => {
  assert.deepEqual(fabricsHostDecision(HOST, 'GET', '/'), {
    action: 'rewrite',
    pathname: FABRICS_STORE_INDEX,
  });
  assert.equal(FABRICS_STORE_INDEX, '/fine-fabrics');
});

test('host match ignores port and case', () => {
  assert.equal(isFabricsHost('Fabrics.EmpireBox.store:443'), true);
  assert.deepEqual(fabricsHostDecision('TEST-FABRICS.empirebox.store:3005', 'HEAD', '/').action, 'rewrite');
});

test('store pages, assets, and the fine-fabrics API pass through', () => {
  for (const path of [
    '/fine-fabrics',
    '/fine-fabrics/12',
    '/fine-fabrics/cart',
    '/fine-fabrics/checkout',
    '/fine-fabrics/samples',
    '/fine-fabrics/quote',
    '/fine-fabrics/sitemap.xml',
    '/fine-fabrics/merchant.xml',
    '/_next/static/chunks/main.js',
    '/favicon.ico',
    '/ff-placeholder-swatch.svg',
    '/api/v1/fine-fabrics/catalog',
    '/api/v1/fine-fabrics/checkout',
  ]) {
    assert.deepEqual(fabricsHostDecision(HOST, 'GET', path), { action: 'next' }, path);
  }
  assert.deepEqual(fabricsHostDecision(HOST, 'POST', '/api/v1/fine-fabrics/checkout'), { action: 'next' });
  assert.deepEqual(fabricsHostDecision(HOST, 'GET', '/sitemap.xml'), {
    action: 'rewrite',
    pathname: '/fine-fabrics/sitemap.xml',
  });
});

test('operator screens and other APIs are not reachable on the fabrics host', () => {
  for (const path of [
    '/workroom',
    '/landing',
    '/intake',
    '/max',
    '/platform',
    '/api/v1/quotes',
    '/api/v1/finance/invoices',
    '/api/v1/leadforge/intake',
    '/fine-fabrics/admin',
    '/fine-fabrics/admin/import',
    '/fine-fabrics/../api/v1/quotes',
  ]) {
    assert.deepEqual(fabricsHostDecision(HOST, 'GET', path), { action: 'not-found' }, path);
  }
});

test('apex, workroom, luxe, studio, and forge are untouched by the fabrics rule', () => {
  for (const host of [
    'empirebox.store',
    'workroom.empirebox.store',
    'luxe.empirebox.store',
    'studio.empirebox.store',
    'forge.empirebox.store',
    'localhost',
    '',
  ]) {
    assert.deepEqual(fabricsHostDecision(host, 'GET', '/'), { action: 'pass' }, host);
  }
});
