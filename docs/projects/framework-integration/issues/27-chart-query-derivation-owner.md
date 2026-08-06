# 27 — Who derives a chart's query?

Type: grilling
Status: open
Blocked by: none

## Question

A chart's rows come from its **data query** — the source query plus the chart's
own summarize and order operations. Nothing derives that query on the server.
It is computed in `frontend/src2/charts/chart.ts` (`refresh()` →
`addSourceOperation` / `addFilterOperation` / `addChartOperation` /
`addOrderByOperation` → `dataQuery.setOperations`), persisted onto
`Insights Query v3`, and from then on the server reads it as if it were content.

So `data_query` is a cache of a client-side computation that the server depends
on. Every server-side consumer stands on it:

- `Insights Chart v3.get_data()` executes it;
- `insights.api.viewer.get_chart_data` — the only data path the desk island has
  — executes it and reads the date grain out of it (`column_granularity`);
- the shipping format carries it: `CARRIED_FIELDS[CHART]` names `data_query`,
  and `bundle_export` writes one `<chart>_data.json` per chart.

Nothing recomputes it. A chart whose config is right and whose cache was never
filled is a chart with no rows, and until now the server answered that with the
source query instead.

## Evidence

This is not hypothetical. Every chart in all four shipped bundles was exported
with `"operations": []` on its `*_data.json`, because the documents were flagged
standard and exported without ever having been opened in a builder session:

    erpnext_accounting: 11 charts | with ops: 0
    erpnext_purchasing:  7 charts | with ops: 0
    erpnext_sales:       8 charts | with ops: 0
    erpnext_stock:      10 charts | with ops: 0

`get_data_query()` then fell back to the chart's source query, so every desk
dashboard drew its raw source table and called it the chart: number cards read
`₹ 0`, donut legends listed `docstatus` and `idx`, the Quotation Funnel read
`NaN`. Standard documents are read-only outside developer mode, so no consuming
site could repair it. Two smaller symptoms of the same cause: the exported data
queries also carried `use_live_connection: 0`, because that flag is copied off
the source query client-side too (`chart.ts:94`), and it decides whether the
query runs against the source or the data store.

Both halves are fixed for now — the bundles were re-materialized from workbook
copies whose charts had been through a builder session, and `get_data_query()`
now throws instead of falling back. That makes the failure loud. It does not
remove the second truth.

## Options

1. **Derive on the server, delete the client derivation.** `chart.config` is the
   only input; the server produces the chart-shaped query. Cost: port ~200 lines
   of TypeScript covering seven chart types (axis with split-by → `pivot_wider`,
   number, donut, funnel in both measures and grouped mode, table with pivot,
   map, bubble) and keep the builder's preview responsive — today it derives and
   executes without a save round trip.
2. **Derive on the server at save time, keep the client derivation for preview.**
   Cheapest to write and the one shape this project rejects on principle: two
   derivations of the same fact, free to drift.
3. **Keep the client as the only deriver, make the invariant enforceable.** Export
   refuses a chart whose data query is empty; sync refuses such a file. Cheap,
   and it would have caught this defect at the source. It leaves `data_query` a
   client-side cache the server depends on, and leaves authoring by script or API
   unable to produce a working chart.
4. **Stop persisting it.** The server computes the chart-shaped query at
   execution time from `config`; the `data_query` link and its documents retire,
   and the shipping format loses one file per chart. The largest prize — one
   derivation, no cache, half the bundle files — and the largest question: what
   the builder's per-chart pipeline editing (which edits the data query as a
   query) becomes.

Options 1 and 4 are the same decision at different depths; 3 is a floor either
could ship behind first.

## Acceptance criteria

- [ ] A ratified owner for the derivation, with the builder's preview path stated
      (round trip, or client derivation as a pure display of a server contract)
- [ ] The fate of the `data_query` link and its documents named
- [ ] What the shipping format carries per chart, stated against ticket 24's
      workbook format
- [ ] A first step that is shippable on its own
