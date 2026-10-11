import assert from 'node:assert/strict';
import test from 'node:test';
import {
  familyHomeRedirect,
  isFamilyHost,
  isFamilyPublicPath,
} from './familyChrome.mjs';
import {
  FAMILY_LOGIN_PATH,
  familyAuthFailedStatus,
  shouldGateFamilyShell,
} from './familyAuth.ts';

test('anonymous AMP root and dashboard redirect to /login', () => {
  assert.equal(familyHomeRedirect('amp', '/', false), '/login');
  assert.equal(familyHomeRedirect('amp', '/amp/dashboard', false), '/login');
  assert.equal(familyHomeRedirect('workroom', '/', false, 'amp.empirebox.store'), '/login');
  assert.equal(familyHomeRedirect('amp', '/login', false), null);
  assert.equal(familyHomeRedirect('amp', '/amp/login', false), null);
  assert.equal(familyHomeRedirect('amp', '/amp/signup', false), null);
  assert.equal(familyHomeRedirect('amp', '/', true), null);
  assert.equal(familyHomeRedirect('workroom', '/', false), null);
  assert.equal(isFamilyPublicPath('/login'), true);
  assert.equal(isFamilyPublicPath('/amp/login'), true);
  assert.equal(isFamilyPublicPath('/'), false);
});

test('family gate uses host when NEXT_PUBLIC_EMPIRE_EDITION was not baked', () => {
  assert.equal(isFamilyHost('amp.empirebox.store'), true);
  assert.equal(shouldGateFamilyShell('workroom', 'amp.empirebox.store'), true);
  assert.equal(shouldGateFamilyShell('workroom', 'studio.empirebox.store'), false);
  assert.equal(isFamilyPublicPath('/_next/static/chunk.js'), true);
  assert.equal(isFamilyPublicPath('/api/v1/edition'), true);
  assert.equal(FAMILY_LOGIN_PATH, '/login');
  assert.equal(familyAuthFailedStatus(403), true);
  assert.equal(familyAuthFailedStatus(401), true);
  assert.equal(familyAuthFailedStatus(200), false);
});
