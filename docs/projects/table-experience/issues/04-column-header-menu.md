# One column header menu

Type: task
Status: ready-for-agent

## Question

In the builder a column has two sort controls: the table's arrow in `DataTableColumn.vue` and the host's three-dot menu in `QueryBuilderTable.vue`. The header takes a `prefix` and a `suffix` slot, so each host fills them differently.

## What to build

The header shows the label and state only: sort arrow, filter dot, type icon when the host allows type change. Click the header to open one menu. The table builds it from capabilities the host passes:

- sort: asc, desc, remove
- filter: opens the picker's condition body (01) for this column
- rename
- type
- granularity, for a date column
- pin
- wrap
- remove

Hosts pass callbacks, not slot content. `ChartBuilderTable`'s calendar dropdown becomes the granularity capability. The `header-prefix` and `header-suffix` slots go from `DataTable.vue`, `QueryDataTable.vue` and both hosts.

Sort state is drawn always. A control is not: the menu is the control.
