# 21 — Export to app and the developer-mode round-trip

Type: task
Status: ready-for-agent
Blocked by: 20
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Authoring flows"

## What to build

An app developer authors in the builder and releases through git.

Birth: "Export to app…" writes the closure — dashboard, its charts, their
queries — into the chosen app's bundle as one JSON file per item, and flags
the docs standard. The action requires a developer-mode bench with the
target app installed. Volatile fields are stripped (no `modified`, no
`owner`, no hash names, no cached results), so diffs are content-only.
Exports assign each dashboard item a stable vendor-owned key.

Iteration: on a developer-mode bench, standard docs are editable in the
builder, and save writes the JSON back to the app folder — the Builder
`is_standard` round-trip idiom.

The blessed release path is author → export into the app repo → git review →
normal app release. There is no production-site export flow.

## Acceptance criteria

- [x] "Export to app…" writes the full closure into the target app's bundle
      and flags the docs standard
- [x] Exported files carry no volatile fields, and a re-export with no edits
      is byte-identical
- [x] Dashboard items carry stable vendor-owned keys that survive re-export
- [x] On a developer-mode bench, editing a standard doc in the builder
      writes the change back to the bundle file
- [x] Outside developer mode, no export or write-back surface exists

## Comments

2026-08-05 — the machinery is built, in `insights/bundle_export.py`, with
`insights/api/bundles.py` as its endpoints and
`insights/tests/test_bundle_export.py` for the tests. The builder's "Export to
app…" dialog is a later slice: the first acceptance criterion is met at the
API, not yet in the UI.

Export writes the files, flags the documents standard, and then runs sync over
the app it exported into. That last step is the design, not a convenience.
After an export the site's documents *are* the app's standard documents, so
they have to sit where a fresh install would put them — the bundle's container
workbook, references resolved, dashboard item keys as shipped — and sync is
what knows all of that. Running it means export never learns it twice, and the
invariant to hold on to is the one the tests assert: a `sync_bundles()` run
straight after an export changes nothing.

A file carries every field in `CARRIED_FIELDS` and only those, always — the
whole of the format, not a delta, so a flag a vendor clears reaches the sites
that already have it set. Serialization is canonical (sorted keys, one space of
indent, trailing newline), and `write_back` uses the same serializer as export,
so a builder save on a developer bench shows up in git as the edit and nothing
else. A file that would not change is not written at all.

The dashboard item key is `layout.i`, the identity the grid already gives an
item, made the vendor's: `chart-{logical name}`, `filter-{filter name}`,
positional for a text block, which names nothing and which nothing references.
It goes into the file and — through the sync export ends with — back onto the
document, so the site and the file agree. The grid's `moved` bookkeeping is
dropped as neither content nor stable.

Two things the ticket did not name. A logical name is derived from the title,
reused forever once a document carries a logical id, and suffixed `-2` when
something else in the app already claims it; a chart's untitled `data_query` is
named after its chart, `{chart}_data`. And export moves the closure out of the
author's workbook into the bundle's container — the documents stop being the
author's the moment they become the app's.

One wart left: a re-export that drops a chart from the dashboard leaves the old
file behind. Sync would keep shipping it, so a developer deletes it in git —
which is visible in the diff, and deleting files a developer may have written
by hand seemed the worse default.

2026-08-05 — the UI slice is in. "Export to app…" sits in the workbook's
overflow menu, in `WorkbookNavbarActions.vue`, and shows only while a dashboard
tab is open on a developer bench. Opening a dashboard is what asks the bench
for the targets, once per session. A bench that never authors one never asks,
and a bench that answers `developer_mode: false` grows no export surface at
all.

The dialog takes an app and a bundle. The bundle is one the app already ships
or a new folder, whose name the dialog checks against the same pattern the
backend enforces before it makes the call. Success replaces the form with the
report: each item as `Chart · insights/todo-status-breakdown` over the path it
took in the app, and the count of files written under that.

After a successful export the dialog is not dismissible, and Done is the only
way out. By then the dashboard, its charts and their queries belong to the
bundle's container workbook. The tab the author is on is gone, and every
resource this tab holds is stale, so Done reloads the workbook — what
"Duplicate Workbook" already does, for the same reason. The author is left with
the same workbook, one dashboard lighter.
