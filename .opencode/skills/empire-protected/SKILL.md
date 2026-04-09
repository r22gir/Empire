---
name: empire-protected
description: Guardrails for protected Empire business flows including WorkroomForge, CraftForge/Woodcraft, finance, pricing, orders, jobs, invoices, auth, and OpenClaw-adjacent changes
compatibility: opencode
---

## When to use me
Use this skill for any task touching:
- `workroomforge/`
- `craftforge/`
- finance or payment code
- pricing, orders, invoices, jobs, or persistence flows
- auth or session handling
- OpenClaw integration paths
- backend router registration or shared API contracts

## Core posture
Start in plan mode.
Read before editing.
Prefer the smallest safe change.
Treat this repo as near-production.

## Required steps before any edit
1. Read the relevant files first
2. List impacted files, routes, DTOs, DB touchpoints, and UI surfaces
3. State what could regress
4. Give a rollback plan
5. Only then propose the edit

## Hard rules
- Do not rename DB columns, route paths, DTO fields, or response shapes casually
- Do not change pricing, finance, invoice, order, or job behavior without explicit owner approval
- Do not alter auth/session behavior casually
- Do not invent missing docs or structure
- Do not claim a fix without pointing to the changed files and verification steps

## Special caution
If `backend/app/main.py` or router-loading behavior is involved:
- read it first
- list the currently relevant routers
- explain the blast radius
- do not edit until the change is clearly justified

## Output format
For protected-area tasks, produce:
- VERIFIED facts
- impacted files
- risk summary
- rollback plan
- regression checklist
