# 20 — Bundle shipping and declarative reconcile

Type: task
Status: resolved
Blocked by: 19
Spec: [spec-insights-foundation.md](../../spec-insights-foundation.md), "Bundle format and shipping" and "Sync: declarative reconcile"

## What to build

An app ships analytics as files, and every site that installs the app has
the content after migrate.

The format: an app ships `insights/<bundle>/` folders. Each bundle holds
typed subfolders (`query/`, `chart/`, `dashboard/`) with one JSON file per
item, named by logical name, plus a `bundle.json` (title, `required_apps`,
one integer format version). Item names are unique per app — `{app}/{name}`
is a flat namespace, bundle folders are organization, not identity. Internal
references are logical names, never docnames. The format version is owned by
Insights, append-only within a major, importers tolerate unknown keys.

The sync: bundles reconcile on `after_migrate` and `after_app_install` into
real Insights documents flagged standard, carrying their `{app}/{name}`
identity in the resolver's lookup field. Discovery walks the installed apps'
`insights/` directories — real installed apps, not a fakeable seam.
Reconcile is declarative and idempotent: new items are created, changed
items updated, removed items deleted. `before_app_uninstall` deletes the
app's standard docs. User copies survive both.

Standard docs are read-only on a site outside developer mode. Each bundle's
docs attach to one site-managed, Administrator-owned workbook per bundle,
created by sync and titled from `bundle.json` — a site-side container, not
part of the format. Shipped dashboards get their slug at sync: the logical
name, app-qualified only on collision, with a sync warning.

## Acceptance criteria

- [x] A fixture bundle syncs on migrate: docs exist, flagged standard, with
      logical ids, attached to a per-bundle workbook
- [x] Re-sync with no changes is a no-op, a changed file updates the doc, a
      removed file deletes it
- [x] Uninstall deletes the app's standard docs and spares user copies
- [x] Standard docs reject edits outside developer mode
- [x] Internal references (dashboard→chart, chart→query) resolve through
      logical names after sync
- [x] Shipped slugs assign at sync, app-qualified on collision with a warning

## Comments

2026-08-05 — built, in `insights/bundles.py`, with
`insights/tests/test_bundles.py` writing its fixture bundle to disk under the
Insights app's own `insights/` directory. Discovery only ever walks
`frappe.get_installed_apps()` and looks for directories, so a test cannot fake
an app into it; `insights` is the app the fixture ships from.

Reconcile is one pass. Read the files, read the app's standard documents by
`logical_id`, order the wanted items queries → charts → dashboards (queries
among themselves in reference order), and write each one with its references
already resolved to docnames. Whatever standard document is left over is
deleted, dashboards first. `_differs` is what makes it idempotent: an unchanged
item is not saved at all, so `modified` stays where the last real change left
it.

The unit of isolation is the app, not the bundle. The flat name namespace is
checked across an app's bundles, and an item whose file could not be read is
indistinguishable from one that was removed — so half an app is worse than
none. Each app reconciles inside its own savepoint; a failure is logged and
lands on `SyncReport.errors`, and `sync_bundles(strict=True)` re-raises instead,
which is what tests and a developer's own bench want.

Two things the ticket did not name but the machinery needs. A chart's
`data_query` — the chart-shaped query holding its summarize/order — is a
carried, remapped reference like `query`, otherwise a shipped chart draws its
own rows from the source query and the chart's configuration means nothing.
And the standard-document guard needs a request-scoped bypass beside the
per-document flag: deleting a chart deletes the `data_query` it owns, and that
document is loaded fresh by the controller, without flags. Uninstall fails
without it (verified by removing the check).

The container workbook is remembered as a site global keyed
`insights_bundle_workbook:{app}/{bundle}`. The honest home is a `logical_id` on
`Insights Workbook`, beside the one the three content doctypes carry; the
global keeps that one decision in one function until the field exists.

Two gaps in files this ticket does not own, both pre-existing:

- `InsightsChartv3.on_trash` deletes `data_query` before the standard-delete
  guard runs. Where the `data_query` is not itself standard, a blocked delete of
  a standard chart still destroys it.
- `InsightsDashboardv3.set_linked_charts` iterates `self.items` without a
  default, so a dashboard saved with `items` unset raises `TypeError`.
