# REPORT — BusinessOps / TenantOps Foundation Design

**Repo:** `/home/rg/empire-repo-main` · **Branch:** `feature/businessops-tenantops-design` (off `main@8b0383c`) · **Date:** 2026-06-09
**Author:** Empire Completion Coordinator · **Scope:** design spike only. **No code, no migrations, no DB changes, no live writes.**

## 0. Why this design spike exists

Per `EMPIRE-COMPLETION-PLAN.md` and `EMPIRE-MODULE-READINESS-REGISTRY.md`, BusinessOps / TenantOps is the **strategic #2 priority** (after MAX-first orchestration, before Apostille MVP, VendorOps routing, SocialForge bridge, and Drawing Sprint 2). All four workstreams either need `business_id`/`tenant_id` to be safe at scale, or they get blocked when the next paying customer arrives.

This spike answers: **what is the minimum viable foundation that lets EmpireBox sell, provision, and control access to modules per business/customer — without leaving any module behind, and without making any of the existing workstreams redo their data model from scratch?**

## 1. Fragmentation found

Today the repo carries **at least seven overlapping plan/tier/tenant-like primitives**, none of which talk to each other. Every one of them is a partial answer to "who can do what, how much does it cost, and what are they entitled to."

### 1.1 Real code (working systems)

| # | Primitive | Where | What it is | What it is NOT |
|---|---|---|---|---|
| 1 | **`sf_tenants` table** | `backend/app/models/supportforge_tenant.py` | First-class `Tenant` model: `id (UUID)`, `name`, `subdomain (unique)`, `plan` enum (starter / growth / enterprise), `settings (JSONB)`, `created_at`, `updated_at`, `deleted_at`. PostgreSQL-only (uses `JSONB`). | Not loaded into `main.py`. No router mounts it. No `supportforge_tenants` router file. **Orphaned model** — it exists but nothing reads or writes it. |
| 2 | **Tenant ID on every SupportForge table** | `supportforge_customer.py`, `supportforge_ticket.py`, `supportforge_kb.py`, `supportforge_automation.py`, `supportforge_integration.py`, `supportforge_agent.py` | Every SupportForge table has a `tenant_id` foreign key. This is the **only true multi-tenant pattern in the entire codebase.** | Not used by the router. `tenant_id` is the field name but no code path actually populates it from a request. |
| 3 | **`vo_accounts.category` (free-form)** | `backend/app/routers/vendorops.py:236, 329` | TEXT NOT NULL DEFAULT `'vendor'`. Already used in production for vendor records. | No enum, no FK, no validation. Apostille categories (`apostille_notary_dc`) are proposed as strings, not enforced. |
| 4 | **VendorOps TIERS dict** | `backend/app/routers/vendorops.py:25–67` | `TierName = Literal["free", "starter", "pro"]`. Hardcoded Python dict with `monthly_price_usd`, `approval_limit`, `account_limit`, `subscription_limit`, `automation`. Exposed via `GET /vendorops/plans`. | VendorOps-only. Not shared with other modules. Not driven by a DB. |
| 5 | **License key system** | `backend/app/models/license.py`, `backend/app/routers/licenses.py`, `backend/app/routers/llcfactory.py`, `backend/app/routers/preorders.py` | `License` model: `id (UUID str)`, `key (unique)`, `plan` (free / lite / pro / empire), `duration_months`, `hardware_bundle`, `status` (pending / activated / expired / revoked), `user_id`, `preorder_id`. Endpoints: `POST /generate`, `GET /{key}/validate`, `POST /{key}/activate`, `GET /my-licenses`. | Founder-mediates preorders, not customer self-serve. Not connected to module entitlements. Used for hardware bundles (Beelink). |
| 6 | **Tokens & Costs `tenant_id`** | `backend/app/routers/costs.py`, `app.services.max.token_tracker` | Per-tenant token usage tracking. `tenant_id` defaults to `"founder"`. | Cost-tracking only; not entitlement. No enforcement on what a tenant can do. |
| 7 | **`business_unit` field** | `backend/app/services/vision/product_catalog.py:11, 26, 38, 48, 59, 70, 80, 101, 111, 121` | Hardcoded `business_unit: "workroom"` or `"woodcraft"` on every vision product. String literal, not a FK. | Drawing Studio only. Single source of truth is a Python module. |
| 8 | **Pricing page (front-end copy)** | `empire-command-center/app/components/screens/PricingPage.tsx:8, 22, 37, 87, 189–254` | Three tiers: `lite ($29)`, `pro ($79)`, `empire ($199)`. Hardcoded in TSX. "14-day free trial" copy. Checkout calls `POST /vendorops/activation/checkout` which **does not exist as a working flow** (the route is declared but Stripe is not wired). | **UI copy is ahead of code.** A customer can click "Buy" today and the system will return an error. |
| 9 | **Ecosystem catalog SaaS tiers** | `backend/app/services/max/ecosystem_catalog.py:58–63` | `tiers: { lite: 29, pro: 79, empire: 199, founder: 0 }` in JSON inside the catalog. Read by MAX for "what should this cost" questions. | Catalog copy, not API. Not enforced. Not connected to license keys or VendorOps tiers. |
| 10 | **Sidebar `business=` query param** | `backend/app/routers/memory.py`, `backend/app/routers/avatar.py` | Two routes accept `?business=workroom|woodcraft` to filter results. | URL-level only, not a tenant concept. Not persistent. Not a real scoping primitive. |

### 1.2 The seven-tier-vs-plan inconsistency

The repo has **four different tier-naming conventions** in active use:

| Convention | Values | Lives in |
|---|---|---|
| SupportForge plan | `starter` / `growth` / `enterprise` | `supportforge_tenant.py:20` |
| VendorOps tier | `free` / `starter` / `pro` | `vendorops.py:25` |
| License plan | `free` / `lite` / `pro` / `empire` | `license.py:13` |
| Pricing-page tier | `lite` / `pro` / `empire` | `PricingPage.tsx:8, 22, 37` |
| Ecosystem-catalog tier | `lite` / `pro` / `empire` / `founder` | `ecosystem_catalog.py:58–63` |

None of these align. A customer who buys "Pro" on the pricing page would get a different entitlement set in SupportForge (where it's "Growth") and VendorOps (where it's also "Pro" but with different limits). This is the fragmentation pattern that the foundation must unify.

### 1.3 Other entitlement-like logic

- **MAX capability registry** (`app.services.max.empire_module_knowledge.py`): describes what MAX can and cannot do per module. Internal, not customer-facing.
- **MAX desk router keyword map**: `DESK_ALIASES` and `KEYWORD_MAP` route natural-language requests to desks. Not a customer entitlement.
- **Founder-approval gates**: scattered (VendorOps `explicit_founder_confirmation`, ApostApp `notify-founder` planned, SocialForge "no auto-publish" rule). Not a unified approval primitive.
- **Sidebar status badges** (`active` / `dev` / `planned`): module visibility, not entitlement. Belongs in the operating_registry, not in tenant scope.
- **ShipForge `shipping.py` PLACEHOLDER**: not a tier concern, but a module-safety concern.

### 1.4 Summary verdict

| Primitive | Real code? | Real entitlement? | Customer-facing? | Reusable across modules? | Action |
|---|---|---|---|---|---|
| `sf_tenants` | Yes (model only) | No (no router) | No | Yes (if wired) | Adopt as canonical, mount a router |
| SupportForge `tenant_id` FKs | Yes | Partial (no enforcement) | No | Yes | Adopt; require on every SupportForge write |
| `vo_accounts.category` | Yes | No (free-form) | No | Yes | Promote to `vendor_type` enum, validate |
| VendorOps TIERS | Yes (Python) | Yes (within VendorOps) | No | No | Move to DB; share with BusinessOps |
| License plan | Yes | No (not entitlement) | No | No | Keep for hardware bundles; don't unify with SaaS tiers |
| Tokens & Costs `tenant_id` | Yes | No (cost tracking) | No | No | Keep as-is; add `business_id` when BusinessOps lands |
| `business_unit` (vision) | Yes (hardcoded) | No | No | Limited (vision only) | Migrate to `business_id` lookup table |
| Pricing page | UI copy | No (calls dead endpoint) | Yes | No | Defer copy change until Phase 6 |
| Catalog tiers | JSON copy | No | No (MAX knowledge) | No | Keep as Founder-facing description |
| `business=` query param | Code | No (URL only) | No | Limited | Replace with `business_id` FK |

**Bottom line:** the repo has a real `Tenant` model in SupportForge, the bones of `tenant_id` foreign keys, and four inconsistent tier-naming schemes. **No module is multi-tenant in practice.** Every paying customer today gets either the founder's data or no data.

## 2. Canonical business/tenant model

**Design principles:**
1. **One concept, one name.** BusinessOps wins. The column is `business_id`. The catalog entity is `business`. The package concept is `package`. The entitlement is `entitlement`.
2. **Reuse where possible.** SupportForge's `sf_tenants` table is the prototype; widen its scope, mount a router.
3. **No destructive DB changes today.** Every new table is additive. Existing fields stay (License plan, VendorOps tier, SupportForge plan) as legacy. Migration of those is a later phase.
4. **DDL inside this doc only.** No `.sql` files. No Alembic. Just CREATE TABLE examples.
5. **PII-aware.** A `business` represents a customer organization, not a person. People live in `business_users`. Customer documents (apostille) are in `apostapp.orders` with a `business_id` FK. Legal docs (transcripts) are in `transcriptforge.orders` with a `business_id` FK.

### 2.1 `businesses` (the central table)

**Purpose:** the customer organization that buys and uses Empire products. Every other business-scoped table hangs off this one.

**DDL (illustrative only, NOT applied):**
```sql
CREATE TABLE businesses (
    id              TEXT PRIMARY KEY,            -- ULID/UUID; `biz_<ulid>` is the URL-safe form
    slug            TEXT UNIQUE NOT NULL,        -- `empire-workroom`, `cliente-juan-perez`
    display_name    TEXT NOT NULL,
    legal_name      TEXT,                        -- for invoicing; nullable
    business_type   TEXT NOT NULL DEFAULT 'workroom',  -- workroom / woodcraft / apostille / contractor / other (free-form for v1, enum in v2)
    status          TEXT NOT NULL DEFAULT 'prospect', -- prospect / active / paused / canceled
    timezone        TEXT NOT NULL DEFAULT 'America/New_York',
    default_locale  TEXT NOT NULL DEFAULT 'en', -- en / es
    contact_email   TEXT,                        -- PII; treated as such in audit logs
    contact_phone   TEXT,                        -- PII
    billing_email   TEXT,                        -- PII; nullable, falls back to contact_email
    website         TEXT,
    notes           TEXT,                        -- Founder-only; never shown to customer
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at    TIMESTAMP,                   -- when status moved to active
    canceled_at     TIMESTAMP,
    metadata        TEXT,                        -- JSON; free-form (e.g. external CRM id)
    CHECK (status IN ('prospect', 'active', 'paused', 'canceled'))
);
CREATE INDEX idx_businesses_status ON businesses(status);
CREATE INDEX idx_businesses_type ON businesses(business_type);
```

**PII:** contact_email, contact_phone, billing_email. **Treat as PII in audit logs and data exports.** Not encrypted at rest in v1 (matching the existing repo's pattern), but flagged for v2.

**First module consumers:** ApostApp (top priority), VendorOps, Drawing Studio, LLCFactory, LuxeForge, StoreFront Forge, ConstructionForge, ArchiveForge, SocialForge, SupportForge, ForgeCRM, LeadForge, MarketForge, RelistApp, ContractorForge.

### 2.2 `business_profiles` (one-to-one extension)

**Purpose:** keep `businesses` lean; put module-specific profile fields in a side table. Lets us add fields without ALTER TABLE churn.

**DDL:**
```sql
CREATE TABLE business_profiles (
    business_id     TEXT PRIMARY KEY REFERENCES businesses(id) ON DELETE CASCADE,
    -- Apostille profile
    apostille_states  TEXT,                  -- comma-separated: "DC,MD,VA"
    apostille_languages TEXT,                -- comma-separated: "en,es"
    -- Workroom profile
    workroom_specialties TEXT,                -- "drapery,upholstery,bedding"
    -- WoodCraft profile
    woodcraft_materials TEXT,                 -- "oak,walnut,plywood"
    -- Social profile
    social_ig_handle  TEXT,
    social_fb_page    TEXT,
    social_linkedin   TEXT,
    -- Free-form bag
    extra             TEXT,                   -- JSON
    updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**PII:** none (profile is org-level).
**First module consumers:** ApostApp, SocialForge, Workroom, WoodCraft.

### 2.3 `packages` (the catalog of what can be sold)

**Purpose:** the canonical set of "what does a customer get when they buy X." Single source of truth for tier names, prices, and limits.

**DDL:**
```sql
CREATE TABLE packages (
    id              TEXT PRIMARY KEY,            -- `pkg_starter`, `pkg_growth`, `pkg_empire`, `pkg_custom`, `pkg_apostille_only`, `pkg_founder`
    display_name    TEXT NOT NULL,                -- "Empire Starter", "Empire Growth", "Empire (full)", "Custom Build", "Apostille-only", "Founder / Internal"
    description     TEXT,                         -- for pricing page / sales
    monthly_price_usd  INTEGER NOT NULL DEFAULT 0, -- store as integer cents to avoid float issues; expose USD at API layer
    annual_price_usd   INTEGER NOT NULL DEFAULT 0,
    is_custom       BOOLEAN NOT NULL DEFAULT FALSE, -- custom packages skip price display
    is_internal     BOOLEAN NOT NULL DEFAULT FALSE, -- founder / internal — never sold
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    positioning     TEXT,                         -- Founder-facing positioning
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Seed data (v1):**
| id | display_name | price/mo | purpose |
|---|---|---|---|
| `pkg_starter` | Empire Starter | $29 | Empire Workroom + WoodCraft core + ForgeCRM + Tokens |
| `pkg_growth` | Empire Growth | $79 | Starter + Drawing Studio + SocialForge + LeadForge + MarketForge |
| `pkg_empire` | Empire | $199 | Growth + ApostApp + VendorOps + SupportForge + ArchiveForge + ContractorForge |
| `pkg_custom` | Custom Build | — | hand-priced bundle |
| `pkg_apostille_only` | Apostille-only | $49 | ApostApp + VendorOps only (the DMV market entry tier) |
| `pkg_founder` | Founder / Internal | $0 | the founder's own business; never sold |

**PII:** none.
**First module consumers:** the API layer; not used directly by module code.

### 2.4 `business_subscriptions` (what a business actually has)

**Purpose:** the live "this business is on this package" record. One row per active subscription; historical rows kept when a package changes.

**DDL:**
```sql
CREATE TABLE business_subscriptions (
    id              TEXT PRIMARY KEY,            -- `sub_<ulid>`
    business_id     TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    package_id      TEXT NOT NULL REFERENCES packages(id),
    status          TEXT NOT NULL DEFAULT 'pending', -- pending / active / paused / canceled / expired
    started_at      TIMESTAMP,
    activated_at    TIMESTAMP,                   -- when status moved to active
    current_period_start TIMESTAMP,
    current_period_end   TIMESTAMP,
    canceled_at     TIMESTAMP,
    cancellation_reason TEXT,
    stripe_subscription_id TEXT,                 -- nullable in v1 (Founder-mediated)
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('pending', 'active', 'paused', 'canceled', 'expired'))
);
CREATE INDEX idx_bs_business ON business_subscriptions(business_id);
CREATE INDEX idx_bs_package ON business_subscriptions(package_id);
CREATE INDEX idx_bs_status ON business_subscriptions(status);
```

**Unique partial index** to enforce "one active subscription per business":
```sql
CREATE UNIQUE INDEX uniq_bs_business_active
  ON business_subscriptions(business_id)
  WHERE status IN ('pending', 'active', 'paused');
```

**PII:** none on the row itself; links to PII via `business_id`.

**First module consumers:** Entitlements engine; pricing page; Founder admin.

### 2.5 `module_entitlements` (the bridge from package to module)

**Purpose:** for each (package, module) pair, what is the entitlement level. This is what MAX and the routers check.

**DDL:**
```sql
CREATE TABLE module_entitlements (
    id              TEXT PRIMARY KEY,            -- `ent_<ulid>`
    package_id      TEXT NOT NULL REFERENCES packages(id) ON DELETE CASCADE,
    module_id       TEXT NOT NULL,                -- 'apostapp', 'vendorops', 'drawing_studio', etc. (matches ecosystem_catalog keys)
    access_level    TEXT NOT NULL,                -- 'none' / 'preview' / 'internal' / 'standard' / 'full' / 'founder_only'
    limits          TEXT,                         -- JSON: {"monthly_orders": 50, "vendors": 10, "social_posts": 100, "drawings": 25}
    requires_approval BOOLEAN NOT NULL DEFAULT FALSE, -- must Founder approve each use?
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (package_id, module_id),
    CHECK (access_level IN ('none', 'preview', 'internal', 'standard', 'full', 'founder_only'))
);
CREATE INDEX idx_me_module ON module_entitlements(module_id);
```

**Access level semantics:**
- `none` — module is hidden from this business
- `preview` — module is read-only (e.g. sample data, demo mode)
- `internal` — usable by the founder's own staff, not exposed to customer
- `standard` — usable by the customer's own users, with limits
- `full` — usable without limits (Founder-tier)
- `founder_only` — only the founder can use it on behalf of this business (e.g. Apostille for now: founder handles the actual order, customer only submits intake)

**PII:** none.
**First module consumers:** MAX desk router; every router that needs an entitlement check.

### 2.6 `provisioning_checklists` (the 12-step onboarding template)

**Purpose:** for each new business, a per-package checklist of provisioning tasks. A "lead" gets created with the full checklist; tasks are marked done as they're completed.

**DDL:**
```sql
CREATE TABLE provisioning_checklists (
    id              TEXT PRIMARY KEY,            -- `pc_<ulid>`
    business_id     TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    package_id      TEXT NOT NULL REFERENCES packages(id),
    step_key        TEXT NOT NULL,                -- 'lead_capture', 'business_profile', 'package_selection', etc. (see §6)
    title           TEXT NOT NULL,
    description     TEXT,
    required        BOOLEAN NOT NULL DEFAULT TRUE,
    completed_at    TIMESTAMP,
    completed_by    TEXT,                         -- founder / system / business contact id
    notes           TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (business_id, step_key)
);
CREATE INDEX idx_pc_business ON provisioning_checklists(business_id);
CREATE INDEX idx_pc_open ON provisioning_checklists(business_id) WHERE completed_at IS NULL;
```

**PII:** notes field may include the customer's own words.
**First module consumers:** the Founder admin UI; the MAX desk for `intake` (Zara) and `clients` (Elena).

### 2.7 `business_users` (people who work at / for a business)

**Purpose:** a business has many users (the founder, staff, the customer's own staff, vendors who are invited into a business). This is **not** the same as `app/models/user.py` (the platform-level user). A `business_user` is a person who has access to one or more businesses on the platform.

**DDL:**
```sql
CREATE TABLE business_users (
    id              TEXT PRIMARY KEY,            -- `bu_<ulid>`
    business_id     TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    user_id         TEXT,                        -- nullable for invited-not-yet-registered users
    email           TEXT NOT NULL,               -- PII
    display_name    TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'member', -- owner / admin / member / vendor / customer_contact
    status          TEXT NOT NULL DEFAULT 'invited', -- invited / active / suspended / removed
    last_active_at  TIMESTAMP,
    invited_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at    TIMESTAMP,
    removed_at      TIMESTAMP,
    UNIQUE (business_id, email),
    CHECK (role IN ('owner', 'admin', 'member', 'vendor', 'customer_contact'))
);
CREATE INDEX idx_bu_business ON business_users(business_id);
CREATE INDEX idx_bu_email ON business_users(email);
```

**PII:** email, display_name. **PII handling required** (audit-log redaction, no plaintext export).
**First module consumers:** ForgeCRM, SupportForge, Workroom/WoodCraft staff access.

### 2.8 Optional: `business_integrations`

**Purpose:** track which external systems a business has connected (Instagram Graph, Facebook Graph, Stripe, QuickBooks, Google Drive, etc.). Holds the credential **reference** (never the secret itself).

**DDL:**
```sql
CREATE TABLE business_integrations (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL,                -- 'instagram_graph', 'facebook_graph', 'stripe', 'quickbooks', 'google_drive', etc.
    account_ref     TEXT,                         -- the public account id (e.g. ig @handle)
    credential_ref_hash   TEXT,                   -- SHA-256 of the credential, never the credential itself
    credential_ref_masked TEXT,                   -- human-readable masked form: 'sk_live_...4f2a'
    status          TEXT NOT NULL DEFAULT 'active', -- active / expired / revoked
    connected_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP,
    last_used_at    TIMESTAMP,
    UNIQUE (business_id, provider)
);
CREATE INDEX idx_bi_business ON business_integrations(business_id);
```

**PII:** none directly; account_ref can be (an IG handle is not strictly PII, an email is). Treat cautiously.
**Secrets:** never store plaintext. The `credential_ref_hash` + `credential_ref_masked` pattern matches `vo_accounts` (see `vendorops.py:1058`).
**First module consumers:** SocialForge (IG/FB), VendorOps (Stripe), ApostApp (future Stripe).

### 2.9 Optional: `business_audit_events`

**Purpose:** a unified audit log for everything BusinessOps-relevant (subscription changes, entitlement grants/revokes, integrations added, provisioning steps completed, approval events).

**DDL:**
```sql
CREATE TABLE business_audit_events (
    id              TEXT PRIMARY KEY,
    business_id     TEXT NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    actor           TEXT NOT NULL,                -- 'founder' / 'system' / 'business:<ulid>' / 'vendor:<ulid>'
    action          TEXT NOT NULL,                -- 'subscription.activated', 'entitlement.granted', 'integration.connected', 'provisioning.step_completed', 'approval.requested', 'approval.granted', 'approval.denied'
    target_type     TEXT,                         -- 'subscription' / 'entitlement' / 'integration' / 'checklist' / 'order' / etc.
    target_id       TEXT,
    payload         TEXT,                         -- JSON
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bae_business ON business_audit_events(business_id, created_at);
CREATE INDEX idx_bae_action ON business_audit_events(action);
```

**PII:** payload may include PII (customer email, customer name). Treat as PII when exported.
**First module consumers:** the Founder admin; future customer-facing audit-log view.

### 2.10 Lifecycle state machine

```
businesses.status:      prospect → active → paused → canceled
business_subscriptions: pending → active → paused → canceled → expired
business_users:         invited → active → suspended → removed
provisioning_checklists: (incomplete) → completed
module_entitlements:    (one row per package × module; immutable per (pkg, module) pair)
business_integrations:  active → expired / revoked
business_audit_events:  append-only, never deleted
```

A business cannot be deleted; it can only be `canceled`. This preserves audit trails forever. A physical DELETE is forbidden at the DB level (enforced by `ON DELETE RESTRICT` on all child FKs; `ON DELETE CASCADE` only for `business_profiles` because the profile is a 1:1 extension).

## 3. Naming decision (the canon)

| Concept | **Canonical name** | Rejected alternatives | Why |
|---|---|---|---|
| Product | **BusinessOps** | TenantOps, CustomerOps, AccountOps | Founder-facing. "Business" is a word customers understand. "Ops" matches the existing `VendorOps` and `RecoverForge` naming. TenantOps implies a single software tenancy (a developer concept); BusinessOps is a business concept. |
| Column / URL / API field | **`business_id`** | `tenant_id`, `customer_id`, `account_id` | Matches the existing repo's `business_unit` and `business=workroom` query param. `tenant_id` is overloaded (SupportForge already uses it). `customer_id` confuses org vs person. `account_id` is overloaded with `vo_accounts`. |
| What gets sold | **`package`** | `plan`, `tier` | "Package" is what customers buy. "Plan" is overloaded (License plan, SupportForge plan, business plan). "Tier" is internal-only (VendorOps tier, license tier). |
| What a package grants | **`entitlement`** | `capability`, `access`, `module_access` | "Entitlement" matches the OAuth/security vocabulary. "Capability" is overloaded with MAX capability_registry. "Access" is too generic. "Module access" is fine but verbose. |
| A person at a business | **`business_user`** | `member`, `seat`, `user_role` | A business has users. The "user" is qualified by the business scope. |
| An external connection | **`integration`** | `connection`, `link`, `binding` | Matches the existing `supportforge_integration` table. |
| The onboarding artifact | **`provisioning_checklist`** | `onboarding`, `setup`, `kickoff` | "Provisioning" matches IT/SaaS vocabulary. "Checklist" makes it obvious that there are steps to track. |

**Conflict resolution rule for legacy names:**
- `License.plan` → keep as-is. It's a different concept (hardware bundle activation). Don't unify.
- `VendorOps.tier` → keep the field name in VendorOps (`tier`), but map it to a `package` in BusinessOps. A business on `pkg_starter` gets VendorOps tier `starter`.
- `supportforge_tenant.plan` → keep the column for now, but plan a deprecation. New code reads `module_entitlements`. Old code reads the column.
- `pricing_tiers` on the front-end → rename to `packages` in a future front-end lane (not in this spike).
- `EMPIRE_CATALOG.tiers` (ecosystem_catalog.py) → keep as Founder-facing copy; map each tier name to a `package_id` in BusinessOps.

## 4. Module scoping map

| Module | Readiness | Needs `business_id` now? | When? | Notes |
|---|---|---|---|---|
| **ApostApp** | 🟠 ORANGE | **YES (top priority)** | Phase 2 | Top priority. New tenant, JSON → DB, every order needs `business_id`. |
| **VendorOps** | 🟡 YELLOW | **YES (top priority)** | Phase 3 | Top priority. `vo_accounts.category` → `vendor_type` enum. `apostille_tasks` table needs `business_id`. |
| **Drawing Studio** | 🟠 ORANGE | **YES** | Phase 4 | `business_unit: "workroom"` in vision/product_catalog.py grows to a real `business_id` lookup. |
| **LLCFactory** | 🟡 YELLOW | **YES** | Phase 5 | JSON → DB; orders need `business_id`. Stripe handoff needs `business_integrations`. |
| **LuxeForge** | 🟡 YELLOW | **YES** | Phase 5 | New tenant; `business_id` on measurements. |
| **StoreFront Forge** | 🟡 YELLOW | **YES** | Phase 5 | POS becomes multi-tenant. |
| **ConstructionForge** | 🟡 YELLOW | **YES** | Phase 5 | Colombian market tenant. |
| **ArchiveForge** | 🟢 GREEN | **YES** | Phase 4 | Already external-facing; add `business_id` to lifecycle records. |
| **SocialForge** | 🟡 YELLOW | **YES** | Phase 4 | `business_id` on `posts`, `campaigns`, `accounts`. Each business has its own connected IG/FB. |
| **SupportForge** | 🟠 ORANGE | **YES** | Phase 3 (already wired) | The `sf_tenants` model exists; promote to `businesses`. Backfill `tenant_id` → `business_id`. |
| **ForgeCRM** | 🟢 GREEN | **YES** | Phase 4 | `customer` and `contact` records need `business_id`. |
| **LeadForge** | 🟡 YELLOW | **YES** | Phase 4 | Campaigns and leads are per-business. |
| **MarketForge** | 🟡 YELLOW | **YES** | Phase 4 | Marketplace accounts and listings are per-business. |
| **RelistApp** | 🟡 YELLOW | **YES** | Phase 4 | `pricing_tiers` already (lite/pro/empire) — map to BusinessOps packages. |
| **ContractorForge** | 🟡 YELLOW | **YES** | Phase 4 | Shares intake+jobs+CRM with Workroom; needs `business_id` to disambiguate. |
| **Workroom / WoodCraft** | 🟢 GREEN | **YES (proto-tenant via `business=workroom`)** | Phase 4 | The `business=workroom` query param becomes a real `business_id` FK. |
| **Pricing Studio** | 🟢 GREEN | Inherits | Phase 4 | Reads `business_id` from the caller's context. |
| **AI Vision** | 🟢 GREEN | Inherits | Phase 4 | Inherits `business_unit` lookup from Drawing Studio. |
| **EmpireAssist** | 🟡 YELLOW | NO this sprint | Future | Helper layer under MAX. No business scope. |
| **EmpirePay** | 🟡 YELLOW | Inherits | Phase 4 | Tenant-scoped wallets. |
| **AMP** | 🟢 GREEN | NO | n/a | Personal dev. Platform only. |
| **MAX** | 🟢 GREEN | Platform | n/a | Routes by business via `business_id` in context. |
| **MAX Avatar** | 🟢 GREEN | Founder-only | n/a | Not a customer module. |
| **Owner's Desk** | 🟢 GREEN | Founder-only | n/a | Hidden from any tenant view. |
| **MAX Continuity** | 🟢 GREEN | Platform | n/a | Internal tool. |
| **Dashboard** | 🟢 GREEN | Per-business | Phase 4 | Dashboard filters by `business_id`. |
| **OpenClaw** | 🟡 YELLOW | NO | n/a | Local Ollama front. Founder-only. |
| **RecoveryForge** | 🟡 YELLOW | NO | n/a | Local-only. |
| **ShipForge** | 🔴 RED | After EasyPost wired | Phase 6 | Defer until stub is replaced. |
| **System** | 🟢 GREEN | Platform | n/a | Internal. |
| **Tokens & Costs** | 🟢 GREEN | YES | Phase 4 | Already has `tenant_id`; rename to `business_id` in a migration. |
| **PlatformForge** | 🟢 GREEN | Platform | n/a | |
| **Hardware** | 🟡 YELLOW | NO | n/a | Docs-only. |
| **VetForge** | ⏸️ PARKED | Future | After BusinessOps | Wait for BusinessOps. |
| **PetForge** | ⏸️ PARKED | Future | After BusinessOps | Wait for BusinessOps. |
| **Notifications** | 🟡 YELLOW | YES | Phase 4 | Per-business unread badge. |
| **Ecosystem Catalog** | 🟢 GREEN | Platform | n/a | Spine for tenant entitlement. |
| **MAX Code Mode / self_heal / git_operations** | — | **Founder-only** | Always | Per capability_registry.json. |
| **MAX Continuity** | — | Platform | n/a | Internal. |

**Customer-facing eligibility list (the v1 go-to-market answer):**
- ✅ **Customer-facing safe TODAY:** ArchiveForge, AMP (AMP is its own thing; outside BusinessOps scope), Drawing Studio (proto-tenant via Workroom/WoodCraft), Pricing Studio (proto-tenant).
- 🟡 **Customer-facing after BusinessOps Phase 2:** ApostApp, VendorOps (as vendor directory), SupportForge.
- 🟡 **Customer-facing after BusinessOps Phase 4:** SocialForge, LeadForge, MarketForge, RelistApp, ContractorForge, ForgeCRM, EmpirePay.
- ⛔ **NOT customer-facing until further hardening:** ShipForge (PLACEHOLDER), Drawing Studio (bench rewrite), OpenClaw worker (queue stalled), MAX Code Mode / self_heal / git_operations (founder-only), MAX Continuity (internal), Tokens & Costs (internal), RecoveryForge (local-only), VetForge / PetForge (parked).

## 5. Package / entitlement matrix (initial)

Each row says: for the listed package, what is the access level of each module? `none` means the module is hidden from the business; `standard` means the customer can use it; `founder_only` means only the founder acts on the business's behalf through this module.

| Module | `pkg_starter` ($29) | `pkg_growth` ($79) | `pkg_empire` ($199) | `pkg_custom` | `pkg_apostille_only` ($49) | `pkg_founder` ($0) |
|---|---|---|---|---|---|---|
| MAX chat | standard | standard | full | per contract | preview | full |
| Owner's Desk | founder_only | founder_only | founder_only | founder_only | founder_only | full |
| Empire Workroom | standard | standard | full | per contract | none | full |
| WoodCraft | standard | standard | full | per contract | none | full |
| StoreFront Forge | none | none | standard | per contract | none | full |
| ConstructionForge | none | none | standard | per contract | none | full |
| LuxeForge | none | none | standard | per contract | none | full |
| LLCFactory | none | standard | standard | per contract | none | full |
| **ApostApp** | none | none | **founder_only** | per contract | **founder_only** | full |
| ForgeCRM | standard | standard | standard | per contract | none | full |
| RelistApp | none | standard | standard | per contract | none | full |
| TranscriptForge | none | standard | standard | per contract | none | full |
| EmpireAssist (helper) | standard | standard | standard | per contract | none | full |
| EmpirePay | none | standard | standard | per contract | none | full |
| AMP | standard | standard | standard | per contract | standard | full |
| AI Vision | standard | standard | standard | per contract | none | full |
| Drawing Studio | none | standard | standard | per contract | none | full |
| Pricing Studio | standard | standard | standard | per contract | none | full |
| SocialForge | none | standard | standard | per contract | none | full |
| OpenClaw | founder_only | founder_only | founder_only | founder_only | founder_only | full |
| VendorOps | none | standard | standard | per contract | standard | full |
| RecoveryForge | founder_only | founder_only | founder_only | founder_only | founder_only | full |
| MarketForge | none | standard | standard | per contract | none | full |
| ContractorForge | none | standard | standard | per contract | none | full |
| SupportForge | none | none | standard | per contract | none | full |
| LeadForge | none | standard | standard | per contract | none | full |
| ShipForge | none | none | standard (after Phase 6 hardening) | per contract | none | full |
| ArchiveForge | standard | standard | standard | per contract | none | full |
| VetForge | none | none | none | per contract | none | full |
| PetForge | none | none | none | per contract | none | full |
| PlatformForge | founder_only | founder_only | founder_only | founder_only | founder_only | full |
| Hardware | none | none | none | per contract | none | full |
| System | founder_only | founder_only | founder_only | founder_only | founder_only | full |
| Tokens & Costs | founder_only | founder_only | founder_only | founder_only | founder_only | full |
| Notifications | standard | standard | standard | per contract | standard | full |
| MAX Continuity | founder_only | founder_only | founder_only | founder_only | founder_only | full |

**Notes:**
- `ApostApp = founder_only` in v1 means: the customer submits an intake on the landing page; the founder takes the order in `apostille/admin/orders/[id]`. The customer does not have an ApostApp account.
- `MAX chat = standard` in `pkg_starter` means: the customer can use MAX chat (via the public `/max` route) with their own subscription context.
- `ShipForge = standard` in `pkg_empire` is conditional on Phase 6 hardening (EasyPost wired). Until then, it's `none` for all packages.
- `pkg_founder` has `full` on every module because that's the founder's own business — but the routing layer still checks `business_id` so a customer who somehow gets `pkg_founder` on their account still cannot reach founder-only modules.

**Approval gates by default:**
- `requires_approval = TRUE` for: ApostApp, VendorOps, SocialForge (publish), Drawing Studio (bench output > 5 per day), OpenClaw (any task), ShipForge (any label purchase).
- `requires_approval = FALSE` for: everything else in `standard` access.

**Provisioning requirements (per package):**
- `pkg_starter`: business profile + 1 business_user (the owner) + 1 of (Workroom | WoodCraft) opted-in.
- `pkg_growth`: Starter + at least 1 social account connected OR 1 lead source connected.
- `pkg_empire`: Growth + ApostApp intake live + at least 1 vendor in VendorOps.
- `pkg_apostille_only`: business profile + 1 vendor (notary) in DC/MD/VA.
- `pkg_custom`: per contract; minimum: business profile + at least 1 opted-in module.
- `pkg_founder`: not provisioned; the founder is the operator.

**Billing assumptions (v1):**
- All packages bill monthly via Founder-mediated Zelle/Venmo/wire. Stripe is **not** wired in v1.
- `pkg_empire` and above assume the founder sets up a recurring invoice. `pkg_starter` is pay-as-you-go.
- The licensing system (`License` model) stays separate; it's for hardware bundles (Beelink), not SaaS.

**Customer-facing status (default per package):**
- `pkg_starter`, `pkg_growth`, `pkg_empire`, `pkg_apostille_only`: customer-facing once provisioned.
- `pkg_custom`: per contract.
- `pkg_founder`: never customer-facing.

## 6. Provisioning checklist (12 steps)

The 12 steps that turn a prospect into a paying/active business. Each step is a `provisioning_checklists` row with a `step_key`.

| # | step_key | Required? | Default for | What happens | Who does it | Approval gate? |
|---|---|---|---|---|---|---|
| 1 | `lead_capture` | YES | all | A prospect is created in the `businesses` table with `status='prospect'`. Captures: name, contact email, contact phone, what they're interested in, source. | Founder (manually) or via web lead form | NO |
| 2 | `business_profile` | YES | all | The business profile is filled in: legal name, business type, timezone, locale, addresses, website. | Founder (with prospect input) | NO |
| 3 | `package_selection` | YES | all | A `package` is chosen. A `business_subscriptions` row is created with `status='pending'`. The corresponding `module_entitlements` rows become queryable. | Founder (with prospect agreement) | NO |
| 4 | `payment_or_contract` | YES | all except `pkg_founder` | For paid packages: Founder marks "paid via Zelle YYYY-MM-DD" or signs a contract. For custom: contract signed. `business_subscriptions.status` moves to `active`. | Founder | NO (but `explicit_founder_confirmation` is the same concept) |
| 5 | `module_entitlement_assignment` | automatic | all | The chosen `package`'s `module_entitlements` rows are copied into a per-business effective entitlement set. (In v1 this is just a JOIN; in v2 it could be a per-business override table.) | System | NO |
| 6 | `business_user_invite` | YES | all | At least 1 `business_users` row with `role='owner'` and `status='active'`. | Founder | NO |
| 7 | `social_account_setup` | required for `pkg_growth`+ | growth/empire | At least 1 `business_integrations` row for Instagram or Facebook (if the package includes SocialForge). | Founder (with business) | NO (but `auto_publish_enabled=FALSE` until Founder flips it) |
| 8 | `vendor_setup` | required for `pkg_apostille_only`+ | apostille/empire | At least 1 `vo_accounts` row with `vendor_type='apostille_notary_dc'` (or equivalent for the market). | Founder | NO |
| 9 | `apostille_intake_setup` | required for `pkg_apostille_only`+ | apostille/empire | `apostille_tasks` table seeded with the 12-step lifecycle template. Landing page configured with business slug. | Founder + System | NO |
| 10 | `max_desk_routing` | automatic | all | MAX desk router learns the new business: maps `business_id` → allowed desks. For `pkg_starter`, only `forge` + `clients`. For `pkg_growth`, adds `marketing` + `sales`. For `pkg_empire`, full desk set. | System | NO |
| 11 | `notification_setup` | YES | all | The business is subscribed to the right Telegram group / email list. Founder + business contact both get notifications. | Founder | NO |
| 12 | `launch_review` | YES | all except `pkg_founder` | Founder signs off: profile is correct, package matches what was sold, billing is set, no module is exposed outside entitlement. The business moves to `status='active'`. | Founder | YES (Founder-only) |

**Lifecycle events after launch:**
- `businesses.status` transitions: `prospect → active → paused → canceled` (with `paused_at` / `canceled_at` timestamps).
- `business_subscriptions.status` transitions: `pending → active → paused → canceled → expired`.
- `business_users.status` transitions: `invited → active → suspended → removed`.
- `provisioning_checklists.completed_at` is set; never unset.

## 7. MAX-first routing impact

MAX's existing desk router (`backend/app/services/max/desk_router.py`) maps natural-language requests to desks. BusinessOps changes **what desks are reachable per request**.

**The MAX request flow with BusinessOps:**

```
1. MAX receives a request
   - From: web (ChatScreen), Telegram, email, phone (future)
   - Request carries: channel, user_id, business_id (if known), message, attachments

2. MAX identifies the business
   - If business_id is explicit in the request: use it.
   - Else: infer from channel (e.g. Telegram group → business_id from group metadata).
   - Else: infer from user_id (the business_users table maps user_id → business_id).
   - Else: route to "unknown business" — Founder-only path.

3. MAX checks entitlement
   - For each module the request might touch, look up module_entitlements for (package_id, module_id).
   - If access_level = 'none': refuse. Reply "this module is not in your package."
   - If access_level = 'founder_only': route to a Founder-only flow (Founder acts on the business's behalf).
   - If access_level in ('standard', 'full', 'internal'): continue.
   - If requires_approval = TRUE: queue for Founder approval; do not execute.

4. MAX checks module safety state
   - The module must be in the operating_registry with status != 'broken'.
   - If a module is in 'partial' or 'dev' state: warn the user, route with extra care.

5. MAX routes to desk/module
   - Use the existing desk_router with the filtered allowed-desks set.
   - The desk.handle_task() now receives business_id and can scope its work.

6. MAX asks for approval if needed
   - Either inline (if the user is the Founder) or queued (if the user is a customer).
   - Approval events go into business_audit_events.

7. MAX logs the action
   - Every request: business_audit_events row.
   - Every entitlement check: business_audit_events row with action='entitlement.checked'.
   - Every approval: business_audit_events row with action='approval.requested|granted|denied'.

8. MAX blocks unauthorized module use
   - At the router level: a check_entitlement(business_id, module_id, action) helper.
   - At the desk level: each desk's handle_task() validates the caller's business_id and the requested action's allowed access_level.
```

**Concrete examples:**

### Example A: Apostille customer order (DMV customer)
- 1. Customer on `/apostille` (no login in v1) submits intake form.
- 2. Backend creates a `businesses` row (status='prospect') + an `apostapp.customers` row + an `apostapp.orders` row.
- 3. `POST /apostapp/notify-founder` fires; Founder gets a Telegram message.
- 4. Founder opens the apostille admin: sees the new order tagged with `business_id`.
- 5. Founder uses MAX to ask "what's the status of order X?" → MAX identifies business → checks `apostapp` access_level = 'founder_only' for the business → routes to Founder-only flow → Founder sees the order details.
- 6. Founder generates a quote using `GET /apostapp/pricing-calculator`, marks the order paid, then assigns a vendor in VendorOps (which now has business_id and vendor_type='apostille_notary_dc').
- 7. The 12-step apostille_tasks are created and routed through the VendorOps alert runner.
- 8. Customer gets a status-check URL (token auth, no login) to poll `GET /apostapp/orders/{order_id}/status`.

### Example B: VendorOps vendor alert
- 1. VendorOps alert runner sees a renewal alert is due.
- 2. Looks up the `vo_accounts.category` → maps to `business_id`.
- 3. Checks `module_entitlements` for `(pkg_empire, vendorops)` → 'standard'.
- 4. Sends the Telegram message to the Founder (the customer contact doesn't get raw vendor alerts in v1).
- 5. Logs the event in `business_audit_events`.

### Example C: SocialForge social post
- 1. Marketing user at a `pkg_growth` business opens SocialForge.
- 2. Drafts a post, clicks "publish to Instagram".
- 3. Backend checks `module_entitlements` for `(pkg_growth, socialforge)` → 'standard'.
- 4. Backend checks `business_integrations` for `(business_id, 'instagram_graph')` → 'active' and not expired.
- 5. Backend calls `POST /socialforge/post/instagram` which uses the business's stored credential_ref to call the Graph API.
- 6. **CRITICAL GUARD:** the desk `marketing.handle_task()` refuses `action='auto_publish'` unless `requires_approval` is FALSE AND `auto_publish_enabled` is TRUE in `business_integrations`. In v1, both are FALSE by default — only the Founder can flip them per business.
- 7. The post is published; the event is logged in `business_audit_events`.

### Example D: Drawing Studio drawing request
- 1. Workroom user at a `pkg_growth` business opens Drawing Studio.
- 2. Submits a drawing request for a bench.
- 3. Backend checks `module_entitlements` for `(pkg_growth, drawing_studio)` → 'standard'. Limits include `{"drawings": 25}` per month.
- 4. Counts the business's drawings this month. If under limit, continues.
- 5. Routes to `forge` desk (Kai), which calls `bench_renderer.py`.
- 6. Returns the PDF/SVG to the user.
- 7. Logs the event with `module_entitlements` check + count.

### Example E: Workroom estimate/proposal
- 1. Workroom user at a `pkg_starter` business creates a quote.
- 2. `module_entitlements` for `(pkg_starter, workroom)` → 'standard'. No approval required.
- 3. Existing flow runs; the quote now has `business_id` in its metadata.
- 4. The business's ForgeCRM contact list and LeadForge pipeline can now see the quote (per entitlement).

## 8. Safety and privacy gates

A table of what is **Founder-only** until hardened, and what is **safe for customer use** in v1.

| Activity | Customer-safe in v1? | Founder-only until? | Notes |
|---|---|---|---|
| Submit intake form (no auth) | YES | — | The `/apostille/intake` form is a public form, no login. |
| View own order status via token | YES | — | Token-authenticated URL. |
| Receive email updates about own order | YES (Founder sends the email) | — | Founder-mediated until Stripe + transactional email lands. |
| Use MAX chat | YES (preview in `pkg_starter`, standard in growth+) | — | MAX is safe for chat. |
| Connect a social account (IG/FB) | NO | Founder-mediated; business contact provides credentials out-of-band; Founder connects | Auto-publish is blocked. Manual post is via Founder click only. |
| Publish a social post | NO | Always (Founder clicks publish) | The `marketing.handle_task()` refuses `action='auto_publish'` for any business. |
| Approve a vendor (VendorOps) | NO | Founder-only via `explicit_founder_confirmation` | Match the existing pattern. |
| Receive a vendor renewal alert | NO (Founder only) | — | The customer contact doesn't see vendor renewal noise. |
| Use ApostApp as a logged-in customer | NO | Founder-mediated for v1 | The customer has no ApostApp account. |
| Upload a document for an order | YES (no auth, just order_id) | — | Same as today. |
| View another business's data | NO (enforced by FK) | — | The router must include `business_id` in every query. |
| Use OpenClaw | NO | Founder-only | OpenClaw is internal. |
| Modify module entitlements | NO | Founder-only (Founder is the only actor with `role='owner'` at the platform level) | No customer has direct entitlement-write access. |
| Cancel a subscription | NO | Founder-mediated | Customer emails Founder; Founder clicks cancel. |
| Issue a refund | NO | Founder-only | Out of scope for BusinessOps. |
| Access Tokens & Costs | NO | Founder-only | Internal cost data. |
| Access System monitor | NO | Founder-only | |
| Use SupportForge as a customer | YES (in `pkg_empire`) | — | SupportForge is the only module that has working multi-tenant. New tenants get a fresh subdomain. |
| Edit `business_profiles.extra` | NO | Founder-only | The free-form bag is a trap; restrict to Founder. |
| Use VetForge / PetForge | n/a | Not exposed | PARKED. |
| Run a Bash command in MAX | NO | Founder-only | `code_mode: founder_only` per capability_registry. |
| Self-heal a broken module | NO | Founder-only | `self_heal.full_autonomous_repair_verified: false` today. |
| git_operations | NO | Founder-only | Per capability_registry. |

**PII rule:** any field marked PII in this design (contact_email, contact_phone, billing_email, business_user email, business_user display_name, customer email in business_audit_events.payload) is **never** included in a public API response, **never** written to a log line at INFO level (DEBUG only), and **never** exported in a CSV dump without explicit Founder approval. The audit log's `actor` field is allowed to be 'founder' or 'system' or `business:<ulid>` (no PII).

**Documents/files rule:** all customer documents (apostille orders, transcript orders) carry `business_id`. A file in `/data/apostapp/orders/<order_id>/` is implicitly `business_id=<orders.business_id>`. A file in `/data/images/` (used by RecoveryForge) is **internal-only** and never carries PII. ArchiveForge files carry `business_id`.

**Payment data rule:** v1 has no Stripe wiring. All payment records are free-form strings in the existing `apostapp.orders.payment` field. When Stripe lands (v2), every `stripe_*_id` lives in `business_integrations` (with `credential_ref_hash`), never in the order row.

**Legal disclaimer rule:** every customer-facing page (apostille, transcript, llcfactory, luxe) shows a "Not legal advice" disclaimer in the footer. This is enforced by the front-end `clientView` flag, not by BusinessOps.

**OpenClaw/browser automation rule:** OpenClaw is **always** Founder-only. The BusinessOps foundation does not give any business access to OpenClaw under any package. The MAX desk `it.handle_task()` for OpenClaw bypasses entitlement (Founder is the operator).

**Auto-publish rule:** `socialforge` auto-publish is **off** for every business in v1. The `business_integrations.auto_publish_enabled` column (default FALSE) is the gate. The MAX desk `marketing.handle_task()` for `action='auto_publish'` checks the column and refuses unless `auto_publish_enabled = TRUE AND requires_approval = FALSE AND Founder has explicitly approved this business for auto-publish`. In v1, no business qualifies.

## 9. First implementation sequence

The implementation is broken into 7 phases. **Phase 0 (this doc) is complete.** All other phases are gated on Founder approval and on prior phases passing.

### Phase 0 — Design only (THIS DOCUMENT)

**Objective:** document the canonical model, the package matrix, the provisioning checklist, the MAX routing impact, and the safety gates.

**Files touched:** `REPORT-businessops-tenantops-design.md` (created in this lane).

**Risk:** zero.

**Tests:** none.

**Rollback:** delete the file.

### Phase 1 — DB models + read-only admin API

**Objective:** create the new tables (businesses, business_profiles, packages, business_subscriptions, module_entitlements, provisioning_checklists, business_users, business_integrations, business_audit_events). Mount a read-only router that lists them. No writes yet. Seed the `packages` table with the 6 packages from §5.

**Files likely touched:**
- `backend/app/models/business.py` (new — single file with all 9 models for v1)
- `backend/app/models/__init__.py` (import the new models so SQLAlchemy creates the tables)
- `backend/app/routers/businessops.py` (new — read-only GET endpoints)
- `backend/app/main.py` (mount the new router; line 186 area)
- `backend/app/services/business/entitlements.py` (new — `check_entitlement(business_id, module_id, action)` helper)
- `backend/tests/test_businessops_models.py` (new)
- `backend/tests/test_businessops_router.py` (new)
- `backend/data/seed/packages.json` (new — seed data)
- `backend/data/seed/module_entitlements.json` (new — seed data for the matrix in §5)

**Risk:** **low** — additive only; no existing router is touched.

**Tests required:**
- `test_businessops_models.py`: each table can be created; unique constraints fire; FK constraints fire; ON DELETE CASCADE works for business_profiles only.
- `test_businessops_router.py`: GET endpoints return correct shapes; auth gate (Founder-only in v1) works.
- `test_businessops_entitlements.py`: `check_entitlement` returns correct access_level for each (package, module) pair from the seed data.

**Rollback path:** drop the new tables; revert `main.py` line 186; delete the new files. The existing `sf_tenants` and SupportForge `tenant_id` are untouched.

**Approval gates:** Founder must approve (a) the model file before any code merges, (b) the seed data, (c) the router surface area, (d) the read-only auth model.

### Phase 2 — ApostApp scoped to business

**Objective:** every apostapp row (customer, order, document) gets `business_id`. The `apostille_tasks` table from `REPORT-vendorops-apostille-design.md` is created. A `pkg_apostille_only` business can submit intake; the founder handles the order.

**Files likely touched:**
- `backend/app/routers/apostapp.py` — add `business_id` to all storage; new `POST /apostapp/notify-founder` endpoint; new `GET /apostapp/orders/{order_id}/status?token=...` public endpoint
- `backend/app/data/apostapp/` — migration to add `business_id` field to every JSON record
- `backend/app/models/apostille_vendor_task.py` (new) — same as REPORT-vendorops-apostille-design.md §4.1
- `backend/app/services/apostille/landing_lifecycle.py` (new) — the 12-step task creation on intake
- `backend/app/services/business/entitlements.py` (extend) — `check_entitlement` for apostapp actions
- `empire-command-center/app/apostille/intake/page.tsx` (new) — calls POST /customers + POST /orders with business_id
- `empire-command-center/app/apostille/admin/orders/[id]/page.tsx` (new) — Founder-only admin
- `backend/tests/test_apostille_intake_journey.py` (new)
- `backend/tests/test_apostille_business_id.py` (new)

**Risk:** **medium** — touches an in-production router. Migration of existing JSON records requires care.

**Tests required:**
- `test_apostille_intake_journey.py`: end-to-end intake → notify-founder → founder sees order.
- `test_apostille_business_id.py`: every order has business_id; queries without business_id fail.
- `test_apostille_status_token.py`: token-authenticated status endpoint works.
- `test_apostille_entitlements.py`: founder-only actions refuse non-founder callers (once auth is wired in Phase 5).

**Rollback path:** remove business_id from JSON records; remove apostille_tasks table; delete the new files. Apostapp retains its 15 existing routes (unchanged shape, just adds business_id to records).

**Approval gates:** Founder must approve (a) the data migration script, (b) the apostille_tasks table DDL, (c) the landing page, (d) the notify-founder endpoint, (e) the admin page.

### Phase 3 — VendorOps + SupportForge scoped to business

**Objective:** VendorOps' `vo_accounts.category` becomes a real `vendor_type` enum with apostille categories. `apostille_tasks` is wired to VendorOps alert runner. SupportForge promotes its `sf_tenants` model into the canonical `businesses` table; existing SupportForge tenants are backfilled.

**Files likely touched:**
- `backend/app/routers/vendorops.py` — add `apostille-tasks` endpoints from REPORT-vendorops-apostille-design.md §4.4
- `backend/app/services/vendorops_alert_runner.py` — add `run_apostille_alerts()` from §5.2
- `backend/app/routers/supportforge.py` (or wherever tenants are loaded) — add `businesses` router
- `backend/app/models/supportforge_tenant.py` — deprecation comment; new code reads `businesses`
- `backend/app/services/supportforge_migrate.py` (new) — backfill `sf_tenants` → `businesses`
- `backend/tests/test_vendorops_apostille_routing.py` (new)
- `backend/tests/test_vendorops_business_id.py` (new)
- `backend/tests/test_supportforge_tenant_backfill.py` (new)

**Risk:** **medium** — touches the alert runner (in production). Backfill of existing SupportForge tenants must be idempotent.

**Tests required:**
- `test_vendorops_apostille_routing.py`: 12-step lifecycle end-to-end.
- `test_vendorops_business_id.py`: every vendor account has business_id (or 'founder_default' for Founder's own vendors).
- `test_vendorops_apostille_alerts.py`: 24h-before / at-due / overdue alert triggers.
- `test_supportforge_tenant_backfill.py`: idempotent; existing tenants get business_id; new tenants go to businesses directly.

**Rollback path:** disable `run_apostille_alerts` in the alert runner start loop; backfill is read-only and doesn't change source data.

**Approval gates:** Founder must approve (a) the vendor_type enum values, (b) the alert message templates, (c) the SupportForge backfill script, (d) the merge order (VendorOps first, then SupportForge).

### Phase 4 — SocialForge bridge + MAX entitlement-aware routing

**Objective:** SocialForge accounts/posts/campaigns get `business_id`. MAX desk router checks entitlement before routing. The auto-publish guard is in place.

**Files likely touched:**
- `backend/app/routers/socialforge.py` — add `business_id` to all records; new `target_landing_page` on campaigns; `language` field on `/generate` (per REPORT-socialforge-apostille-gap.md §6.3)
- `backend/app/services/socialforge/apostille_campaigns.py` (new) — content library, read-only
- `backend/app/data/socialforge/` — JSON records gain `business_id`
- `backend/app/services/max/desk_router.py` — pre-check entitlement before desk routing
- `backend/app/services/max/marketing.py` (or wherever marketing desk lives) — refuse `action='auto_publish'` unless `business_integrations.auto_publish_enabled = TRUE`
- `backend/app/services/business/entitlements.py` (extend) — `check_entitlement` for socialforge actions
- `backend/tests/test_socialforge_business_id.py` (new)
- `backend/tests/test_socialforge_auto_publish_guard.py` (new)
- `backend/tests/test_max_entitlement_routing.py` (new)

**Risk:** **high** — MAX desk router is shared with Harry. The pre-check must be additive (the existing routing still works when no business_id is in the request, which is the Founder's own session).

**Tests required:**
- `test_socialforge_business_id.py`: every post/campaign/account has business_id.
- `test_socialforge_auto_publish_guard.py`: any attempt to auto-publish from a non-Founder-owned business is refused.
- `test_max_entitlement_routing.py`: a Founder-owned request still routes normally; a customer request is filtered to allowed modules.

**Rollback path:** disable the pre-check in `desk_router.py`; revert the marketing guard; remove the business_id from socialforge records. SocialForge retains its existing 21 routes.

**Approval gates:** Founder must approve (a) the marketing guard wording, (b) the MAX routing pre-check, (c) any change to existing desk behavior, (d) the socialforge migration.

### Phase 5 — Workroom / WoodCraft / Drawing Studio + Stripe wiring (deferred)

**Objective:** Workroom and WoodCraft become per-business. Drawing Studio gains a real `business_id` lookup (replacing the hardcoded `business_unit`). The first Stripe wiring goes in for `pkg_empire` customers.

**Files likely touched:** (deferred to a later lane; not in the v1 sequence)

**Risk:** **high** — Drawing Studio's quality issues and Stripe integration are each medium-to-high risk on their own.

**Approval gates:** Founder must approve (a) the Stripe account, (b) the per-business pricing model, (c) the Drawing Studio quality bar.

### Phase 6 — UI admin / provisioning screen

**Objective:** a Founder-only admin UI in the Command Center that lists all businesses, shows their status, runs the provisioning checklist, and shows the entitlement matrix per business.

**Files likely touched:**
- `empire-command-center/app/components/screens/BusinessOpsAdminPage.tsx` (new)
- `empire-command-center/app/components/screens/BusinessProfilePage.tsx` (new)
- `empire-command-center/app/components/screens/ProvisioningChecklistPage.tsx` (new)
- `empire-command-center/app/components/layout/LeftNav.tsx` — add a new "Admin" or "BusinessOps" entry
- `empire-command-center/app/lib/api.ts` — add businessops API helpers
- `frontend/tests/test_businessops_admin.ts` (new)

**Risk:** **low** — front-end only.

**Approval gates:** Founder must approve (a) the new sidebar entry, (b) the UI copy, (c) the data shown.

### Phase 7 — Pricing page realignment (deferred)

**Objective:** the pricing page at `/pricing` uses real package data from `GET /businessops/packages`. The `lite`/`pro`/`empire` tier names map to `pkg_starter`/`pkg_growth`/`pkg_empire`.

**Files likely touched:**
- `empire-command-center/app/pricing/page.tsx` (extend) — fetch packages from API
- `empire-command-center/app/components/screens/PricingPage.tsx` (extend) — render real package data
- `empire-command-center/app/lib/api.ts` — package helpers

**Risk:** **medium** — the pricing page is a customer-facing surface. The mapping between old tier names and new package IDs must be in the URL so old links don't break.

**Approval gates:** Founder must approve (a) the new pricing copy, (b) the URL mapping, (c) the merge order.

## 10. Compatibility and migration plan

**Backward compatibility with existing data:**

- `sf_tenants` rows → migrate to `businesses`. One-time SQL. New code reads `businesses`; old code reading `sf_tenants` continues to work until SupportForge is updated.
- `supportforge_*.tenant_id` → keep the column. Phase 1 adds a `business_id` column. Both can coexist. New code reads `business_id`; old code reads `tenant_id`. A later phase drops `tenant_id`.
- `vo_accounts.category` → keep the column as a free-form string. Phase 1 adds a `vendor_type` column with the enum. Both can coexist.
- `License.plan` → untouched. It serves a different purpose (hardware bundles).
- `VendorOps.tier` → keep. Map to `package_id` at the API layer; never store the package in VendorOps.
- `pricing_tiers` (RelistApp) → unchanged in v1; mapped in v2.
- `EMPIRE_CATALOG.tiers` → unchanged. This is Founder-facing copy.
- `business=workroom` query param → deprecated. Phase 4 introduces `business_id` query param. Old `business=` continues to work.

**No destructive DB changes today.** Every new column is additive. Every new table is additive. Every old table/column is untouched.

## 11. Open questions for Founder

1. **License plan vs package.** Should the `License` model be unified with the new `package` table, or stay separate (hardware-only)? My recommendation: keep separate. But the Founder may want them unified.
2. **`pkg_founder` is a real package row or a flag on the business?** My recommendation: a real package row (`pkg_founder` with `is_internal=TRUE`) so the same query serves all rows. The `is_internal` flag hides it from the pricing page.
3. **Pricing for `pkg_apostille_only` ($49).** Is this a real price to commit to, or placeholder? My recommendation: placeholder until validated against the DMV market.
4. **Multi-business-per-user.** Can a single person be a `business_user` at multiple businesses (e.g. the founder at both `empire_workroom` and `empire_woodcraft`)? My recommendation: yes; the `business_users` table allows it (no UNIQUE on `user_id`).
5. **Business deletion policy.** Today: `canceled` is the only terminal state. Should we support hard-delete after a retention period? My recommendation: no. Append-only audit trail. Founder can hide a canceled business from the UI.
6. **MAX `package_id` field.** Should MAX's chat state carry a `package_id` for context, or just a `business_id`? My recommendation: just `business_id`. The package is derived from `business_subscriptions`.
7. **Subdomain per business.** The SupportForge `Tenant` model has `subdomain` (e.g. `acme.support.empirebox.store`). Should the canonical `businesses` table also have a subdomain? My recommendation: yes, optional, for future per-business portals.

## 12. What this design does NOT cover

- **Stripe integration.** Deferred to Phase 5. The pricing page's "Buy" button is still broken until Stripe is wired.
- **Transactional email.** Deferred. Customer emails are Founder-mediated in v1.
- **SMS.** Deferred. Not in v1.
- **Hard-delete of canceled businesses.** Forbidden in v1. Append-only.
- **Per-module UI theming.** A `pkg_apostille_only` business might want a stripped-down Command Center. Deferred to a separate lane.
- **Self-serve customer onboarding.** v1 is Founder-mediated. Self-serve is v3.
- **Internationalization beyond English/Spanish.** The schema has `default_locale` but the front-end i18n machinery is separate.
- **Hardware integration.** The `License.hardware_bundle` field is preserved but not in scope for this spike.

## 13. Sign-off

This document is the **source of truth for the BusinessOps / TenantOps foundation**. Any code that contradicts this doc is a bug, not a feature.

Before Phase 1 begins, the Founder must explicitly approve:
1. The 7 naming choices in §3.
2. The 9 tables in §2.
3. The package matrix in §5.
4. The 12-step checklist in §6.
5. The MAX routing changes in §7.
6. The safety gates in §8.
7. The phased implementation plan in §9.
8. The compatibility / migration plan in §10.
9. The open questions in §11 (or accept the recommendations).

After approval, Phase 1 lands in a single branch off `main` with no destructive changes to existing data, and the read-only admin API is the only new surface.

---

**End of design spike. No implementation performed. No migrations applied. No live DB changed.**
