# 15 — Visibility ladder

Type: task
Status: resolved
Blocked by: none — can start immediately
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Visibility ladder"

## What to build

An author declares who may view a chart or dashboard, and every surface
honors it. Two fields on `Insights Chart v3` and `Insights Dashboard v3`:
`visibility: Private | Specific Roles | Everyone | Public` (default
`Private`) plus a `visible_to_roles` child table using the shared `Has Role`
child doctype. The share dialog in the builder declares the ladder.

The ladder is strict — each rung includes the previous. `Private` is owner
plus person-level DocShares. `Specific Roles` is the desk-report pattern.
`Everyone` is any logged-in user. `Public` absorbs `is_public`, which dies as
a separate flag with a migration patch. Guest access moves inside the
permission controller. The public shared pages keep working, gated by the
ladder.

Enforcement is one seam: the ladder becomes one grant source inside the
`InsightsPermissions` controller, beside the existing ones. Nothing outside
the controller reads the ladder. A chart on a dashboard inherits the
dashboard's audience through the existing linked-dashboard grant. The
`Insights User` role appears nowhere in the viewing path. The ladder is
view-only — editing stays on the authoring axis, unchanged.

## Acceptance criteria

- [x] Both doctypes carry `visibility` and `visible_to_roles`, declared
      through the share dialog
- [x] Matrix tests pass: each rung × chart/dashboard × member, non-member,
      and guest, through `frappe.has_permission`
- [x] A chart inherits its dashboard's audience, downward only; a standalone
      chart uses its own declaration
- [x] A guest reads `Public` content and nothing below it, decided inside
      the controller
- [x] The `is_public` migration lands and the shared pages keep working
- [x] No viewing path consults the `Insights User` role

## Comments

2026-08-05 — built. The ladder is one grant source in `InsightsPermissions`
(`_build_audience_query`, folded into the chart and dashboard grant queries by
`_with_audience_grant`), so `has_doc_permission` and
`get_permission_query_conditions` answer from the same shape. It returns
nothing unless `ptype` is `read`, so the ladder never grants write or share.
Guests are cut to the `Public` rung inside the query. The chart cascade needed
no work: the existing linked-dashboard grant now carries the dashboard's
audience, and there is no reverse join, so it stays downward only.

`is_public` keeps its value and its readers. The patch
(`insights.patches.set_visibility_from_is_public`) only moves public content
onto the `Public` rung; the field retirement and the shared-page guest checks
complete with ticket 23. The share dialogs write `is_public` (and, for
dashboards, the organization DocShare) as mirrors of the top two rungs so the
existing shared pages keep working meanwhile.

2026-08-07 — `is_public` retired. It read as a second access system beside the
ladder, so `insights/api/shared.py` is gone whole: the `is_public` walk, the
`check_public_access` helper, the duplicate preview-key check, and both
`get_*_name` endpoints. The `old_name` lookup those two carried moved into
`resolver.resolve` as a fourth reference form, which is where every other form
already lives — the three route components now hand their raw reference to the
viewer. `insights.api.get_doc` and `run_doc_method` lose the public fallback and
`allow_guest`; nothing guest-facing called them, since ticket 17's endpoints are
what the shared pages read through. `frappe.flags.insights_for_public_access`
went with the fallback that set it, and so did its three readers in
`insights_table_v3` and `insights_team`. The share dialogs stop mirroring the
top rung, and the field keeps its value with nothing reading it.

One gap is outside this ticket's files. Frappe's controller hooks can only
deny — "Controllers can only deny permission, they can not explicitly grant any
permission that wasn't already present" (`frappe/permissions.py`). Both content
doctypes only grant `read` to `Insights User` and `Insights Admin`, so a desk
user with no Insights role never reaches the controller and
`frappe.has_permission` answers `False` before the ladder is consulted. For
ticket 17's endpoints to work, `Insights Chart v3` and `Insights Dashboard v3`
need `read`-only permission rows for `All` and `Guest` in their doctype JSON,
with the controller and the query conditions narrowing them — which they now
do, per rung. Note the side effect: doctype-level `read` becomes true for
everyone, which flips the chart and dashboard rows of
`test_permissions_for_non_insights_user`; list results stay correct because
`get_permission_query_conditions` returns only audience-admitted docs.
