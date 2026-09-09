# One pane around every grid

Type: task
Status: done

## Question

The builder, the native editor and the script editor each assemble the chrome around the grid by hand. The cache line is written three times. Alerts sit in the footer, export sits in the footer, the execution error is a banner that pushes the grid down.

## What to build

A result pane that the builder, native, script, drill and data source views all mount. Three bands:

1. **Table toolbar.** Columns (05), find (06), filter chips, export. Execute and the query's More menu stay in the editor's own toolbar above it.
2. **Grid.**
3. **Footer.** One status line: "100 of 4,210 rows · fetched in 1.2s · 2 min ago", or "from cache". "Running" while executing. In the native and script editors, which do not auto-execute, "edited since last run" with a Run action. Pagination on the right, as now.

Moves:

- `QueryExecutionStatus.vue` and the copy in `ScriptQueryEditor.vue` go. The footer says it.
- `QueryAlerts` leaves the footer for the editor's More menu.
- Export leaves the footer for the toolbar.

States: the grid body has one slot with three states. Execution error, no data, and no rows match your find, the last with a clear action. No banner above the grid.

Loading is one state: body dims, footer says running. The veil-versus-dim split goes.

## Looks like

Settled on the prototype at `frontend/src2/dev/FrameProto.vue` (branch `try/table-proto`), variant `page`, 2026-09-09. Copy it, do not reinterpret it.

- **Page variant**, for the builder, native, script and drill: one header row outside the bordered pane, `h-8`. Title left, inline-editable (`ContentEditable`, chart-card title type). Right, `gap-2`, all `outline`: `[Filter][Columns][Execute][⋯][search]`. Filter, Columns and Execute are icon+label. The menu is icon-only. Search is last because it grows: `w-40` at rest, `w-64` focused or non-empty, `transition-[width] duration-150`.
- **Search does both jobs.** Rows narrow live, and a panel under the input lists matching columns under a "Jump to column" header with a live "N rows match" line. Enter jumps: scroll the header cell into view and flash it for 600 ms. Escape clears and closes. The panel is a plain positioned box in Popover's look, because Popover steals focus on open. See 07.
- **Footer**, ghost buttons only. Left: "Showing 1–20 of N rows" with the Load Count control as today, then ` · fetched in 1.2s · 2 min ago` or ` · from cache`. Right: the pager, then Export as a ghost icon. Running replaces the time with an indicator and "Running…". Stale (native and script only) says "Edited since last run" and turns the toolbar's Execute `solid`. Error says "Failed · 2 min ago" with no pager.
- **Card variant**, for a table chart: header inside the border, `h-10 px-3 border-b`, plain title, ghost icons in `text-ink-gray-5` always visible: Filter with a count badge, search that expands in place to `w-48`, expand. No footer. When narrowed, one line under the header: "12 of 100 rows".
- **Paging is the pane's.** `DataTable`'s footer slot exposes no cursor, so the pane owns `usePagination`, slices the rows, and passes `current-page` down for the row gutter. A no-op `on-page-change` makes the table believe it is server-paged and Next never disables; do not pass one for client paging.
- Body states, one slot: error, no data, "No rows match “xyz”" with a subtle Clear.

## Amendment, 2026-09-09

The first build put the query's actions on a header row above the grid. That row mixed two owners, and in the SQL and script editors it put Execute and the data source below the code box. Replaced by two headers, and the pane is always card-shaped. This is what shipped:

- **Page header**, at the top of every query page (`QueryHeader.vue`): one `h-7` row. Left, the title, inline-editable, `font-medium`, prefixed with the query's own sidebar icon — no meta line. Right, whatever the editor puts there: the data source selector (SQL), Execute (`solid` while stale) and the menu, all in `QueryActions.vue`.
- **Pane header**, inside the border, `h-10`. It holds the find, and the host's own `#header-left` and `#actions`. An editor with a page header of its own takes the find instead: it passes a `findTarget` element and the pane teleports the find into it, so the builder, the native and the script editors show it beside Execute. Nothing else lives here yet — the result actions (Columns, 05) are unbuilt.
- **Footer**: the status line on the left (`ResultStatus.vue` — rows, timing, from cache, running, stale, failed, find count), the pager and Export on the right. The bar is hidden only when it would be empty.
- **Body**, one slot: the grid, or one of four states — error, loading (a first run, with no columns yet), "no rows match", no data. A run that already has columns dims the body instead of replacing it.

The "page variant" in *Looks like* above is superseded by this, and so is its footer: the status line reads in the footer, not the pane header. The prototype's `card` variant is the shape of the pane everywhere.

## Amendment, 2026-09-09

The chart builder mounts the pane under the card, and drops the toolbar it drew above it. The card's own header is the page header: the title frappe-ui's `ChartContainer` already draws, with Refresh and the chart menu in its `actions` slot, passed down from the builder through `ChartRenderer` and `ChartCardFrame`.

There is no page header row on the chart page. The title already lives in the card, and a page header would draw it twice. The source query is not in a header either — it is a config field, not an act.
