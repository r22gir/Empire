import assert from 'node:assert/strict';
import test from 'node:test';
import {
  familyHomeRedirect,
  isFamilyChatsPath,
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

test('anonymous WhatsApp chats pages redirect to /login on amp and maxine', () => {
  for (const edition of ['amp', 'maxine']) {
    assert.equal(familyHomeRedirect(edition, '/amp/whatsapp/chats', false), '/login');
    assert.equal(familyHomeRedirect(edition, '/whatsapp/chats', false), '/login');
    assert.equal(familyHomeRedirect(edition, '/amp/whatsapp/chats', true), null);
    assert.equal(familyHomeRedirect(edition, '/whatsapp/chats', true), null);
  }
  assert.equal(isFamilyChatsPath('/amp/whatsapp/chats'), true);
  assert.equal(isFamilyChatsPath('/whatsapp/chats'), true);
  assert.equal(familyHomeRedirect('amp', '/amp/whatsapp', false), '/login');
  assert.equal(familyHomeRedirect('workroom', '/whatsapp/chats', false), null);
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
