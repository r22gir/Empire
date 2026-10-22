/**
 * Job JSON visuals + PDF hrefs. Mock records only.
 * Run: node --experimental-strip-types --test app/lib/docs-hub/jobVisuals.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { isSyntheticDocId, viewerHref } from './types.ts';
import { docViewerTarget, invoicePdfSrc, normalizePhotoSrc, quotePdfSrc, visualsFromJob } from './jobVisuals.ts';

test('sets job visuals from photos, drawings, and mockups JSON', () => {
  const docs = visualsFromJob({
    photos: [{ url: '/api/v1/photos/job/abc/room.jpg', filename: 'room.jpg' }],
    drawings: [{ url: '/api/v1/drawings/files/bench.pdf', filename: 'bench.pdf', title: 'Bench plan' }],
    mockups: ['/api/v1/drawings/files/mockup.pdf'],
  });
  assert.equal(docs.length, 3);
  assert.equal(docs[0].src, '/api/v1/photos/serve/job/abc/room.jpg');
  assert.equal(docs[0].kind, 'image');
  assert.equal(docs[1].title, 'Bench plan');
  assert.equal(docs[1].kind, 'pdf');
  assert.equal(docs[2].filename, 'mockup.pdf');
});

test('rewrites photo urls onto the serve route', () => {
  assert.equal(normalizePhotoSrc('/api/v1/photos/quote/q1/a.png'), '/api/v1/photos/serve/quote/q1/a.png');
  assert.equal(normalizePhotoSrc('/api/v1/photos/serve/quote/q1/a.png'), '/api/v1/photos/serve/quote/q1/a.png');
});

test('opens quotes and invoices on the real PDF routes', () => {
  assert.equal(quotePdfSrc('q-1'), '/api/v1/quotes-v2/q-1/pdf');
  assert.equal(invoicePdfSrc('inv-1'), '/api/v1/finance/invoices/inv-1/pdf');
  const t = docViewerTarget({ url: '/api/v1/drawings/files/plan.pdf', filename: 'plan.pdf' });
  assert.equal(t.src, '/api/v1/drawings/files/plan.pdf');
  assert.equal(t.kind, 'pdf');
});

test('synthetic job ids open the file src, not the docs-hub index', () => {
  const docs = visualsFromJob({
    photos: [{ url: '/api/v1/photos/serve/job/job-mock-hub/room.jpg', filename: 'room.jpg', title: 'Room photo' }],
  });
  assert.equal(isSyntheticDocId(docs[0].id), true);
  const href = viewerHref({ id: docs[0].id, src: docs[0].src, title: docs[0].title });
  assert.match(href, /src=%2Fapi%2Fv1%2Fphotos%2Fserve/);
  assert.doesNotMatch(href, /[?&]id=/);
});
