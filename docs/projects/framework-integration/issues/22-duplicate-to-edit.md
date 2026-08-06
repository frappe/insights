# 22 — Duplicate to edit

Type: task
Status: resolved
Blocked by: 17, 20
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Customization floor"

## What to build

The v1 customization floor. Standard content is read-only on a site —
"Duplicate" is the only customization: a server-side copy of the content
closure (dashboard, charts, queries) into a user-owned workbook, the same
shape template import produces today. The duplicate is an ordinary user
document with its own identity — it is never returned for the shipped
logical id. Duplicate requires authoring access.

The island's overflow menu gains "Duplicate to edit" on read-only shipped
content, driven by the capability flags, opening the duplicate in Insights
in a new tab.

The duplicate-beside-original UX is acknowledged debt. The real
customization model is ticket 10's open question and lands behind the
resolver later.

## Acceptance criteria

- [x] Duplicating a shipped dashboard creates a user-owned workbook with
      copies of the dashboard, its charts, and their queries
- [x] The copy is editable, the standard stays read-only, and the shipped
      logical id still resolves to the standard
- [x] Duplicate requires authoring access — a pure viewer cannot invoke it
- [x] "Duplicate to edit" appears in the island overflow only for shipped
      content and permitted users, and opens the copy in Insights

## Comments

2026-08-05 — built. `insights/duplicate.py` holds the copy, with the endpoint
beside export's in `insights/api/bundles.py`
(`duplicate_dashboard(dashboard) -> {"workbook", "dashboard"}`, the shape
template import already answers with). Tests in
`insights/tests/test_duplicate.py`, over the fixture bundle `test_bundles`
ships.

**The closure is export's walk, not a second one.** What a dashboard needs — its
charts, their `query` and `data_query`, and the queries a query reads — is one
definition, and it already lives in `bundle_export._closure`. A copy of that walk
would drift the first time an edge is added. *Un-owned change this wants:*
`_closure` is private and export is a developer-bench module, so a duplicate on
an ordinary site now imports a private name out of it. It should be public, and
probably not in `bundle_export` at all.

`CARRIED_FIELDS` is the other reuse: the fields a bundle ships are exactly the
fields a copy takes, and everything a copy must not take (the workbook, folders,
previews, slug, `linked_charts`) is already outside that set for the same reason.

**Two gates, two different questions.** The role on the whitelist says the caller
may author at all; `resolve_for_read` inside says they may have this dashboard.
An audience member without an authoring seat is refused by the first, an author
outside the audience by the second — in the words every other missing reference
gets. The read on the dashboard is the whole check: its audience is what carries
the charts on it, and the queries behind them are what a viewer never receives
directly anyway.

**The copy starts Private — the pin worth arguing about.** A shipped
`visibility` is the vendor's declaration about the original. Carrying it would
make duplicating a way to re-publish someone else's audience under a document
its new owner controls, which is a grant nobody made. So the copy is a draft:
`Private`, `visible_to_roles` empty, published by its owner or not at all.

**`data_authority` carries, but the author it names has changed.**
`get_authority_user_for` reads the authority off the document and resolves
`Author` to the document's `owner` — and the copy's owner is whoever duplicated
it. A chart shipped `Author` therefore runs under the duplicator in the copy,
never under the original's owner (Administrator, for shipped content). Combined
with the `Private` reset, a copy can never show rows its owner could not already
reach, which is what makes carrying the declaration safe rather than a
privilege leak. Verified in
`test_the_declared_authority_carries_over_under_the_copys_owner`.

**Provenance, not identity.** The copy keeps the `logical_id` it was made from
and sets `is_standard = 0`. The resolver's shipped-id lookup keys on both, so the
copy never answers for the id; uninstall spares it for the same reason. The copy
lands in a workbook of the caller's own — never the bundle's container, which
would keep the container alive after the bundle that made it is gone.

**The island side is one `menuOptions` entry** on `doc.can_duplicate`, beside
the `can_edit` one, calling through `islands/viewer.ts`. The overflow closes on
click, so the title row answers instead: "Duplicating…" while it runs, and a
failure line in its place — the same inline idiom the cards use, and no toast
infrastructure the islands do not have. On success the copy opens in Insights
through the navigation adapter, the same new tab "Edit in Insights" uses.

*Known edge:* that new tab is a `window.open` after an awaited request, so a
duplicate slower than the browser's activation window (~5s in Chrome) is popup-
blocked and the user has to click again. The copy is a handful of inserts and
lands well inside it in practice; the honest fix is an affordance that survives
the round trip, which is worth doing when the surface gets a real feedback
primitive.

Measured, production build, JS + CSS raw (gzip):

| entry | ticket 18 | now |
| --- | --- | --- |
| `insights_chart` | 89.5 + 45.8 kB (31.5 / 7.0) | 89.5 + 47.3 kB (31.5 / 7.1) |
| `insights_dashboard` | 110.1 + 46.7 kB (37.5 / 7.2) | 110.8 + 48.2 kB (37.7 / 7.3) |

159.0 kB against the 160 kB budget. 1.5 kB of the growth is the `lucide-copy`
mask data URI, and it lands in *both* sheets because the Tailwind content globs
are shared across entries — the chart island pays for an icon only the dashboard
renders. The budget in `build-islands.mjs` (un-owned here) should be re-pinned
from this build before the next entry grows.

### For ticket 23

The gallery's "import" becomes this call. `duplicate_dashboard` is dashboard-
scoped by design — a template is a workbook of several — so 23 needs either a
workbook-wide entry point beside it (same copy, closure per dashboard, one
workbook) or a per-dashboard gallery. The copy semantics above are the ones to
keep: `Private`, provenance kept, authority under the new owner.
