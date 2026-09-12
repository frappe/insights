# Columns: search, jump, show and hide

Type: task
Status: ready-for-agent
Blocked by: 03

## Question

Removing a column in the builder is three clicks, one column at a time. Selecting is a dialog in the operations panel. There is no way to jump to a column in a wide result.

## What to build

A Columns button in the table toolbar (03). It opens the filter picker's column list over the result columns, each row with a checkbox.

- Type to narrow. Enter on a row scrolls the grid to that column and flashes its header. The new-column path in `DataTable.vue` already scrolls with `scrollIntoView`; reuse it.
- Untick calls `removeColumn`, which merges into the last `remove` operation. Ten unticks in one visit are one operation.
- Tick drops the column from that `remove`. It never writes a `select`. A `select` stays the way to order and rename.
- A keyboard shortcut opens the popover, so jump is shortcut, type, Enter.

The header menu (04) keeps Remove for the single case. One action, two places.

## Looks like

Settled on `frontend/src2/dev/ProtoColumns.vue` (branch `try/table-proto`), 2026-09-09.

- frappe-ui Popover, `w-72`. Search input on top. One row per result column: Checkbox, type icon, label. Footer row: "N of M shown" left, "Show all" ghost xs right when any are hidden. The trigger shows a hidden-count badge.
- Clicking the checkbox toggles. Clicking the rest of the row, or Enter, jumps to the column with the same scroll and flash as search. A jump to a hidden column shows it first.
- Space stays a typed character in the search box. Toggle only on the checkbox. The prototype bound Space to toggle, which blocks labels with spaces; do not copy that.
