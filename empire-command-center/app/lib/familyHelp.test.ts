import assert from 'node:assert/strict';
import test from 'node:test';
import {
  EDITION_WHO,
  LOG_STATUSES,
  REQUEST_TYPES,
  STATUS_LABEL,
  TYPE_LABEL,
  statusOf,
  typeOf,
  whoLabel,
} from './familyHelpModel.ts';

test('PR 124 types and founder statuses are the only enums', () => {
  assert.deepEqual([...REQUEST_TYPES], ['adjust', 'fix', 'create']);
  assert.deepEqual([...LOG_STATUSES], ['new', 'planned', 'in_progress', 'done', 'declined']);
  assert.equal(TYPE_LABEL.adjust, 'Adjust');
  assert.equal(TYPE_LABEL.fix, 'Fix');
  assert.equal(TYPE_LABEL.create, 'Create');
  assert.equal(STATUS_LABEL.new, 'New');
  assert.equal(STATUS_LABEL.in_progress, 'In progress');
});

test('who labels are Juan/Max-e and Camilo/Maxine', () => {
  assert.equal(EDITION_WHO.amp, 'Juan / Max-e');
  assert.equal(EDITION_WHO.maxine, 'Camilo / Maxine');
  assert.equal(whoLabel({ edition: 'amp' }), 'Juan / Max-e');
  assert.equal(whoLabel({ edition: 'maxine' }), 'Camilo / Maxine');
});

test('type and status fallbacks', () => {
  assert.equal(typeOf({ id: '1', edition: 'amp', sender: 'Juan', message: '', created_at: '' }), 'adjust');
  assert.equal(typeOf({ id: '1', edition: 'amp', sender: 'Juan', message: '', created_at: '', request_type: 'fix' }), 'fix');
  assert.equal(statusOf({ id: '1', edition: 'amp', sender: 'Juan', message: '', created_at: '' }), 'new');
  assert.equal(statusOf({ id: '1', edition: 'amp', sender: 'Juan', message: '', created_at: '', log_status: 'done' }), 'done');
});
