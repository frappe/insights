# Content lifecycle: author → ship → customize

Type: grilling
Status: resolved

## Question

The producer side of the contract: how a dashboard/chart gets from an app
developer's hands into their app, and what happens when users touch it.

- Authoring: in Insights' builder, then export? What exactly exports?
- Shipping: what form in the app's codebase (folder of files? which hook)?
- Customization: what happens when a user edits shipped content — and what
  happens on app update?

Starting position (Saqib, from charting — probably a short ticket): author in
builder → export, ship as files in an app folder, customization =
duplicate/fork (no in-place merge; avoids conflict management / a full VCS).

Constraint to respect: the export format must stay stable — a future
code-first authoring API would emit the same format (see map fog).

## Answer

**One mechanism, redesigned.** Shipped desk content and workbook templates
converge on a single shipping channel. The current template machinery
(import-a-copy, `imported_version`/`imported_checksum`, warn+manual updates) is
an input, not the base — it migrates onto this design and retires.

**The shipped unit is a bundle of typed, named documents.** An app ships
`insights/<bundle>/` folders holding one JSON per named item in typed
subfolders (`query/`, `chart/`, `dashboard/`) plus a small `bundle.json`
(title, `required_apps`, format version). Internal references —
dashboard→chart, chart→query — are logical names, never docnames. Item names
are unique per app: `{app}/{name}` is a flat namespace, and bundle folders are
organization, not identity. The workbook does not appear in the shipping
format; it stays an authoring concept. This is the Studio/Builder folder idiom
(`studio/`, `builder_files/`), so the layout is native Frappe.

**Sync model: standard synced documents.** Bundles sync on
`after_migrate`/`after_app_install` into real Insights documents flagged
standard, carrying their `{app}/{name}` identity — the doc the resolver
returns. No import step, no gallery ceremony: shipped content exists on every
site after migrate, so a reference can never dangle. Sync is *declarative
reconcile*: an item removed from the bundle is deleted on migrate;
`before_app_uninstall` deletes the app's standard docs (user copies survive);
rename is not a v1 feature — the logical name is the identity, and a
`renamed_from` alias can be added to the format later if demand shows.

**Authoring: builder-first, two flows.**

- *Birth*: author as normal content in Insights' builder, then "Export to
  app…" writes the closure (dashboard + charts + queries) into the chosen
  app's bundle and flags the docs standard. A future code-first authoring API
  is just another producer of the same files.
- *Iteration*: on a `developer_mode` bench, standard docs are editable in the
  builder and save writes the JSON back to the app folder (Builder's
  `is_standard` round-trip).
- The blessed release path is author → export into the app repo → git review →
  normal app release. No production-site export flow.

**Format discipline.** One document per file, named by logical name; volatile
fields stripped (no `modified`, `owner`, hash names, cached results) so diffs
are content-only. One integer format version in `bundle.json`, owned by
Insights: append-only within a major (importers tolerate unknown keys),
breaking change bumps the major with a file-level migration. No per-file or
per-doctype versions. Exports assign each dashboard item a stable,
vendor-owned key — cheap, append-only, and the hook any future keyed
customization model hangs on.

**Customization: deferred, with a floor.** On a site, standard content is
read-only; "Duplicate" (a plain user copy) is the only customization for now.
This floor is explicitly interim — the duplicate-beside-original UX is
acknowledged debt. The real model (and the fork-resolution policy the
[Mount and renderer API](04-v1-contract-surface.md) ticket delegated here)
moves to a new grilling ticket,
[Site customization of shipped content](10-site-customization-of-shipped-content.md),
carrying as inputs: the
[overlay-prior-art research](../../research/03-customization-overlay-prior-art.md)
(verdict: item-keyed overlay is bounded under four rules — vendor-owned keys,
per-key replace, silent orphan skip, declared surface — with ordering/layout
as the proven danger zone) and the candidate design (site overlay shadowing
the standard at the same logical id, layout as one wholesale-replaced key).
Nothing on the current frontier depends on that choice: it is entirely behind
Insights' resolver, invisible to the mount contract and consumers.

**Migration.** The four shipped templates re-export into the new bundle
format; existing imported copies become user documents (they were
user-editable, so they are forks by definition); the gallery's "import"
becomes "duplicate"; the version/checksum update model retires.
