---
name: empire-frontend
description: Working rules for Empire frontend and command-center changes, with focus on shared API clients, layout, auth, and low-regression UI updates
compatibility: opencode
---

## When to use me
Use this skill for any task touching:
- `empire-command-center/`
- frontend `app/` code
- shared API client usage
- layout, auth wrappers, or app-wide providers
- UI flows tied to protected backend contracts

## Frontend rules
- Verify the actual app structure before assuming default Next.js conventions
- Reuse the existing API client instead of duplicating fetch logic
- Reuse shared types instead of inlining incompatible shapes
- Be cautious with layout, i18n, auth wrappers, and page entry points
- Prefer minimal UI edits that preserve existing behavior

## Before editing
List:
- impacted pages/components
- impacted shared client calls
- impacted types
- impacted user flows
- backend contracts depended on by the UI

## Do not
- duplicate API logic
- silently change request/response expectations
- restructure layout or wrappers without reading the relevant files first
