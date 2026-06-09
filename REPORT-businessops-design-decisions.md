# REPORT — BusinessOps / TenantOps Design Decisions

**Repo:** `/home/rg/empire-repo-main` · **Branch:** `feature/businessops-tenantops-design` (off `main@8b0383c`) · **Date:** 2026-06-09
**Author:** Empire Completion Coordinator · **Scope:** decision capture only. **No code, no migrations, no DB changes.**

This is the short, signable companion to `REPORT-businessops-tenantops-design.md`. That doc is the **source of truth**; this doc is the **decision log** — what was accepted, what was rejected, what was deferred, what risks the Founder is carrying in v1, and what must be revisited before the first paying customer lands on `pkg_starter` or `pkg_apostille_only`.

---

## 1. Accepted decisions (Founder has signed off)

These are the 9 canonical decisions that every implementation phase must conform to. The Founder's standing message (2026-06-09) accepts them as the default direction.

### D1. **Canonical layer name: BusinessOps** (not TenantOps)
- **Accepted:** use `BusinessOps` everywhere — repo path, router, models, audit events, design docs, MAX knowledge, and the front-end sidebar (when it lands).
- **Founder-facing rationale:** "Business" is a word customers understand. "Ops" matches the existing `VendorOps` and `RecoverForge` naming.
- **Source:** design doc §3.

### D2. **Backend key: `business_id`** (not `tenant_id` / `customer_id` / `account_id`)
- **Accepted:** every new column, FK, URL param, and JSON field uses `business_id`.
- **Migration rule:** old `tenant_id` columns (SupportForge) coexist with new `business_id` columns; old code continues to read `tenant_id`; new code reads `business_id`. A later phase drops `tenant_id`.
- **Source:** design doc §3, §10.

### D3. **Sold unit: `package`** (not `plan` / `tier`)
- **Accepted:** the table is `packages`; the row id is `pkg_<slug>`; the API returns `package_id`.
- **Conflict rule:** the four legacy `tier` / `plan` / `licence` / `pricing_tier` fields stay as-is. The BusinessOps layer maps them:
  - `License.plan` (free / lite / pro / empire) — keep for hardware bundles; do NOT unify with SaaS packages.
  - `VendorOps.tier` (free / starter / pro) — keep the field; map at the API layer to `pkg_*`.
  - `supportforge_tenants.plan` (starter / growth / enterprise) — deprecate; new code reads `module_entitlements`.
  - Pricing page (lite / pro / empire) — Phase 7 aligns with packages.
  - Ecosystem catalog (lite / pro / empire / founder) — keep as Founder-facing copy; map names to `package_id` in BusinessOps.
- **Source:** design doc §3, §1.2.

### D4. **Access control: `module_entitlement`** (not `capability` / `access` / `module_access`)
- **Accepted:** the table is `module_entitlements`; the row id is `ent_<ulid>`; the per-(package, module) cell holds `access_level` + `limits` (JSON) + `requires_approval`.
- **Access level enum:** `none` / `preview` / `internal` / `standard` / `full` / `founder_only`.
- **Source:** design doc §2.5, §3.

### D5. **Initial packages (6):** Starter, Growth, Empire, Custom, Apostille-only, Founder/Internal
- **Accepted:** seed the `packages` table with exactly these 6 rows, with the access-level matrix from design doc §5.
- **Price placeholder:** `$29 / $79 / $199 / — / $49 / $0`. Founder accepts the placeholders; price validation against the DMV market is an open question.
- **Founder/Internal is a real package row**, not a flag on the business — same query serves all rows; the `is_internal` flag hides it from the pricing page.
- **Source:** design doc §5.

### D6. **ApostApp v1: Founder-mediated, not customer self-serve**
- **Accepted:** the customer submits an intake form on `/apostille/intake` (no login). The backend creates a `businesses` row + an `apostapp.customers` row + an `apostapp.orders` row. The Founder gets a Telegram notification via the new `POST /apostapp/notify-founder` endpoint. The Founder uses the apostille admin UI to generate a quote, mark paid, assign a vendor, and update the customer.
- **Access level:** `founder_only` for `pkg_apostille_only` and `pkg_empire` in v1. The customer has **no ApostApp account**.
- **Token-authenticated public status check:** the customer gets a token URL (`GET /apostapp/orders/{order_id}/status?token=...`) to poll their own order. No customer login.
- **Source:** design doc §7 example A, §8.

### D7. **Stripe v1: not in scope**; Founder-mediated Zelle/Venmo/wire first
- **Accepted:** every paid package bills monthly via Founder-mediated Zelle/Venmo/wire. The pricing page's "Buy" button calls `POST /vendorops/activation/checkout` which exists but is not wired to a real Stripe flow; this is acknowledged.
- **Stripe is deferred to Phase 5.** When it lands, every `stripe_*_id` lives in `business_integrations` with `credential_ref_hash` (never plaintext).
- **Founder cost:** every new customer means a manual invoice + a manual Zelle/Venmo/wire link in the email. The Founder's standing accounting handles this in v1.
- **Source:** design doc §5, §12.

### D8. **SocialForge auto-publish: blocked by default**
- **Accepted:** `business_integrations.auto_publish_enabled` column defaults to `FALSE` for every business in every package. The MAX `marketing.handle_task()` refuses `action='auto_publish'` unless ALL three gates pass:
  1. `business_integrations.auto_publish_enabled = TRUE`
  2. `module_entitlements.requires_approval = FALSE`
  3. The Founder has explicitly approved this business for auto-publish (recorded in `business_audit_events`)
- **In v1, no business qualifies.** Every SocialForge post is Founder-clicked-publish.
- **Source:** design doc §7 example C, §8, REPORT-module-widget-crosswalk.md top risk #5.

### D9. **OpenClaw: Founder-only, always**
- **Accepted:** OpenClaw is not a customer-facing module. Every package gets `access_level = 'founder_only'` for OpenClaw. The MAX desk `it.handle_task()` for OpenClaw bypasses entitlement (Founder is the operator).
- **Source:** design doc §4, §8.

### D9a. **Phase 1 scope: additive DB models + read-only admin API only**
- **Accepted:** Phase 1 ships exactly the items listed in design doc §9 Phase 1 and the gate summary below. No module rewiring, no customer-facing UI, no migrations beyond CREATE TABLE, no `vo_accounts` schema change.
- **Source:** design doc §9 Phase 1.

---

## 2. Rejected alternatives

The design spike considered 7 alternative directions and rejected them. The reason is recorded here so future work does not relitigate them.

### R1. **TenantOps / Tenant as the canonical name**
- **Rejected because:** "Tenant" is a developer concept (single software tenancy). "Business" is a customer concept. The Founder's word is `business`.
- **Side effect:** the existing `supportforge_tenants` table stays for now (its row is migrated to `businesses` in Phase 1) but no new code calls it a tenant.

### R2. **`tenant_id` as the canonical FK**
- **Rejected because:** `tenant_id` is overloaded by SupportForge today; the new layer would inherit that ambiguity.
- **Side effect:** the SupportForge `tenant_id` columns stay in Phase 1 (additive); a later phase drops them.

### R3. **Plan / Tier as the sold-unit name**
- **Rejected because:** five different naming schemes are already in use. Adding a sixth would make the fragmentation worse.
- **Side effect:** legacy `plan` / `tier` fields stay; the new layer is `package`.

### R4. **Capability / Access as the access-control name**
- **Rejected because:** `capability` is overloaded by MAX's `capability_registry.json`. `access` is too generic.
- **Side effect:** the existing `capability_registry.json` stays (internal MAX surface); BusinessOps uses `module_entitlement`.

### R5. **Customer self-serve ApostApp accounts in v1**
- **Rejected because:** no payment automation in v1, no transactional email service, no customer auth flow. A self-serve customer needs all three.
- **Side effect:** `pkg_apostille_only` is `founder_only` in v1. A self-serve option is on the v3 roadmap.

### R6. **Stripe-first billing**
- **Rejected because:** no Stripe account in v1, no webhook flow, no payout flow. Founder-mediated Zelle/Venmo/wire is the Founder's existing accounting and ships today.
- **Side effect:** the pricing page's "Buy" button is broken until Phase 5. Founder accepts the broken button.

### R7. **Auto-publish for any package in v1**
- **Rejected because:** the publish endpoints are live (`POST /socialforge/post/{instagram,facebook}`). A bug or misconfiguration could publish to a paying customer's account without review.
- **Side effect:** every business must have `auto_publish_enabled = FALSE` in v1. The founder flips it explicitly per business in a later phase, after auto-publish tooling is hardened.

---

## 3. Deferred decisions (explicitly out of scope for v1)

These are decisions the design spike surfaced but did not resolve. They are deferred to a later phase, lane, or revisit. They are listed here so a future agent does not assume they were forgotten.

### F1. **Stripe integration** (Phase 5, deferred)
- **Defer because:** no Stripe account, no webhook wiring, no payout flow.
- **Reopen when:** Founder sets up a Stripe account and approves the Stripe integration lane.

### F2. **Transactional email service** (Postmark / SendGrid / SES — deferred)
- **Defer because:** v1 customer emails are Founder-sent. The system records `apostille_customer_updates` so the audit trail is intact.
- **Reopen when:** Stripe lands, or when the manual email flow becomes a bottleneck (estimated at > 20 orders/week).

### F3. **SMS notifications** (Twilio — deferred)
- **Defer because:** no SMS use case in v1. The customer gets a token-authenticated status URL; the Founder gets Telegram.
- **Reopen when:** customers start asking "can you text me when it's ready?"

### F4. **Hard-delete of canceled businesses** (forbidden in v1)
- **Defer because:** append-only audit trail. FKs are `ON DELETE RESTRICT` on all child tables; `ON DELETE CASCADE` only on `business_profiles`.
- **Reopen when:** regulatory requirement (e.g. GDPR right-to-erasure) is binding. The current jurisdictions (DC/MD/VA / US federal) do not require hard-delete of B2B records.

### F5. **Per-module UI theming per package** (deferred)
- **Defer because:** a `pkg_apostille_only` business might want a stripped-down Command Center. The v1 Command Center is a single Founder-facing surface; the front-end `clientView` toggle handles per-context visibility, not per-package theming.
- **Reopen when:** the first paying customer asks "can I hide modules I don't use?"

### F6. **Self-serve customer onboarding** (deferred to v3)
- **Defer because:** v1 is Founder-mediated. Self-serve requires customer auth, self-serve payment, self-serve entitlement, and self-serve support — none of which are in v1.
- **Reopen when:** the Founder's pipeline exceeds what the Founder can handle manually (estimated at > 30 orders/week or > 5 paying businesses).

### F7. **Internationalization beyond English / Spanish** (deferred)
- **Defer because:** the DMV apostille market is bilingual. Other markets (Colombian land CRM, French-Canadian, etc.) are separate feature lanes.
- **Reopen when:** the first non-English/Spanish customer appears.

### F8. **Hardware bundle integration** (deferred)
- **Defer because:** the `License.hardware_bundle` field exists (Beelink bundles) but no BusinessOps coupling is needed. The hardware buyer is a single-Founder-operator flow.
- **Reopen when:** the hardware bundle becomes a SaaS customer (e.g. "buy a Beelink + 6 months Empire Starter").

### F9. **Multi-package per business** (rejected for v1; revisit if needed)
- **Defer because:** v1 has UNIQUE INDEX on `(business_id) WHERE status IN (pending, active, paused)`. A business can be on exactly one active package at a time.
- **Reopen when:** a customer asks "can I add Apostille to my Starter plan?" — at that point, either add a `business_subscription_addons` table or remove the UNIQUE.

### F10. **Per-business entitlement overrides** (deferred to v2)
- **Defer because:** v1 entitlements are purely package-driven. A per-business override table (e.g. "this customer gets SocialForge even though they're on Starter") is a v2 feature.
- **Reopen when:** the first customer asks for a custom module outside their package.

### F11. **`sf_tenants` → `businesses` backfill timing** (deferred to Phase 3)
- **Defer because:** Phase 1 only creates the new tables. Phase 3 (VendorOps + SupportForge) is when the SupportForge tenant model is wired into `businesses` and the existing tenants are backfilled.
- **Reopen when:** Phase 3 begins.

### F12. **`business=workroom` query param deprecation** (deferred to Phase 4)
- **Defer because:** v1 keeps the existing query param working. Phase 4 (Workroom / WoodCraft) introduces `business_id` as a real FK and the old param becomes legacy.
- **Reopen when:** Phase 4 begins.

---

## 4. Risks accepted for v1

The Founder is carrying these risks in v1. They are recorded so future work does not forget them.

| # | Risk | Severity | Mitigation in v1 | Owner |
|---|---|---|---|---|
| V1-R1 | The pricing page "Buy" button is broken (no Stripe wiring) | medium | The Founder knows. Customers get a "contact us" CTA or a Founder-mediated Zelle link. | Founder |
| V1-R2 | Customer emails are Founder-sent (no transactional email) | low | `apostille_customer_updates` table records every email for audit. | Founder |
| V1-R3 | ApostApp customer has no account (no customer auth) | medium | Token-authenticated status URL. Customer email + order_id + token = access. Token rotates per status change. | Phase 2 |
| V1-R4 | No SMS (customer has to check email or status URL) | low | The status URL is the primary surface; the email is the trigger to check it. | deferred |
| V1-R5 | SocialForge auto-publish is Founder-only | low (intentional) | The guard is enforced in the MAX marketing desk handler. No business can bypass it. | Phase 4 |
| V1-R6 | SocialForge calendar has no scheduler daemon (scheduled posts are stored, not published) | low (intentional) | The Founder reviews and clicks publish manually. | deferred |
| V1-R7 | No multi-package per business | low | UNIQUE INDEX enforces one active subscription. | revisit if needed |
| V1-R8 | No per-business entitlement overrides | low | v1 is purely package-driven. | v2 |
| V1-R9 | The pricing page tier names (`lite` / `pro` / `empire`) don't match the package ids (`pkg_starter` / `pkg_growth` / `pkg_empire`) | medium | The pricing page is Founder-facing copy. A URL map (Phase 7) handles the public-facing renaming. | Phase 7 |
| V1-R10 | Five tier-naming schemes coexist during the transition | medium | Each legacy scheme has a documented mapping rule in design doc §3. | ongoing |
| V1-R11 | SupportForge `tenant_id` and BusinessOps `business_id` columns coexist | low | New code reads `business_id`; old code reads `tenant_id`. Both work. | Phase 3 |
| V1-R12 | `vo_accounts.category` is still free-form until Phase 3 | low | New code validates against the proposed `vendor_type` enum; old code accepts strings. | Phase 3 |
| V1-R13 | `business=workroom` query param works but is not a real tenant scope | low | Existing 2 routes continue to work. New routes use `business_id` FK. | Phase 4 |
| V1-R14 | No subdomain per business yet | low | The `subdomain` field is in the `Tenant` model but not on `businesses` (deferred to F-style open question). | deferred |
| V1-R15 | Apostille 12-step task lifecycle runs in VendorOps, which has a broken alert runner | medium | Phase 1 ships the additive models. Phase 3 wires `run_apostille_alerts` additively (existing `run_once` unchanged). | Phase 3 |
| V1-R16 | No backup of the new tables in v1 | low | The existing `backend/data/` JSON storage has no backup policy. The new tables follow the same pattern. The Founder backs up `/data` manually. | ongoing |
| V1-R17 | The new entitlement helper is the only enforcement point | low | The helper is called from the MAX desk router. Module-level calls (e.g. `POST /apostapp/orders`) do not yet call the helper. Phase 2 adds the per-module call. | Phase 2+ |
| V1-R18 | The `check_entitlement` helper has no auth context in Phase 1 | low | Phase 1's read-only admin API uses Founder-only auth (a simple role check; auth scheme TBD in Phase 1 implementation). | Phase 1 |

---

## 5. Decisions that must be revisited before customer-facing SaaS

These are the 6 decisions that the Founder must explicitly revisit **before** a paying customer lands on `pkg_starter` or `pkg_apostille_only`. They are not blockers for the **Founder's own business** (which is `pkg_founder`), but they are blockers for the first external customer.

### RV1. **Customer auth model**
- **Today:** the customer has no account. Token-authenticated URLs are the only customer-facing surface.
- **Blocker for SaaS:** a paying customer on `pkg_starter` needs to log in to see their workroom data. Token URLs are not enough.
- **Re-decide:** customer auth via email magic link, password, or OAuth? Single business per user, or many businesses per user? Session duration?
- **Open question source:** design doc §11.4.

### RV2. **Stripe wiring (or Founder-mediated stays)**
- **Today:** Founder-mediated Zelle/Venmo/wire. The pricing page "Buy" button is broken.
- **Blocker for SaaS:** a paying customer cannot self-serve payment. Every new customer is a manual invoice.
- **Re-decide:** does the Founder want Stripe in the customer-facing SaaS path? If yes, Phase 5 must ship before the first paying customer.
- **Open question source:** design doc §11.3, §12.

### RV3. **Self-serve vs Founder-mediated onboarding**
- **Today:** every `pkg_*` business (except `pkg_founder`) requires Founder-mediated provisioning.
- **Blocker for SaaS:** a paying customer cannot sign up themselves. Every new customer is a 12-step Founder checklist.
- **Re-decide:** which packages are self-serve? `pkg_starter` and `pkg_growth` are obvious candidates. `pkg_empire` is Founder-mediated in v2.
- **Open question source:** design doc §12.

### RV4. **ApostApp customer self-serve**
- **Today:** `founder_only`. The customer submits an intake, the Founder handles the order.
- **Blocker for SaaS:** a paying customer on `pkg_empire` who wants to run their own apostille workflow needs a customer account.
- **Re-decide:** when does `pkg_empire` get a customer-facing ApostApp account? Phase 2? Phase 5? v2?
- **Open question source:** design doc §11.2, §7 example A.

### RV5. **Subdomain per business**
- **Today:** no subdomain. The SupportForge `Tenant.subdomain` column exists but no `businesses.subdomain` does.
- **Blocker for SaaS:** a paying customer on `pkg_empire` may want `acme.empirebox.store` (or similar) to host their workroom portal.
- **Re-decide:** add `businesses.subdomain`? Wildcard DNS? Per-business TLS? (Or: keep all customers on `app.empirebox.store/<business_slug>` and skip subdomains for v2.)
- **Open question source:** design doc §11.7.

### RV6. **License plan vs SaaS package unification**
- **Today:** `License` is for hardware bundles; `package` is for SaaS. They are separate.
- **Blocker for SaaS:** a customer who buys a Beelink + 6 months Empire Starter needs one purchase flow, not two.
- **Re-decide:** does the Founder want them unified? If yes, a `License → business_subscriptions` mapping is a small addition.
- **Open question source:** design doc §11.1.

---

## 6. What this decision record is NOT

- It is **not** the design doc. The design doc is `REPORT-businessops-tenantops-design.md`. This is the decision log.
- It is **not** a Phase 1 implementation plan. That is the gate summary in the closure report.
- It is **not** an audit. It does not check whether the design is correct; it records what was decided.
- It is **not** signed in the legal sense. It is a design artifact for the Founder to accept or override.

---

## 7. Sign-off

The Founder's standing message (2026-06-09) accepts all 9 decisions in §1 as the default direction. This document records that acceptance and the 6 deferred decisions in §5 that the Founder must revisit before customer-facing SaaS.

After this design lane is closed, the next step is the **Phase 1 implementation gate**, which is summarized in the closure report.

**End of decision record. No implementation performed. No migrations applied. No live DB changed.**
