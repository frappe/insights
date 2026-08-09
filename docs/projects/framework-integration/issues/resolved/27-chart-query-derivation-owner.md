# 27 — Who derives a chart's query?

Type: grilling
Status: resolved
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

- [x] A ratified owner for the derivation, with the builder's preview path stated
      (round trip, or client derivation as a pure display of a server contract)
- [x] The fate of the `data_query` link and its documents named
- [x] What the shipping format carries per chart, stated against ticket 24's
      workbook format
- [x] A first step that is shippable on its own

## Answer

Ratified 2026-08-06 (grilling, together with ticket 31).

**Option 4. The server derives a chart's query from `config` at execution
time. Nothing is persisted.** Option 1 was rejected as a waypoint: once the
server can derive, persisting the result buys nothing except a staleness bug
class. Option 3 survives only as the loud throw already shipped.

**The preview path.** A finding dissolved the cost the ticket feared: the
builder's preview already round-trips on every config change — the client only
derives operations JSON, execution was always a server call. Moving derivation
server-side moves computation to the other end of a call that already happens.
Preview latency is unchanged to first order.

The contract is one endpoint family: a saved chart name, or inline unsaved
config plus the source query reference, in; rows plus the **derived
operations** out. The client keeps zero derivation. The two remaining client
dependents re-home onto the response: the SQL display renders what the server
sent, and drill-down (`query/query.ts` `getDrillDownQuery`) forks the
server-sent operations instead of client-derived ones. The derived operations
cross the wire only on the authoring endpoint — the viewer contract still
never ships operations (drill-down on read surfaces stays ticket 11's
business).

A correction to this ticket's own text, found while grilling: the builder's
"pipeline editing" does not edit the data query as a query. Sort and
granularity in `ChartBuilderTable.vue` write to `chart.doc.config` and the
derivation re-runs. There is no user-facing pipeline surface to preserve.

**The artifact retires completely** — five cuts, one refactor, no transitional
field:

1. `Insights Chart v3.data_query` dropped; `set_data_query`/`get_data_query`
   deleted; `get_data()` calls the deriver on `config`.
2. A patch deletes every `Insights Query v3` document a chart's `data_query`
   references — pure caches, chart-owned, referenced nowhere else.
3. `permissions.py` loses its data-query rows (a grant source dying — its row
   leaves the table, per ticket 26's rule).
4. The shipped format: a chart ships one file; `<chart>_data.json` dies and
   sync stops reading it. No compatibility read — this lands before the
   format freezes, same rule as `bundle.json` → `workbook.json` (ticket 24).
5. `duplicate.py` and export drop their data-query handling.

**The route**, each step shippable on its own:

1. **Port the deriver, prove it by parity.** Python derivation (config →
   operations JSON, seven chart types) plus a test that runs it against every
   chart whose cache is populated — the four shipped workbooks and dev-site
   content — and diffs derived against stored operations. The caches become
   the port's fixture set before they die.
2. **Switch the read paths.** `get_data()` and `viewer.get_chart_data` derive
   instead of reading the cache. The client still writes it; nothing reads it.
3. **Preview endpoint, delete the client derivation.** `chart.ts` loses
   `addSourceOperation` and friends; SQL display and drill-down consume
   server-sent operations. This is where ticket 31's data layer becomes real.
4. **Retire the artifact** — the five cuts and the deletion patch.
