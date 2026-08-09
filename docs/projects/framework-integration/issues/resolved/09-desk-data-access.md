# Data access for desk-rendered content

Type: grilling
Status: resolved

## Question

Every `@insights_whitelist` endpoint requires the `Insights User` role (ticket
01). An ordinary desk user viewing an embedded chart in a workspace or a
dashboard page has no such role, so the data path needs a story that does not
assume one.

- What does a desk user need to view an embedded chart — a role, a permission
  on the chart document, or nothing beyond access to the page?
- How is the already-decided author-mode vs viewer-mode choice declared on
  content, and enforced when the request arrives from a desk page rather than
  the Insights app?
- Does viewing embedded content imply any access to Insights itself (opening
  the workbook, drilling into the underlying query)?
- What does drill-down expose — the chart's rows only, or the query behind it?

Constraint: the answer must not require site admins to grant `Insights User`
broadly, since that would widen access to the Insights app as a side effect of
embedding a chart.

## Answer

**The model is three axes, and every grant source belongs to exactly one.**
*Authoring* — who can build in Insights, and with which data (`Insights User`
role, teams, workbook shares — unchanged by this ticket). *Visibility* — who
can see a given chart or dashboard, on any surface. *Data authority* — whose
permissions filter the rows. This ticket fixes the semantics only. The storage
behind them is deliberately open: a unified `subject × object × action`
permission-rule store is a separate future effort, and its first recorded
requirement is role-based *edit* grants, which this ticket defers. Because
enforcement sits behind one seam (below), the store can land later without a
contract change.

**The gate is a visibility ladder declared on the content.** Two fields on
`Insights Chart v3` and `Insights Dashboard v3`:
`visibility: Private | Specific Roles | Everyone | Public` plus a
`visible_to_roles` child table (the shared `Has Role` child doctype, the desk
Report convention). The ladder is strict — each rung includes the previous:

- **Private** (default) — owner plus person-level DocShares. DocShare is
  re-scoped as the person rung of this axis, not a parallel mechanism.
- **Specific Roles** — the desk-report pattern, for AR/AP-class content.
- **Everyone** — any logged-in user, the natural rung for workspace content.
- **Public** — absorbs `is_public`, which dies as a separate flag. Guest
  access moves inside the permission controller, out of the API allowlist.

The ladder is view-only — editing stays on the authoring axis. A chart
rendered inside a dashboard inherits the dashboard's audience (cascade kept,
downward only). A chart embedded standalone uses its own declaration. Fields
live on the doc, not in a side table, so the declaration travels through
template export and `workbook.json` with no extra stitching, and cannot
orphan. No teams rung: roles are Frappe's native group primitive, and richer
groups arrive with the future store.

**Enforcement is one seam: `frappe.has_permission`.** Data endpoints for
embedded consumption are plain `frappe.whitelist()` — no `check_role`. Each
one checks read permission on the referenced content doc, and the
`InsightsPermissions` controller answers, with the ladder as one grant source
inside it alongside the existing ones. Nothing outside the controller ever
reads the ladder directly. The ticket's constraint holds by construction: the
`Insights User` role appears nowhere in the viewing path, so a desk user
needs nothing beyond membership in the content's declared audience.

**Data authority is the second field: `data_authority: Viewer | Author`,
default `Viewer`.** Doc-declared and engine-enforced at execution — the
request names the chart, the doc names the authority, and no parameter on the
wire can flip it, so the surface (Insights app, desk island, public link) is
irrelevant. Viewer mode is the engine's native permission application, safe
under any audience. Author mode is the deliberate escalation for whole-number
content: the company-wide KPI shown to people who cannot read the rows —
without it, the only fix is granting broad read on the underlying doctypes,
the exact failure this ticket forbids at the data layer. Author mode is also
the only meaningful mode on the `Public` rung (guests have no permissions to
apply) and for non-site-DB sources (external databases and uploads have no
Frappe permissions to filter by — viewer mode is defined over site-DB-backed
data). The authoring UI makes `Public | Everyone` + `Author` a loud, explicit
confirmation, and the copy states that viewers can see the underlying rows.

**Viewing implies no access to Insights.** Audience membership grants exactly
one capability: rendering that content where a surface hosts it. No role, no
app access, no catalog of other visible content. The "open in Insights"
affordance renders only for users who independently pass
`check_app_permission`. Accepted asymmetry: an `Everyone` dashboard is
viewable on desk by a non-Insights user but not at `/insights` — desk is the
viewing surface, the app is for authors. A lean viewer route in Insights
would be additive later.

**Drill-down exposes the chart's own query results, nothing more.** It
re-executes the chart's underlying query with the clicked segment's filters,
under the chart's `data_authority`, bounded by that query's result columns —
never the source tables, never other queries, never the query definition
(operations JSON and SQL are authoring-surface artifacts). The unit the
author publishes is the chart *including its query's result surface*, so the
author's control over row exposure is the query itself: select only what you
would publish. An aggregate-only mode (a per-content drill-down toggle) is a
possible later refinement, deliberately left out of v1 to keep one rule.

Terms `Visibility` and `Data Authority` are recorded in `CONTEXT.md`.
