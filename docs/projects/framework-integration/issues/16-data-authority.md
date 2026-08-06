# 16 — Data authority

Type: task
Status: resolved
Blocked by: none — can start immediately
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Data authority"

## What to build

An author declares whose permissions filter a chart's rows.
`data_authority: Viewer | Author`, default `Viewer`, on `Insights Chart v3`.
The engine enforces it at execution: the request names the chart, the doc
names the authority, and no parameter on the wire can flip it. The surface —
Insights app, desk island, public link — is irrelevant.

Viewer mode is the engine's existing native permission application. Author
mode applies the author's permission context at execution without switching
the session user (never `frappe.set_user` in a request). Author mode is the
deliberate escalation for whole-number content, the only meaningful mode on
the `Public` rung, and the defined mode for non-site-DB sources.

The authoring UI makes a wide audience (`Public | Everyone`) combined with
`Author` a loud explicit confirmation. The copy states that viewers can see
the underlying rows.

## Acceptance criteria

- [x] `Insights Chart v3` carries `data_authority`, default `Viewer`,
      declared in the authoring UI
- [x] Under `Viewer`, two users with different row access get different rows
      from the same chart
- [x] Under `Author`, a viewer gets the author's rows without the session
      user changing
- [x] No request parameter can override the declared authority — a test
      proves the wire cannot flip it
- [x] The wide-audience + `Author` combination requires the loud
      confirmation in the UI

## Comments

2026-08-05 — done. `insights/insights/doctype/insights_data_source_v3/data_authority.py`
is the seam: `get_authority_user_for` reads `data_authority` and `owner`
straight from the database by doctype/name, never from the in-memory document
`run_doc_method` builds off the request, so no wire parameter reaches it.
`InsightsChartv3.get_data` re-reads the stored chart and runs the query inside
`data_authority_of(chart)`, which sets `frappe.local.insights_authority_user`
for `InsightsTablev3.get_ibis_table` to apply instead of the session user —
`frappe.set_user` is never called. `insights/tests/test_data_authority.py`
covers both rungs and the wire-override case. `0aef7b78` adds the
`data_authority` control to `ChartShareDialog.vue` with the loud confirmation
on `Public`/`Everyone` + `Author`.
