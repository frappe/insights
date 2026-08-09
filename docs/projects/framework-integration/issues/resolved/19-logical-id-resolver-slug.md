# 19 — Logical-id resolver and slug

Type: task
Status: resolved
Blocked by: none — can start immediately
Spec: [spec-insights-foundation.md](../../spec-insights-foundation.md), "Logical ids and the resolver"

## What to build

One server-side resolver turns any reference into the site-local document.
Accepted forms, for any dashboard: logical id `{app}/{name}`, slug, and
docname. Charts resolve by logical id and docname. Hash docnames never cross
the contract boundary — consumer apps ship logical ids only.

Shipped docs carry their logical id in a dedicated field, the resolver's
lookup key, extending the `from_template` convention already in the codebase.
Bundle sync (ticket 20) populates the field. This ticket tests the shipped
form against fixture docs carrying the field.

The dashboard doctype grows a `slug` field: unique, auto-generated from the
title for site-authored content. The docname stays a hash. Editing a slug is
cosmetic — internal references never use it.

Resolution policy under the v1 customization floor: a logical id resolves to
the standard doc, always. A failed resolution and a denied read return the
same answer, so the resolver leaks no existence information.

## Acceptance criteria

- [x] Each reference form — logical id, slug, docname — resolves to the
      right document
- [x] An unknown reference and a denied read return the same answer
- [x] Slugs auto-generate from the title, are unique, and are editable on
      site-authored dashboards
- [x] A user copy is never returned for a shipped logical id

## Comments

2026-08-05 — done. `insights/resolver.py` (`resolve`, `resolve_for_read`)
discriminates by shape — a slash is a logical id, otherwise docname then
slug — and `resolve_for_read` raises the same `ContentNotAvailableError` for
an unknown reference and a denied read. `_by_logical_id` keys on
`{logical_id, is_standard: 1}`, so a duplicate carrying the same logical id
never answers for it. `InsightsDashboardv3.set_slug` derives the slug from
the title only when empty and uniquifies it with
`append_number_if_name_exists`; the field stays editable afterward. Covered
by `insights/tests/test_resolver.py`.
