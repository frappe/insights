# 23 — Template migration and glossary

Type: task
Status: resolved
Blocked by: 21, 22
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Migration"

## What to build

The old shipping channel retires. One mechanism remains.

- The four shipped workbook templates re-export into the bundle format and
  sync as standard content.
- Existing imported template copies become user documents — they were
  user-editable, so they are forks by definition.
- The gallery's "import" becomes "duplicate", reusing ticket 22's action.
- The version/checksum update model (`imported_version`,
  `imported_checksum`, warn+manual updates, auto-apply on migrate) retires.
- `CONTEXT.md` gains the new glossary entries: Bundle, Standard content,
  Slug. The Template entry is revised to describe the bundle channel.

## Acceptance criteria

- [x] The four templates ship as bundles and appear as standard content
      after migrate
- [x] A site with imported template copies migrates cleanly: copies become
      user documents and keep working
- [x] The gallery offers "duplicate" and no import ceremony remains
- [x] The version/checksum machinery is deleted, tests included
- [x] `CONTEXT.md` records Bundle, Standard content, and Slug, and the
      revised Template entry

## Comments

2026-08-05 — done. The four bundles are `insights/insights/erpnext_{accounting,
purchasing,sales,stock}/`, written by the machinery rather than by hand: each
template imported on a developer bench, then each of its dashboards exported
with `bundle_export.export_dashboard`. 96 items — accounting 28, stock 26, sales
23, purchasing 19, one dashboard each. Verified on a site that has ERPNext: a
migrate creates all 96, every dashboard and every chart on it comes back through
the viewer endpoints, and a second sync writes nothing.

**They declare `Private` and `Viewer`, which is what the export produced.** Both
are the doctype defaults, and both are right here. `Viewer` authority means the
rows are filtered by whoever is looking, which is the only safe way to ship
AR/AP, spend and stock valuation. `Private` is the audience nobody has to be
talked out of: a vendor declaring `Everyone` would be publishing a site's
financials to every logged-in user on it, and that is a grant only the site can
make. So a shipped dashboard is admin-visible, and a site that wants an audience
duplicates and publishes its own — spec pin 4, arrived at rather than stumbled
into. *Worth a look in review:* the old library's copies were org-shared read, so
non-admins could see them; this is narrower on purpose, and the affordance that
would replace it is a site publishing its own copy.

`required_apps: ["erpnext"]` on all four, the same declaration the manifests
carried. A site without ERPNext ships none of them — verified by syncing on one,
which deleted all 96. That is also why the test site sees them as inert: they can
never interfere with the fixture bundle the tests write.

**Logical names come from titles, with one pin.** Four source queries share a
title with the chart drawn from them. The chart takes the bare name — it is the
id something outside Insights mounts — and the query was pinned to
`{chart}_source` before export, the way a chart's own `data_query` becomes
`{chart}_data`. Left alone the machinery would have shipped
`quotation-funnel-2.json`, which reads like an accident in a repo.

**Deleted:** `insights/api/templates.py`, `insights/workbook_templates/` (four
folders, manifests, workbooks and previews), the `insights_workbooks` hook, the
`sync_workbook_template_updates` call in `after_migrate`,
`insights/tests/test_workbook_templates.py`, `imported_version` and
`imported_checksum` on `Insights Workbook`, and the SPA's `OpenTemplate` route
and component.

**The patch does almost nothing, and that is the finding.** A template copy was
always user-editable, so it was already a fork: nothing about its content,
ownership or organization share has to change for it to keep working. All
`insights.patches.retire_workbook_template_updates` does is blank the two
update-model columns, which are orphans once the fields leave the doctype — raw
SQL, because there is no meta left to write through, and to the columns' empty
values, because an orphan column is still `NOT NULL`. `from_template` stays as
inert history. No `logical_id` was derived from it: a copy is not a duplicate of
anything this site ships, the bundles carry per-document identities those
documents never held, and the only available mapping would be title-matching
inside a workbook the site was free to rename.

**The gallery lists bundles and duplicates one whole.**
`bundles.standard_content()` groups the site's standard dashboards by their
container workbook, read through `frappe.get_list` so the visibility ladder
decides what is in it — `get_all` was the first cut and it ignores permissions,
which a test caught. `duplicate.duplicate_bundle(workbook)` is
`duplicate_dashboard` over every standard dashboard in that workbook, into one
new workbook, sharing one `copies` map so a chart two dashboards carry is copied
once. Ticket 22's semantics unchanged: `Private`, provenance `logical_id` kept,
authority under the new owner. It is named for the bundle, not the workbook,
because it only ever takes standard dashboards — an ordinary workbook answers
like a missing reference rather than quietly becoming a second "Duplicate
Workbook".

Ticket 22's un-owned change is made: the closure walk is
`bundles.dashboard_closure`, public and beside the format it walks, with
`LINK_COLUMN` and `query_references` alongside it. `duplicate.py` no longer
imports a private name out of a developer-bench module.

**The desk nudge lost its import.** It linked at `/template/{app}/{folder}`,
which imported on open; shipped dashboards now exist after migrate, so it links
at the slug. That needed the SPA's `get_dashboard_name` to go through the
resolver, which it now does — a shipped slug is a working SPA URL, and the v2
`old_name` lookup stays behind it.

*Left for review:* the library groups by the app in the logical id, so four
ERPNext dashboards sit under "Insights". The old library grouped by the
template's first required app on purpose. The honest fix is ERPNext shipping its
own bundles from its own app, which the format is built for, rather than a second
grouping rule here.

*Unrelated, found in passing:* `TestUserPermissionColumns` in
`insights_table_v3` fails — its stub for `get_permitted_columns_for_table` still
takes one argument after ticket 16 gave the real one a `user`. Pre-existing on
this branch.
