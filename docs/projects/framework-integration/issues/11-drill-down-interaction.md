# Drill-down interaction

Type: grilling
Status: open

## Question

The drill ladder: chart segment → break down by another dimension (ad-hoc
chart) → underlying rows → open the desk record. Design it as one common
layer that serves both surfaces — Insights' own dashboard viewer and the
desk dashboard page — not a desk-only bolt-on.

- Interaction shape: everything-in-dialog was the v1 sketch from the
  [desk dashboard page UX](05-desk-dashboard-page-ux.md) ticket; validate or
  revise. Back-stack feel, dimension-picker scope (chart's declared
  dimensions first, searchable full list behind).
- Row → record mapping: how does a result row know which doctype/document
  it opens? Source-table queries map cleanly; joined/aggregated rows don't.
  This is a contract/engine question, not a UI one. Known constraint:
  chart → record does not work today.
- What the drill runs under: the chart's `data_authority`, rows only, never
  the query definition (per [desk data access](09-desk-data-access.md)).

Can run in parallel with foundation implementation. Use /grilling, then
/prototype the dialog with a mocked engine if feel is still in question.
