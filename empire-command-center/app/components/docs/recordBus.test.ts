import test from 'node:test';
import assert from 'node:assert/strict';
import { recordHref } from './recordBus.js';

test('recordHref generates QuickBooks-style deep links with params', () => {
  assert.equal(
    recordHref({ type: 'customer', id: 'CUST-001' }),
    '/?screen=customer&id=CUST-001'
  );

  assert.equal(
    recordHref({ type: 'customer', id: 'CUST-001', tab: 'invoices', filter: 'open' }),
    '/?screen=customer&id=CUST-001&tab=invoices&filter=open'
  );

  assert.equal(
    recordHref({ type: 'job', id: 'JOB-0010' }),
    '/?screen=job&id=JOB-0010'
  );

  assert.equal(
    recordHref({ type: 'job', id: 'JOB-0010', tab: 'drawings' }),
    '/?screen=job&id=JOB-0010&tab=drawings'
  );

  assert.equal(
    recordHref({ type: 'quote', id: 'Q-1042' }),
    '/?screen=quote&id=Q-1042'
  );

  assert.equal(
    recordHref({ type: 'invoice', id: 'INV-2041' }),
    '/?screen=invoice&id=INV-2041'
  );

  assert.equal(
    recordHref({ type: 'payment', id: 'PAY-801' }),
    '/?screen=payment&id=PAY-801'
  );

  assert.equal(
    recordHref({ type: 'expense', id: 'EXP-101' }),
    '/?screen=expense&id=EXP-101'
  );
});

test('recordHref properly encodes URL special characters', () => {
  assert.equal(
    recordHref({ type: 'customer', id: 'John & Doe / Co' }),
    '/?screen=customer&id=John%20%26%20Doe%20%2F%20Co'
  );
});
