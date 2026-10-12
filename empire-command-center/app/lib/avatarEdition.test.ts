import assert from 'node:assert/strict';
import test from 'node:test';
import {
  avatarFrameSrc,
  editionFromLocation,
  isFamilyAvatarEdition,
  normalizeAvatarEdition,
  resolveAvatarEdition,
} from './avatarEdition.ts';

test('amp maps to Max-e, maxine stays Maxine, workroom is Max', () => {
  assert.equal(normalizeAvatarEdition('amp'), 'max_e');
  assert.equal(normalizeAvatarEdition('max-e'), 'max_e');
  assert.equal(normalizeAvatarEdition('maxine'), 'maxine');
  assert.equal(normalizeAvatarEdition('workroom'), 'workroom');
  assert.equal(normalizeAvatarEdition('empire'), 'workroom');
});

test('Empire checkout uses workroom unless an amp/maxine hint is passed', () => {
  assert.equal(resolveAvatarEdition(null, 'empire'), 'workroom');
  assert.equal(resolveAvatarEdition('workroom', 'empire'), 'workroom');
  assert.equal(resolveAvatarEdition('amp', 'empire'), 'max_e');
  assert.equal(resolveAvatarEdition('maxine', 'empire'), 'maxine');
});

test('family editions never resolve to Max / workroom', () => {
  for (const family of ['amp', 'max_e', 'maxine'] as const) {
    assert.equal(resolveAvatarEdition(undefined, family) === 'workroom', false, family);
    assert.equal(resolveAvatarEdition('workroom', family) === 'workroom', false, `${family} ignores workroom hint`);
    assert.equal(resolveAvatarEdition(null, family) === 'workroom', false, family);
    assert.ok(isFamilyAvatarEdition(resolveAvatarEdition(null, family)));
  }
  assert.equal(resolveAvatarEdition(null, 'amp'), 'max_e');
  assert.equal(resolveAvatarEdition('workroom', 'maxine'), 'maxine');
  assert.equal(resolveAvatarEdition(null, { id: 'amp' }), 'max_e');
  assert.equal(resolveAvatarEdition('workroom', { id: 'maxine', avatarEdition: 'maxine' }), 'maxine');
});

test('iframe src carries the resolved edition, never a bare workroom default for family', () => {
  assert.equal(avatarFrameSrc('amp'), '/avatar.html?edition=max_e');
  assert.equal(avatarFrameSrc('maxine'), '/avatar.html?edition=maxine');
  assert.match(avatarFrameSrc('workroom', { fallback: 'none' }), /edition=workroom/);
  assert.match(avatarFrameSrc('workroom', { fallback: 'none' }), /fallback=none/);
  assert.equal(avatarFrameSrc(undefined, undefined), '/avatar.html?edition=workroom');
});

test('URL product=amp / edition=maxine is read as the current edition hint', () => {
  assert.equal(editionFromLocation('?product=amp'), 'amp');
  assert.equal(editionFromLocation('?edition=maxine&screen=presentation'), 'maxine');
  assert.equal(normalizeAvatarEdition(editionFromLocation('?product=amp')), 'max_e');
});
