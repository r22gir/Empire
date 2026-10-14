import assert from 'node:assert/strict';
import test from 'node:test';
import { GUIDE_LINKS } from './companySetupLinks.ts';

test('company setup guide links every required screen', () => {
  const ids = GUIDE_LINKS.map((row) => row.id);
  for (const id of ['company-setup', 'pricing-studio', 'crm', 'whatsapp', 'calendar', 'account-setup']) {
    assert.equal(ids.includes(id), true, id);
  }
  const hrefs = GUIDE_LINKS.map((row) => row.href);
  assert.equal(hrefs.includes('/?screen=company-setup'), true);
  assert.equal(hrefs.includes('/?screen=pricing-studio'), true);
  assert.equal(hrefs.includes('/?product=crm'), true);
  assert.equal(hrefs.includes('/?screen=whatsapp'), true);
  assert.equal(hrefs.includes('/?screen=calendar'), true);
  assert.equal(hrefs.includes('/?product=social'), true);
});
