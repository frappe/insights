# Table experience — decision map

The grid and everything around it: find, filter, column actions, the result status, and the frame each editor builds by hand. This map records the shape, so no more header polish lands on the old one.

Tickets live in `issues/`, one body of work each. A ticket carries a `Type:`, a `Status:`, and any `Blocked by:` tickets.

Charted 2026-09-09 on `feat/charts-extract`, after a header-polish patch was set aside. The patch is at `docs/archive/datatable-header-polish.patch` (local-only) and none of it survives.

## Destination

One grid, three regions, and hosts pass capabilities instead of slots.

- **Table toolbar** holds table-scoped acts: Columns, find, filter chips, export. On a dashboard card it is the card's title row.
- **Column header** shows the label and state: sort arrow, filter dot, type icon in authoring. Click opens one menu, built from what the host allows.
- **Footer** is the result status: rows, fetched in / from cache, when. Pagination on the right.

Find and filter are two acts with two owners. **Find** is the table's, client-side over the loaded rows, always. **Filter** is the card's or the editor's, server-side through adhoc filters, always. Nothing switches between them on row count.

One picker under the dashboard filter bar, the card filter button, and the builder's Columns popover.

## Notes

- `frontend/src2/components/DataTable.vue` is mounted from ten places in three roles: authoring (`QueryBuilderTable`), preview (`ChartBuilderTable`, drill, data source, native and script editors) and reading (`TableChart` on a card).
- Adhoc filters are appended to the end of the operation list (`ibis_utils.py`, `set_operations`), so they apply after any summarize. A filter on a measure is a `HAVING`. A column not on the result cannot be filtered this way — that is the dashboard filter's job.
- The filter row today switches on row count in `QueryDataTable.vue` (`isSinglePage`): one page filters in memory, more pages builds `contains` adhoc filters and re-runs. On a card (`TableChart`) there is no server path at all. Same box, two meanings.
- The cache line ("Fetched from cache" / "Fetched in Ns") is written three times: `QueryExecutionStatus.vue` in the builder toolbar and below the native editor's toolbar, and by hand in `ScriptQueryEditor.vue`.
- The builder auto-executes (`autoExecute = true` in `QueryBuilder.vue`), so a stale result exists only in the native and script editors.
- `removeColumn` in `query.ts` takes an array and merges into the last `remove` operation.
- `ColumnFilterTypeText`, `ColumnFilterTypeNumber` and `ColumnFilterTypeDate` are the typed filter bodies the builder's column menu already uses.

- The prototypes live on `try/table-proto` and as untracked files under `frontend/src2/dev/`. Neither is merged, ever. Delete the branch and the files once tickets 01, 03, 05 and 06 have copied what they need.

## Decisions so far

- **Find is client-only, filter is server-only.** The row-count switch dies with the filter row. Find says what it covers ("in 100 loaded rows"). — 06
- **Filter lives on the card, not the table.** A per-chart filter is a dashboard filter scoped to one chart: same picker, same adhoc plumbing. — 02
- **Any column of the result is filterable.** Dimensions get a value picker, measures get number operators, dates get a range. Not author-defined: an author's list would still cost the reader a click to pick from it. — 02
- **The card filter button appears when the result has a dimension column.** No chart-type list. A measure-only result is one row and has nothing to narrow, so a number card gets no button by the rule, not by exception. — 02
- **Reader filter values reset on reload.** Component state into the adhoc dict, nothing stored. — 02
- **The `show_filter_row` chart config dies.** Find is always available and costs no space until used. — 06
- **One header menu.** The table's sort arrow and the host's three-dot menu merge. Prefix and suffix slots go, capabilities come in. — 04
- **Columns popover owns show, hide and jump.** Search, Enter jumps to the column, checkbox toggles it. Untick writes a `remove`; tick drops the column from the `remove`, never writes a `select`. — 05
- **Footer is the result status.** The cache line moves there, once. Alerts leave the footer for the editor's More menu. Export moves to the toolbar. — 03
- **Error replaces the grid body.** No banner above it. Error, "no data" and "no rows match your find" are one slot with three states. — 03
- **Page pane for the builder, card pane for a chart.** Two variants of one frame; a chart's header carries only Filter, search and expand. — 03
- **Toolbar is `[Filter][Columns][Execute][⋯][search]`, all outline; footer is ghost only.** Search sits at the edge because it grows. Export lives in the footer after the pager. — 03
- **Search finds rows and jumps to columns.** One input, a panel under it lists the column hits. — 03, 06
- **Stale is a solid Execute, not a footer button.** — 03
- **The picker has no operator control.** One complete picker per type, include/exclude for dimensions, from/to for measures, calendar with presets for dates. The rare operators sit behind a more menu. — 01
- **A preset emits a span, a calendar pick emits dates.** So the one picker serves a card filter that resets and a dashboard filter default that must move. — 01
- **Two frappe-ui changes come first:** export the calendar panel, and let a Popover open without taking focus. — 07
- **Out of this effort:** column drag to reorder, drag to resize, cell selection and copy, row expand.

## Fog

- Icon-only or icon+label for Filter, Columns and Execute in the builder toolbar. The prototype shows both under `?b=`; the ticket takes label until told otherwise. — 03

- Where the card's title row exposes a slot for the table toolbar, and whether `ChartContainer` in frappe-ui is the one to change. — 02
- Whether a preview grid (`ChartBuilderTable`, drill) gets the filter button, or filter is card-and-builder only. — 02
