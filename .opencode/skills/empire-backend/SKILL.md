---
name: empire-backend
description: Working rules for Empire FastAPI backend changes across routers, services, contracts, persistence, and background processes
compatibility: opencode
---

## When to use me
Use this skill for any task touching:
- `backend/`
- FastAPI routers
- shared schemas / DTOs
- DB queries or persistence
- background services and schedulers
- API contract changes

## Backend rules
- Verify the existing router-loading pattern before changing route registration
- Read the affected router, schema, service, and persistence layers before proposing a change
- Assume API contracts may be used by multiple products
- Do not rename fields, paths, or DB-facing names casually
- Be careful about SQLite dev vs PostgreSQL prod behavior
- Treat background workers, locks, schedulers, and monitors as operationally sensitive

## Before editing
List:
- impacted routers
- impacted schemas / DTOs
- impacted services
- impacted tables or persistence code
- downstream consumers likely affected

## Verification
Before marking complete:
- run focused tests where available
- run the smallest meaningful verification for the changed surface
- report any unverified assumptions explicitly

## Avoid
- broad refactors during narrow bugfixes
- silent contract changes
- touching unrelated routers while editing one backend issue
