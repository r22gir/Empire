"""
BusinessOps Foundation models (Phase 1).

Source of truth: REPORT-businessops-tenantops-design.md and
REPORT-businessops-design-decisions.md (both on branch main as of
2026-06-09).

This file provides TWO layers, matching the existing repo's pattern:

1. SQLAlchemy ORM classes (Base from app.database) — used for OpenAPI
   documentation, type hints, and consistency with other models in
   backend/app/models/. They mirror the raw SQL DDL in the router.

2. The DDL strings themselves are not in this file. They live in
   backend/app/routers/businessops.py as `_BO_DDL`, and are applied
   via the `_init_businessops_schema(conn)` helper on first request
   (matching the VendorOps `vo_` prefix pattern).

Naming canon (D1-D9a):
  - BusinessOps (not TenantOps)
  - business_id (not tenant_id)
  - package (not plan / tier)
  - module_entitlement (not capability / access)
  - business_user, integration, provisioning_checklist

DB prefix: `bo_` (BusinessOps).

PII fields (per design doc §8):
  - businesses.contact_email, contact_phone, billing_email
  - business_users.email, display_name
  - business_audit_events.payload (may contain PII)

Secrets rule: NEVER store plaintext secrets. credential_ref_hash +
credential_ref_masked only. Mirrors VendorOps vo_accounts pattern.

Lifecycle rule: hard-delete is forbidden. ON DELETE RESTRICT for all
child FKs. The only ON DELETE CASCADE is for business_profiles
(1:1 extension).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from app.database import Base


# ──────────────────────────────────────────────────────────────────
# 1. Business — central org table (the customer organization)
# ──────────────────────────────────────────────────────────────────

class Business(Base):
    """The customer organization that buys and uses Empire products.

    Every other business-scoped table hangs off this one. Status
    lifecycle: prospect -> active -> paused -> canceled.
    """
    __tablename__ = "bo_businesses"

    id = Column(String, primary_key=True)                # biz_<ulid>
    slug = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    legal_name = Column(String, nullable=True)            # for invoicing
    business_type = Column(String, nullable=False, default="workroom")
    status = Column(String, nullable=False, default="prospect")
    timezone = Column(String, nullable=False, default="America/New_York")
    default_locale = Column(String, nullable=False, default="en")
    contact_email = Column(String, nullable=True)         # PII
    contact_phone = Column(String, nullable=True)         # PII
    billing_email = Column(String, nullable=True)         # PII
    website = Column(String, nullable=True)
    notes = Column(Text, nullable=True)                   # Founder-only
    metadata_json = Column(Text, nullable=True)           # JSON; free-form
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('prospect', 'active', 'paused', 'canceled')",
            name="ck_bo_businesses_status",
        ),
        Index("idx_bo_businesses_status", "status"),
        Index("idx_bo_businesses_type", "business_type"),
    )


# ──────────────────────────────────────────────────────────────────
# 2. BusinessProfile — 1:1 extension for module-specific profile fields
# ──────────────────────────────────────────────────────────────────

class BusinessProfile(Base):
    """Module-specific profile fields. 1:1 with Business.

    Designed to grow without ALTER TABLE churn. ON DELETE CASCADE
    from businesses (the design doc's only allowed cascade).
    """
    __tablename__ = "bo_business_profiles"

    business_id = Column(
        String,
        ForeignKey("bo_businesses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    apostille_states = Column(String, nullable=True)      # "DC,MD,VA"
    apostille_languages = Column(String, nullable=True)   # "en,es"
    workroom_specialties = Column(String, nullable=True)  # "drapery,upholstery,bedding"
    woodcraft_materials = Column(String, nullable=True)   # "oak,walnut,plywood"
    social_ig_handle = Column(String, nullable=True)
    social_fb_page = Column(String, nullable=True)
    social_linkedin = Column(String, nullable=True)
    extra = Column(Text, nullable=True)                   # JSON
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────
# 3. Package — the catalog of what can be sold
# ──────────────────────────────────────────────────────────────────

class Package(Base):
    """Canonical set of 'what does a customer get when they buy X'.

    Seeded with 6 rows in backend/app/data/seed/packages.json:
      pkg_starter, pkg_growth, pkg_empire, pkg_custom,
      pkg_apostille_only, pkg_founder.

    pkg_founder has is_internal=TRUE and is never sold.
    """
    __tablename__ = "bo_packages"

    id = Column(String, primary_key=True)                # pkg_<slug>
    display_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    monthly_price_usd = Column(Integer, nullable=False, default=0)
    annual_price_usd = Column(Integer, nullable=False, default=0)
    is_custom = Column(Boolean, nullable=False, default=False)
    is_internal = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    positioning = Column(Text, nullable=True)            # Founder-facing copy
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────
# 4. BusinessSubscription — what a business actually has right now
# ──────────────────────────────────────────────────────────────────

class BusinessSubscription(Base):
    """The live 'this business is on this package' record.

    UNIQUE INDEX on (business_id) WHERE status IN (pending, active,
    paused) enforces one active subscription per business (created
    in the router's DDL, since partial unique indexes need raw SQL).
    """
    __tablename__ = "bo_business_subscriptions"

    id = Column(String, primary_key=True)                # sub_<ulid>
    business_id = Column(
        String,
        ForeignKey("bo_businesses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    package_id = Column(
        String,
        ForeignKey("bo_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String, nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)  # nullable in v1
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'active', 'paused', 'canceled', 'expired')",
            name="ck_bo_subscriptions_status",
        ),
        Index("idx_bo_subs_business", "business_id"),
        Index("idx_bo_subs_package", "package_id"),
        Index("idx_bo_subs_status", "status"),
    )


# ──────────────────────────────────────────────────────────────────
# 5. ModuleEntitlement — the bridge from package to module
# ──────────────────────────────────────────────────────────────────

class ModuleEntitlement(Base):
    """For each (package, module) pair, what is the entitlement level.

    This is what MAX and the routers check. Access level enum:
      none / preview / internal / standard / full / founder_only
    """
    __tablename__ = "bo_module_entitlements"

    id = Column(String, primary_key=True)                # ent_<ulid>
    package_id = Column(
        String,
        ForeignKey("bo_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    module_id = Column(String, nullable=False)
    access_level = Column(String, nullable=False, default="none")
    limits = Column(Text, nullable=True)                  # JSON
    requires_approval = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("package_id", "module_id", name="uq_bo_module_ent_pkg_mod"),
        CheckConstraint(
            "access_level IN ('none', 'preview', 'internal', 'standard', 'full', 'founder_only')",
            name="ck_bo_module_ent_access_level",
        ),
        Index("idx_bo_module_ent_module", "module_id"),
    )


# ──────────────────────────────────────────────────────────────────
# 6. ProvisioningChecklist — the 12-step onboarding template
# ──────────────────────────────────────────────────────────────────

class ProvisioningChecklist(Base):
    """For each new business, a per-package checklist of provisioning tasks.

    step_key values (per design doc §6):
      lead_capture, business_profile, package_selection,
      payment_or_contract, module_entitlement_assignment (auto),
      business_user_invite, social_account_setup, vendor_setup,
      apostille_intake_setup, max_desk_routing (auto),
      notification_setup, launch_review
    """
    __tablename__ = "bo_provisioning_checklists"

    id = Column(String, primary_key=True)                # pc_<ulid>
    business_id = Column(
        String,
        ForeignKey("bo_businesses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    package_id = Column(
        String,
        ForeignKey("bo_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_key = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required = Column(Boolean, nullable=False, default=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String, nullable=True)
    notes = Column(Text, nullable=True)                   # may include customer's words (PII)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("business_id", "step_key", name="uq_bo_pc_biz_step"),
        Index("idx_bo_pc_business", "business_id"),
    )


# ──────────────────────────────────────────────────────────────────
# 7. BusinessUser — people who work at / for a business
# ──────────────────────────────────────────────────────────────────

class BusinessUser(Base):
    """A person who has access to a business on the platform.

    PII: email, display_name. NOT the same as app/models/user.py
    (the platform-level user). A business_user is qualified by
    business scope.
    """
    __tablename__ = "bo_business_users"

    id = Column(String, primary_key=True)                # bu_<ulid>
    business_id = Column(
        String,
        ForeignKey("bo_businesses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id = Column(String, nullable=True)              # platform user id (nullable for invited)
    email = Column(String, nullable=False)               # PII
    display_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="member")
    status = Column(String, nullable=False, default="invited")
    last_active_at = Column(DateTime, nullable=True)
    invited_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)
    removed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'vendor', 'customer_contact')",
            name="ck_bo_business_users_role",
        ),
        CheckConstraint(
            "status IN ('invited', 'active', 'suspended', 'removed')",
            name="ck_bo_business_users_status",
        ),
        UniqueConstraint("business_id", "email", name="uq_bo_business_users_biz_email"),
        Index("idx_bo_bu_business", "business_id"),
        Index("idx_bo_bu_email", "email"),
    )


# ──────────────────────────────────────────────────────────────────
# 8. BusinessIntegration — external connections (IG, FB, Stripe, etc.)
# ──────────────────────────────────────────────────────────────────

class BusinessIntegration(Base):
    """External systems a business has connected.

    Secrets rule: NEVER plaintext. credential_ref_hash + credential_ref_masked
    only. Mirrors vo_accounts pattern at vendorops.py:1058.
    """
    __tablename__ = "bo_business_integrations"

    id = Column(String, primary_key=True)
    business_id = Column(
        String,
        ForeignKey("bo_businesses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider = Column(String, nullable=False)            # 'instagram_graph', etc.
    account_ref = Column(String, nullable=True)
    credential_ref_hash = Column(String, nullable=True)
    credential_ref_masked = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    connected_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("business_id", "provider", name="uq_bo_bi_biz_provider"),
        CheckConstraint(
            "status IN ('active', 'expired', 'revoked')",
            name="ck_bo_bi_status",
        ),
        Index("idx_bo_bi_business", "business_id"),
    )


# ──────────────────────────────────────────────────────────────────
# 9. BusinessAuditEvent — unified audit log
# ──────────────────────────────────────────────────────────────────

class BusinessAuditEvent(Base):
    """Unified audit log for BusinessOps-relevant events.

    Append-only. Never deleted. payload may include PII (treat
    cautiously in exports).
    """
    __tablename__ = "bo_business_audit_events"

    id = Column(String, primary_key=True)
    business_id = Column(
        String,
        ForeignKey("bo_businesses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor = Column(String, nullable=False)               # 'founder' / 'system' / 'business:<ulid>' / 'vendor:<ulid>'
    action = Column(String, nullable=False)               # 'subscription.activated', 'entitlement.checked', etc.
    target_type = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
    payload = Column(Text, nullable=True)                 # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_bo_bae_business_time", "business_id", "created_at"),
        Index("idx_bo_bae_action", "action"),
    )


__all__ = [
    "Business",
    "BusinessProfile",
    "Package",
    "BusinessSubscription",
    "ModuleEntitlement",
    "ProvisioningChecklist",
    "BusinessUser",
    "BusinessIntegration",
    "BusinessAuditEvent",
]
