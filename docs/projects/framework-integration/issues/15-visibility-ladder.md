# 15 — Visibility ladder

Type: task
Status: ready-for-agent
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

- [ ] Both doctypes carry `visibility` and `visible_to_roles`, declared
      through the share dialog
- [ ] Matrix tests pass: each rung × chart/dashboard × member, non-member,
      and guest, through `frappe.has_permission`
- [ ] A chart inherits its dashboard's audience, downward only; a standalone
      chart uses its own declaration
- [ ] A guest reads `Public` content and nothing below it, decided inside
      the controller
- [ ] The `is_public` migration lands and the shared pages keep working
- [ ] No viewing path consults the `Insights User` role
