# 19 — Logical-id resolver and slug

Type: task
Status: ready-for-agent
Blocked by: none — can start immediately
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Logical ids and the resolver"

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

- [ ] Each reference form — logical id, slug, docname — resolves to the
      right document
- [ ] An unknown reference and a denied read return the same answer
- [ ] Slugs auto-generate from the title, are unique, and are editable on
      site-authored dashboards
- [ ] A user copy is never returned for a shipped logical id
