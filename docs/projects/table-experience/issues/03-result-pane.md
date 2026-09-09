# One frame around every grid

Type: task
Status: ready-for-agent

## Question

The builder, the native editor and the script editor each assemble the frame around the grid by hand. The cache line is written three times. Alerts sit in the footer, export sits in the footer, the execution error is a banner that pushes the grid down.

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
