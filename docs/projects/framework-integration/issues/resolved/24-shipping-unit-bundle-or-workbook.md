# 24 — Shipping unit: bundle, or shipped workbook?

Type: grilling
Status: resolved
Blocked by: none — decide before any app ships content against the format

## Question

Is "bundle" a real domain concept, or a second name for a workbook an app
ships? The format is append-only once shipped, so this is the one decision on
the branch with a freezing deadline — everything else is app-internal code.

What this ticket decides:

- Whether the shipping format carries the workbook. Today `bundle.json` holds
  title, `required_apps` and `format_version`, and the workbook stays out of
  the format by decision of [Content lifecycle](03-content-lifecycle.md).
- Whether `Insights Workbook` gets a `logical_id`, making the container a
  shipped document with identity instead of site-side scaffolding.
- The name. "Bundle" appears in the format, the sync module and the glossary,
  and nowhere a user reads: the gallery says "Library", "Dashboards your
  installed apps ship", "Duplicate". A term that lives only between the file
  format and the sync code is an implementation name, not a domain term.
  "Workbook" is already the word users and the builder share.

Evidence that the code has already voted:

- Sync invents a container workbook per bundle because "the v3 builder is
  workbook-centric, so shipped documents need a workbook to live in"
  (`bundles.py`, module docstring). One artifact per bundle, Administrator-
  owned, titled from `bundle.json` — a workbook in everything but identity.
- `_container_workbook` names its own debt: the bundle→workbook mapping's
  "honest home is a `logical_id` on Insights Workbook"; until then it lives in
  a site global (`insights_bundle_workbook:<key>` in DefaultValue), with
  `_containers_of` grepping defaults to find them and `_cleanup_containers`
  garbage-collecting.
- `standard_content()` groups shipped dashboards *by container workbook* and
  presents each group as a bundle. The gallery's unit and the workbook are the
  same thing under two names.
- `duplicate_bundle` takes a workbook as its argument.

If a bundle is a shipped workbook: the manifest becomes the workbook file,
`logical_id` on Insights Workbook is the key, the site-global mapping dies,
`_cleanup_containers` becomes ordinary reconcile-deletion, and the glossary
loses a term instead of gaining one. The counter-argument to weigh: workbooks
carry site-side state (folders, sort order, preview images) that must not ship
— which may argue for a thinner workbook, not a second word.

Interlocks with [25](25-workbook-item-list-model.md): a workbook whose item
lists are derived is much cheaper to ship than one that stores them.

## Answer

**The shipping unit is the workbook. "Bundle" dies.** The container workbook,
`duplicate_bundle(workbook)`, and the gallery's grouping had already voted:
one artifact per bundle under two names. The counter-argument (site-side state
on the workbook) dissolved on inspection — the doctype holds only `title`,
`data_backup`, `from_template`; folders are a separate doctype linked to it,
and the item lists in `get_workbook_data` are already derived. The workbook is
thin enough to ship as it stands.

**Format.** `bundle.json` becomes `workbook.json`, same three keys. `title` is
the workbook's shipped field; `required_apps` and `format_version` are shipping
metadata that ride in the file and never land on the document. Nothing else is
added now — folders, ordering, layout are all append-only additions if demand
shows. The rename is free today and never again: nothing has shipped yet.

**Identity.** `Insights Workbook` gets the same pair the content doctypes
carry, and sync reconciles it as the fourth doctype. The accepted price: the
folder name is promoted from organization to identity — `{app}/{folder}` is
the workbook's Standard ID, so renaming the folder is delete-and-create, the
same event as renaming any shipped item (fixable later with the deferred
`renamed_from` alias). Item names stay flat per app; the folder still does not
namespace them.

**Rename: `logical_id` → `standard_id`, everywhere.** The framework's parallel
for this field is the docname itself (`Report`, `Workspace`: named by logical
name, `is_standard` + `module`), which Insights cannot use — user content
shares the doctypes, so docnames are hashes and only the shipped subset has
app-scoped names. The field stays; the name now says why it exists: only
standard content has one, and it pairs with `is_standard`. This amends ticket
04's "logical id" vocabulary.

**Invariant: an item is standard iff its workbook is.** `is_standard` stays
stored on items — it is load-bearing in DB filters and per-doc guards, and
sync is its only writer, so it is a cache with one writer, not two truths.
The invariant's consequence is a new rule: a standard workbook admits only
standard items; creating a user document inside one is blocked. That
eliminates the orphan branch outright — `_cleanup_containers`' "non-empty
container is forgotten, not deleted" case cannot arise, and workbook deletion
is ordinary reconcile-deletion.

**Named fates.** The `insights_bundle_workbook:<key>` site global dies via
patch (migrated into `standard_id`, then dropped), along with
`_container_workbook`, `_containers_of`, and `_cleanup_containers`.

**Vocabulary.** Glossary: "Bundle" replaced by "Standard workbook"; "standard
content" stays the collective noun; "Standard ID" earns an entry. User-facing
surfaces already never said bundle ("Library", "Duplicate") — nothing changes.
Code: no identifier keeps "bundle"; `bundles.py` → `standard_content.py` (it
is the standard-content module — sync, gallery feed, and guards for all four
doctypes), `api/bundles.py` follows, `duplicate_bundle` → `duplicate_workbook`.

## Acceptance criteria

- [x] A ratified answer: bundle stays a distinct concept, or the shipping unit
      is the workbook — with the manifest/format shape that follows
- [x] The `logical_id`-on-workbook question answered either way
- [x] `CONTEXT.md` updated: either "Bundle" earns its entry with a reason a
      workbook can't serve, or the entry is replaced
- [x] The container-workbook site global has a named fate
