import assert from 'node:assert/strict';
import test from 'node:test';
import {
  WORKROOM_SHOWROOM_INDEX,
  isWorkroomHost,
  workroomHostDecision,
} from './workroomHost.ts';

const HOST = 'workroom.empirebox.store';

test('workroom host root rewrites to the Style B showroom page', () => {
  assert.deepEqual(workroomHostDecision(HOST, 'GET', '/'), {
    action: 'rewrite',
    pathname: WORKROOM_SHOWROOM_INDEX,
  });
  assert.equal(WORKROOM_SHOWROOM_INDEX, '/workroom-showroom/index.html');
});

test('host match ignores port and case', () => {
  assert.equal(isWorkroomHost('Workroom.EmpireBox.store:443'), true);
  assert.deepEqual(workroomHostDecision('WORKROOM.empirebox.store:3005', 'HEAD', '/').action, 'rewrite');
});

test('showroom photos and favicon pass through on the workroom host', () => {
  for (const path of [
    '/workroom-showroom/index.html',
    '/workroom-showroom/photos/bed-cognac-panel-headboard.jpg',
    '/workroom-showroom/og.jpg',
    '/favicon.ico',
  ]) {
    assert.deepEqual(workroomHostDecision(HOST, 'GET', path), { action: 'next' }, path);
  }
});

test('operator screens and the API are not reachable on the workroom host', () => {
  for (const path of [
    '/workroom',
    '/landing',
    '/intake',
    '/max',
    '/platform',
    '/api/v1/quotes',
    '/api/v1/leadforge/intake',
    '/_next/static/chunks/main.js',
    '/workroom-showroom',
    '/workroom-showroom/../api/v1/quotes',
    '/workroom-showroom//photos/x.jpg',
  ]) {
    assert.deepEqual(workroomHostDecision(HOST, 'GET', path), { action: 'not-found' }, path);
  }
});

test('workroom host is read-only', () => {
  for (const method of ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']) {
    assert.deepEqual(workroomHostDecision(HOST, method, '/'), { action: 'method-not-allowed' }, method);
  }
});

test('apex, www, luxe, studio, and forge are untouched by the workroom rule', () => {
  for (const host of [
    'empirebox.store',
    'www.empirebox.store',
    'luxe.empirebox.store',
    'test-luxe.empirebox.store',
    'studio.empirebox.store',
    'forge.empirebox.store',
    'localhost:3005',
    '',
  ]) {
    assert.deepEqual(workroomHostDecision(host, 'GET', '/'), { action: 'pass' }, host);
    assert.deepEqual(workroomHostDecision(host, 'POST', '/api/v1/intake/signup'), { action: 'pass' }, host);
  }
  assert.deepEqual(workroomHostDecision(null, 'GET', '/'), { action: 'pass' });
});
