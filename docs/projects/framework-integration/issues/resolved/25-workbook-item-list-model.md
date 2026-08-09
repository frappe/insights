# 25 — Workbook item lists: stored or derived?

Type: grilling
Status: resolved
Blocked by: none — interlocks with 24, settle in the same wave

Note (from resolving 24, 2026-08-06): the server side has already moved — the
workbook doctype stores no item lists (fields: `title`, `data_backup`,
`from_template`), and `get_workbook_data` derives `queries`/`charts`/
`dashboards` via `get_all` on the items' `workbook` field. What remains of the
stored-list model is client-side: `mirrorTitleToWorkbook`, the index-as-route-
param rewrite, and the reload-after-duplicate. Re-verify the premise below
against the branch before deciding.

## Question

`Insights Workbook` stores its item lists (`queries`, `charts`, `dashboards`
as `[{name, title}]`) while every item document stores its own title and a
`workbook` link. One fact, two representations — and the branch keeps paying
for the copy:

- `mirrorTitleToWorkbook` (`workbook/workbook_items.ts`) watches every open
  item's title and writes it back into the workbook's list, debounced, with a
  `WeakSet` so a session-cached store doesn't stack a second mirror. Decent
  code for a problem that shouldn't exist.
- `WorkbookDashboard.vue` (and its query/chart siblings) accept an **array
  index** as a route param and rewrite the URL to the docname — the stored
  list is the index of truth, so a route has to speak list positions.
- `duplicateWorkbookItem` calls `workbook.load` after the copy to resync the
  list it just invalidated.
- Bundle sync creates items with `workbook` set and then needs nothing from
  the list — the list is derivable everywhere it is consulted.

What this ticket decides:

- Whether the item lists become derived — a query on the items' `workbook`
  field (plus `sort_order` for ordering) — and the stored child tables retire
  with a patch.
- What the workbook document still *stores* once lists are derived: title,
  folders, sharing, and whatever [24](24-shipping-unit-bundle-or-workbook.md)
  decides ships. This is the "thinner workbook" that makes shipping it cheap.
- The load contract for the builder: today one workbook fetch brings the item
  index; derived lists need the same in one round trip (a `get_items` on the
  controller, or fields on the workbook's `onload`).

The prize is deletion: the mirror, the index-route rewrite, the
reload-after-duplicate, and the class of drift bugs they guard against, gone
structurally rather than handled.

## Answer

**Derived, permanently — ratified, not built.** The server already moved:
`normalize_workbook.py` migrated the legacy JSON lists into real linked
documents, and the workbook's `as_dict` override derives
`folders`/`queries`/`charts`/`dashboards` from the items' `workbook` field on
every fetch. This ticket makes that final: stored item lists never return, so
the shipping format never grows list keys and ticket 24's invariants stand on
a settled model.

- **Ordering authority**: `sort_order` + `folder` on the items. The workbook
  owns no ordering.
- **Load contract**: lists arrive with the workbook fetch — one round trip,
  already proven. That the derivation lives in `as_dict` (so every full fetch
  pays four `get_all`s) is implementation freedom for later, not contract.
- **What the workbook stores**, post-24: `title`, `standard_id`,
  `is_standard`, plus `data_backup` (trash-restore machinery, untouched here)
  and `from_template` (retiring with the template channel).
- **Migration**: none needed — `normalize_workbook.py` already ran; the
  "patch drops child rows" criterion below was written against a stale premise.

**The client residue is handed off, not gated on.** What survives of the
stored-list model is a client-side snapshot the builder treats as a second
truth: `mirrorTitleToWorkbook`, the index-as-route-param rewrite in the three
Workbook item views, and the reload-after-duplicate. None of it can corrupt
shipped content (standard workbooks are read-only in the builder; the mirror
mutates only a client cache) and the shipping unit does not stand on it — so
its cleanup belongs to the parked **workbook state model** effort (see the
map's Out of scope), carried there as named debt: sidebar titles should read
from the loaded item store and fall back to the snapshot (mirror dies), routes
should speak docnames only (index rewrite dies), reload-after-duplicate is an
honest snapshot refresh and may stay.

## Acceptance criteria

- [x] A ratified answer: stored, derived, or derived-with-cache — with the
      builder's one-round-trip load story stated
- [x] The fate of `mirrorTitleToWorkbook` and the index-as-route-param
      behavior named in the decision (handed to the workbook-state-model
      effort as non-gating debt)
- [x] If derived: the migration path for existing workbook rows sketched
      (moot — `normalize_workbook.py` already ran; `sort_order` authority
      named)
