# Integration surface audit

Type: research
Status: resolved

## Question

What integration surface actually exists today, so the contract is designed
against reality, not recollection? Inventory:

**In Insights (`~/frappe/develop-bench/apps/insights`):**
- Public/guest sharing of charts and dashboards — what exists, how it works
  (routes, tokens, permissions).
- iframe embedding support — anything shipped or half-shipped.
- The workspace custom-block embed experiment (custom block + iframe, live-only)
  — where it lives, what state it's in.
- Whitelisted APIs a consumer app could call today to fetch/render a chart or
  dashboard.

**In framework (`~/frappe/develop-bench/apps/frappe`, plus upstream branches/PRs
if not in the local checkout):**
- The shadow-DOM "vue islands" POC for mounting frappe-ui components inside desk
  (avoiding bootstrap style conflicts) — where it is, what it can do, its
  limitations.
- The `framework/ui` package — state, contents, whether frappe-ui v2 charts are
  in or planned.
- The standard DuckDB sync feature — state, design, timeline signals.
- Desk `Dashboard` / `Dashboard Chart` doctypes — current rendering path and
  extension points.

Deliverable: findings file at
`docs/projects/framework-integration/research/integration-surface-audit.md`,
answer summarized here.

## Answer

Full findings: [research/integration-surface-audit.md](../../research/integration-surface-audit.md)

- Insights sharing is shipped and flag-based: `is_public` on chart/dashboard,
  `/shared/{chart,dashboard}/<name>` src2 routes, guest execution through
  `insights.api.get_doc`/`run_doc_method` with a hardcoded public-method
  allowlist. No tokens (only an internal preview-key header).
- iframe embedding = the share URL in an `<iframe>` snippet + CSP
  `frame-ancestors` from `Insights Settings.allowed_origins`. No embed SDK.
- The workspace custom-block embed has no code yet; what shipped is the
  link-out nudge bundle (`insights_nudge.bundle.js`). Templates hook +
  role-gated `@insights_whitelist` APIs are the only consumer-app surface; no
  purpose-built "get chart data" endpoint.
- Framework: vue-islands POC is real and complete but parked in open PR
  frappe/frappe#39773 (branch `frappe-ui-desk-poc`, June 2026). `@framework/ui`
  exists at `apps/frappe/ui` (shipped, active) but has zero charts — charts
  live in frappe-ui itself (echarts-backed AxisChart etc.).
- DuckDB sync is MERGED (frappe#40177, backported to v15/v16 hotfix):
  Report-driven full-table snapshots via MariaDB ATTACH, 7-day retention, not
  incremental, no permission handling in the sync job, no Dashboard Chart tie-in.
- Desk Dashboard/Dashboard Chart render via widgets → frappe-charts (not
  echarts); the pluggable seam is `Dashboard Chart Source` + the
  `frappe.dashboards.chart_sources` registry.
