# Stripe Go-Live Checklist

## Pre-Launch

- [ ] **Swap API keys in `backend/.env`**
  - Replace `sk_test_...` with `sk_live_...` from https://dashboard.stripe.com/apikeys
  - Replace `pk_test_...` with `pk_live_...` from the same page
  - Keys are on lines 32-33 of `.env`

- [ ] **Create live webhook endpoint in Stripe Dashboard**
  - Go to https://dashboard.stripe.com/webhooks
  - Add endpoint: `https://api.empirebox.store/api/v1/payments/webhook`
  - Subscribe to events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
  - Copy the new `whsec_...` signing secret and replace `STRIPE_WEBHOOK_SECRET` in `.env`

- [ ] **Verify SaaS price IDs still match**
  - `STRIPE_PRICE_LITE`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_EMPIRE` in `.env`
  - These should point to live-mode Product prices (not test-mode)
  - Create new products in live mode if needed at https://dashboard.stripe.com/products

## Go-Live Test

- [ ] **Test $1 charge** — Create a test invoice for $1 in the system, generate a payment link via `POST /api/v1/payments/invoice-link`, pay it with a real card
- [ ] **Verify webhook receives confirmation** — Check backend logs for `Webhook received: checkout.session.completed` and invoice status updated to `paid`
- [ ] **Verify payment recorded in DB** — Check `payments` table has the new row, invoice `balance_due` is $0
- [ ] **Verify notification sent** — Check `/api/v1/notifications` for the "Invoice Paid" notification

## Post-Launch

- [ ] **Enable auto-deposit invoice on quote acceptance** — When a customer accepts a quote, auto-generate an invoice for the deposit amount and send the Stripe payment link
- [ ] **Restart backend** after key swap: kill the uvicorn process and restart
- [ ] **Monitor first 5 real transactions** in Stripe Dashboard for any issues

## What's Already Built (No Code Changes Needed)

| Feature | Status | Endpoint |
|---------|--------|----------|
| SaaS subscription checkout | Working | `POST /payments/checkout` |
| Invoice payment links | Working | `POST /payments/invoice-link` |
| Webhook handler | Working | `POST /payments/webhook` |
| Payment status check | Working | `GET /payments/status/{session_id}` |
| Customer portal | Working | `GET /payments/portal` |
| Subscription management | Working | `GET /payments/subscriptions` |
| Payment history | Working | `GET /payments/history` |
| Auto invoice status update | Working | Webhook triggers `_update_invoice_status()` |
| Customer revenue tracking | Working | Auto-updates `customers.total_revenue` on payment |
| Internal notifications | Working | Sends via `/notifications/internal` on payment events |
| Failed payment alerts | Working | Sends via `/notifications/emergency` on failures |

## Architecture Note

The entire Stripe pipeline (Steps 1-9 of the money path) is built and tested. Only the live API keys are needed to start collecting real payments. No code changes required.
