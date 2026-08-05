# 16 — Data authority

Type: task
Status: ready-for-agent
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

- [ ] `Insights Chart v3` carries `data_authority`, default `Viewer`,
      declared in the authoring UI
- [ ] Under `Viewer`, two users with different row access get different rows
      from the same chart
- [ ] Under `Author`, a viewer gets the author's rows without the session
      user changing
- [ ] No request parameter can override the declared authority — a test
      proves the wire cannot flip it
- [ ] The wide-audience + `Author` combination requires the loud
      confirmation in the UI
