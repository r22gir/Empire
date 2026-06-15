# EmpireBox Module Documentation

This directory is the durable current-state and update-document home for meaningful EmpireBox module changes.

Standard module layout:

- `docs/modules/<module-slug>/README.md`
- `docs/modules/<module-slug>/CURRENT-STATE.md`
- `docs/modules/<module-slug>/UPDATE-YYYYMMDD-<topic>.md`
- `docs/modules/<module-slug>/AUDIT-YYYYMMDD-<topic>.md`
- `docs/modules/<module-slug>/SPEC.md`

Use lowercase kebab-case module slugs. New module changes should add or update a current-state/update document here and then register it in the Command Center docs registry when it should appear in the module Docs UI.
