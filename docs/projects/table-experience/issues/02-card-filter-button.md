# A filter button on every card with a dimension

Type: task
Status: ready-for-agent
Blocked by: 01

## Question

A reader of "revenue by category" wants to see three categories, or only rows with count over 5. Today they cannot, unless the author added a dashboard filter for it.

## What to build

A button in the card's title row, next to expand. It opens the picker (01) over the chart's result columns. Each applied rule shows as a chip under the title. Click a chip to edit, its cross to remove.

- The button renders when the result has at least one dimension column. No chart-type check.
- Rules go into the same per-query adhoc dict that dashboard filters and drill use (`query.adhocFilters`, `adhoc_filters` on the server). They compose with the dashboard's filters with `And`.
- Values live in the card's component state. Reload clears them.
- Adhoc filters apply after summarize (`ibis_utils.py`), so a measure rule is a `HAVING`. That is what the reader expects on a chart.

## Open

- Where the title row exposes the slot. `ChartContainer` is frappe-ui's, so this may be a frappe-ui change first.
- Preview grids: `ChartBuilderTable` and the drill. Same button, or card only. Card only is the safe first cut.
