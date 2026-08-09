# 26 — The viewer seat: an Insights Viewer role?

Type: grilling
Status: resolved
Blocked by: none — decide before the permission controller grows further

## Question

Should Insights have a viewer seat — a role (working name `Insights Viewer`)
for people who consume dashboards but never author — or does "viewing implies
no Insights access" ([09](09-desk-data-access.md)) stay the whole answer?

The tension the branch surfaced: two different questions are answered by one
mechanism today.

- *Seat*: does this person have any business in the Insights app? Answered by
  `check_app_permission()` — Insights User / Insights Admin, all-or-nothing.
  There is nothing below "author".
- *Audience*: may this person see this dashboard? Answered by the visibility
  ladder, per document.

Because there is no seat below author, the ladder carries both jobs. The
enforcement code is deliberate about the conflation — the viewing path never
consults `Insights User` (ticket 15's rule), and the viewer endpoints are
`allow_guest` with the ladder as the only gate. It works, but the shape shows:

- `can_edit` in `api/viewer.py` is rights-on-the-doc AND
  `check_app_permission()` — the seam where seat and audience meet is
  hand-assembled per endpoint.
- The `Everyone` rung means "anyone signed in to this *site*", because there
  is no way to say "anyone with a viewing seat in Insights". A site that wants
  role-scoped viewing must set `Specific Roles` per document, naming desk
  roles Insights doesn't own.
- The SPA's own dashboard/shared pages still gate on `Insights User` via
  resources, which is why viewing had to move to new endpoints instead of the
  ladder simply applying to the existing ones.

What this ticket decides:

- Whether the seat ladder becomes `Admin | User (author) | Viewer | none`,
  what a Viewer reaches in the SPA (dashboard list and viewer surfaces, no
  workbooks, no data-source exploration), and what the role means for
  `check_app_permission`'s call sites.
- Whether `visible_to_roles` stays the per-document mechanism or the Viewer
  seat absorbs the common case ("everyone we gave a seat"), leaving
  `Specific Roles` for finer grants.
- Deciding *no* is a valid outcome — but then the ladder is ratified as the
  permanent owner of both questions, and the map's parked unified-permission
  effort inherits that.

Not in scope: implementing the role. This ticket fixes the model so the
controller stops growing grant sources against an unstated one.

Inputs: the desk-report pattern (role-gated reports, the `Specific Roles`
prior art), and the map's parked unified permission-rule store — whose first
recorded requirement (role-based edit grants) is the same missing primitive
on the write side.

## Answer

**No Viewer seat. The two-mechanism model is ratified as permanent: the seat
means authoring, the ladder owns all viewing, on every surface.**

- The host platform has no viewer-seat primitive — desk content is gated by
  roles on the content, never by an app seat — and ticket 09 already bent
  Insights to that shape ("viewing implies no Insights access"). A Viewer role
  would have nowhere to act: outside the viewing path it gates nothing and
  misleads whoever assigns it; inside it, it contradicts 09 and breaks the
  islands, which mount for users holding no Insights role at all.
- **The `Everyone` rung relationship**: `Everyone` means anyone signed in to
  the site — deliberately, because that is what it means on desk (a report
  with no role restriction behaves identically). A site that wants a narrower
  audience names a role in `Specific Roles`; sites mint roles, Insights does
  not own audiences. The missing "everyone we gave a seat" rung is a
  site-defined role, not an Insights primitive.
- **`check_app_permission()`'s contract, restated**: it is the authoring gate
  — it answers "may this person enter the builder SPA", and is never consulted
  for viewing. `can_edit` = write-rights-on-doc AND seat is the correct model,
  not debt (editing is both a rights question and a seat question); the
  reshape names it once in a helper instead of assembling it per endpoint.
- What a Viewer seat would actually buy — an SPA surface for pure consumers,
  a convenient default audience — belongs to the parked workbook/SPA effort
  and is reachable later without a seat (a ladder-driven "what admits me"
  list; an ordinary shipped role).

**The grant-source table is the named model.** The controller's branching is
three eras layered (teams, workbook sharing, the ladder), but the model
beneath is one rule: a grant is a union of enumerable sources per (doctype,
action):

| Source | Applies to | Actions |
|---|---|---|
| Ownership | everything | all |
| DocShare | workbook, dashboard, chart | per share flags |
| Container inheritance | workbook→items, dashboard→chart, chart→query | follows container |
| Team resource grant | source, table — *and* dashboard, chart (legacy) | all |
| Audience ladder | dashboard, chart | read only |
| Seat (`check_app_permission`) | the authoring SPA, not documents | — |

This table becomes the controller's module docstring when the branch
reshapes. A new grant source must earn a row, not a join.

**Recorded for the parked unified-permission-store effort** (inputs, not
decisions): the table above is its starting spec on the read side, and *team
resource grants on content doctypes are a retirement candidate* — teams
should govern data objects (sources, tables) only, returning content to
ownership/sharing/inheritance/audience. That is a permission change on live
sites, so it is that effort's call.

## Acceptance criteria

- [x] A ratified seat model: Viewer exists (with its SPA reach stated) or is
      rejected with the ladder named as permanent owner of both questions
- [x] The relationship between the seat and the ladder's `Everyone` rung
      stated
- [x] `check_app_permission()`'s contract restated against the decision
