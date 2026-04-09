---
name: empire-zero-to-hero
description: Cross-product awareness for Empire workflows that span multiple products, event chains, integrations, and founder-critical business automations
compatibility: opencode
---

## When to use me
Use this skill for work that crosses product boundaries or may affect:
- LLC / onboarding flows
- payments or Stripe-connected behavior
- social / CRM / lead / contractor interactions
- event-driven automations
- founder-critical automation paths

## Operating mindset
Assume cross-product dependencies until proven otherwise.
A local-looking change may have downstream effects.

## Required behavior
- Identify upstream and downstream products touched by the change
- Identify events, triggers, or side effects
- Separate VERIFIED dependencies from INFERRED ones
- Flag any business-rule change for approval before editing

## Questions to answer before editing
- What starts this flow?
- What products consume its output?
- What events, jobs, or callbacks depend on it?
- What billing, auth, or persistence side effects exist?
- What would silently break if this changed?

## Output format
For cross-product work, include:
- product map
- dependency map
- risk summary
- approval points needed before editing
