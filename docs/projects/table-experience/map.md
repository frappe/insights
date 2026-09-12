# Table experience — decision map

The grid and everything around it: find, filter, column actions, the result status, and the chrome each editor builds by hand. This map records the shape, so no more header polish lands on the old one.

Tickets live in `issues/`, one body of work each; 01 and 02 closed into an ADR. A ticket carries a `Type:`, a `Status:`, and any `Blocked by:` tickets.

Written 2026-09-09 on `feat/charts-extract`, after a header-polish patch was set aside. The patch is at `docs/archive/datatable-header-polish.patch` (local-only) and none of it survives.

## Destination

One grid, three regions, and hosts pass capabilities instead of slots.

- **Table toolbar** holds table-scoped acts: Columns, find, filter chips, export. On a dashboard card it is the card's title row.
- **Column header** shows the label and state: sort arrow, filter dot, type icon in authoring. Click opens one menu, built from what the host allows.
- **Footer** is the result status: rows, fetched in / from cache, when. Pagination on the right.

Find and filter are two acts with two owners. **Find** is the table's, client-side over the loaded rows, always. **Filter** is the host's, server-side through adhoc filters, drill included, always. Nothing switches between them on row count.

One picker under four hosts: the table chart card, the drill rows, the dashboard filter bar, and the builder's column-header filter.

## Notes

- `frontend/src2/components/DataTable.vue` is mounted from ten places in three roles: authoring (`QueryBuilderTable`), preview (`ChartBuilderTable`, drill, data source, native and script editors) and reading (`TableChart` on a card).
- Adhoc filters are appended to the end of the operation list (`ibis_utils.py`, `set_operations`), so they apply after any summarize. A filter on a measure is a `HAVING`. A column not on the result cannot be filtered this way — that is the dashboard filter's job.
- The filter row today switches on row count in `QueryDataTable.vue` (`isSinglePage`): one page filters in memory, more pages builds `contains` adhoc filters and re-runs. On a card (`TableChart`) there is no server path at all. Same box, two meanings.
- The cache line ("Fetched from cache" / "Fetched in Ns") is written three times: `QueryExecutionStatus.vue` in the builder toolbar and below the native editor's toolbar, and by hand in `ScriptQueryEditor.vue`.
- The builder auto-executes (`autoExecute = true` in `QueryBuilder.vue`), so a stale result exists only in the native and script editors.
- `removeColumn` in `query.ts` takes an array and merges into the last `remove` operation.
- `ColumnFilterTypeText`, `ColumnFilterTypeNumber` and `ColumnFilterTypeDate` are the typed filter bodies the builder's column menu already uses.

- `try/table-proto` still exists and is still to be deleted once tickets 03, 05 and 06 have copied what they need.

## Decisions so far

- **The filter picker is settled**: see [one filter picker, as a palette](../../adr/one-filter-picker-as-a-palette.md). Tickets 01 and 02 closed into it; the builder's column filter still wires it.
- **Find is client-only, filter is server-only.** The row-count switch dies with the filter row. Find says what it covers ("in 100 loaded rows"). — 06
- **The `show_filter_row` chart config dies.** Find is always available and costs no space until used. — 06
- **One header menu.** The table's sort arrow and the host's three-dot menu merge. Prefix and suffix slots go, capabilities come in. — 04
- **Columns popover owns show, hide and jump.** Search, Enter jumps to the column, checkbox toggles it. Untick writes a `remove`; tick drops the column from the `remove`, never writes a `select`. — 05
- **Footer is the result status.** The cache line moves there, once. Alerts leave the footer for the editor's More menu. Export stays in the footer, ghost only. — 03
- **Error replaces the grid body.** No banner above it. Error, loading, "no data" and "no rows match your find" are one slot with four states. — 03
- **One card-shaped pane everywhere, under a page header.** The query's actions (source, Execute, menu) sit in a page header with the title. Superseded the page/card split after the first build put Execute below the SQL editor. — 03
- **The status line reads in the footer, left of the pager.** The pane header holds the find and whatever the host puts beside it; an editor with a page header of its own takes the find into that header instead. Footer right is the pager and Export, ghost only. — 03
- **Search finds rows and jumps to columns.** One input, a panel under it lists the column hits. — 03, 06
- **Stale is a solid Execute in the page header, not a footer button.** — 03
- **The header sits on the object the acts belong to.** A query has no card, so its header is a page row. A chart's header is its card's. — 03
- **Two frappe-ui changes come first:** export the calendar panel, and let a Popover open without taking focus. — 07
- **Out of this effort:** column drag to reorder, drag to resize, cell selection and copy, row expand, cross-filter (clicking a chart element to apply a dashboard filter).

## Fog

- Icon-only or icon+label for Filter, Columns and Execute in the builder toolbar. The prototype shows both under `?b=`; the ticket takes label until told otherwise. — 03

