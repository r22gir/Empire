import assert from 'node:assert/strict';
import test from 'node:test';
import { isPublicSignupEnabled } from './businessopsSignup.ts';

test('public signup is off unless the backend flag is explicitly true', () => {
  assert.equal(isPublicSignupEnabled(undefined), false);
  assert.equal(isPublicSignupEnabled(null), false);
  assert.equal(isPublicSignupEnabled({}), false);
  assert.equal(isPublicSignupEnabled({ public_signup_enabled: false }), false);
  assert.equal(isPublicSignupEnabled({ public_signup_enabled: true }), true);
});
