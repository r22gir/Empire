/**
 * Shared-client quotes stay in review, never auto. Mock records only.
 * Run: node --experimental-strip-types --test app/lib/docs-hub/jobRelatedDisplay.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  autoRelatedQuotes,
  isSharedClientReviewQuote,
  reviewRelatedQuotes,
} from './jobRelatedDisplay.ts';

const SHARED = 'f230cd42ff61aea9';

test('Willard addendums EST-2026-292/293 stay under review on Le Midi', () => {
  const related = {
    quotes: [{ id: 'q-midi', quote_number: 'EST-2026-0300', job_id: 'job-midi', customer_id: SHARED }],
    possibly_related: {
      quotes: [
        { id: 'q-292', quote_number: 'EST-2026-292', job_id: null, customer_id: SHARED, review: true, match_by: 'customer_id_shared' },
        { id: 'q-293', quote_number: 'EST-2026-293', job_id: null, customer_id: SHARED, review: true, match_by: 'customer_id_shared' },
      ],
    },
  };
  const auto = autoRelatedQuotes(related);
  const review = reviewRelatedQuotes(related);
  assert.deepEqual(auto.map((q) => q.quote_number), ['EST-2026-0300']);
  assert.deepEqual(review.map((q) => q.quote_number), ['EST-2026-292', 'EST-2026-293']);
  assert.equal(isSharedClientReviewQuote(review[0], 'job-midi'), true);
  assert.equal(isSharedClientReviewQuote(auto[0], 'job-midi'), false);
  assert.doesNotMatch(JSON.stringify(auto), /EST-2026-292|EST-2026-293/);
});
