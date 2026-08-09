# Chart gallery

One workbook that holds one chart of every type, and a dashboard that lays them
out. A human opens the dashboard to review how charts look. This is the review
surface named in `spec-charts-v2.md`, where each stage of the render swap ends
with a browser check.

The gallery outlives the swap. When the swap ends it is the fixture a smoke test
runs against, because it already gives one dashboard with one card per chart
type.

Fixture: `chart-gallery.workbook.json`.

## What it covers

Every card is configured to exercise its type, not to merely exist. Each one
returns rows.

| Card | Type | What it exercises |
| --- | --- | --- |
| Revenue by month, stacked by department | Bar | Split by a dimension, stacked bars, `pivot_wider` derivation |
| Traffic source mix by department (100%) | Bar | `normalize`, so bars fill to 100 percent |
| Revenue and profit trend | Line | A time series with two measures, smoothing, area fill |
| Revenue bars with item count on the right axis | Bar | Combo (one bar series, one line series), dual axis (`align: Right`), and a reference line |
| Revenue by category | Row | Horizontal bars over 26 categories, sorted by the config's `order_by` |
| Revenue share by category | Donut | `max_slices` collapses 26 categories into 8 and a tail |
| Order lifecycle (measures mode) | Funnel | Measures mode. Four stages on one row, three of them expression measures |
| Items by order status (grouped mode) | Funnel | Grouped mode. One row per stage |
| Headline numbers | Number | Three values with per-column prefix and shortening |
| Revenue vs previous month | Number | `comparison` against a date column |
| Items sold with sparkline | Number | `sparkline` over a date column |
| Revenue by category and department | Table | A pivot, row totals, column totals, and conditional formatting |
| Revenue by country | Map | The world map with region mappings |
| Category revenue vs profit | Bubble | Two measures, a size column, and quadrant reference lines |
| Traffic source to category revenue | Sankey | A source, a target, a value, and a chart-level filter |

Both funnel shapes are present because the config admits both, and the spec
keeps both.

## The data

The gallery reads the `ecommerce` data source, a local DuckDB copy of the
TheLook sample dataset. One query feeds every chart.

**Sales facts** joins `order_items` to `products` and to `users`, then adds a
`profit` column. That gives a date column, four categorical dimensions
(`category`, `department`, `traffic_source`, `status`), a country column, and
two numeric measures on 180,952 rows.

The query sets `use_live_connection`. `order_items` and `products` are not in
the Data Store on this site, so the query must reach the source.

The country column needs two region mappings. The geojson names the two largest
countries `United States of America` and `Brazil`, and the data says
`United States` and `Brasil`. Without the mappings the map loses 37 percent of
its revenue and says nothing about it.

## Import it

Run from the bench root. The site needs the `ecommerce` data source.

```bash
bench --site insights.localhost console <<'PY'
import os, json
from insights.insights.doctype.insights_workbook.insights_workbook import import_workbook
path = os.path.join(
    os.path.dirname(frappe.get_app_path("insights")),
    "docs/projects/framework-integration/chart-gallery.workbook.json",
)
print("workbook:", import_workbook(json.load(open(path))))
frappe.db.commit()
PY
```

The command prints the new workbook's name. Open the dashboard at
`/insights/workbook/<workbook>/dashboard/<dashboard>`.

Do not build the path with `frappe.get_app_path("insights", "docs", ...)`. That
helper scrubs each segment, so it turns `framework-integration` into
`framework_integration` and the file is not found.

Importing again adds a second copy. The fixture carries logical names, and the
importer maps them onto fresh ones every time.

## Check it

This runs every chart through the same code path the app uses and reports the
row count of each.

```bash
bench --site insights.localhost console <<'PY'
from insights.insights.doctype.insights_chart_v3.chart_query import config_errors
wb = frappe.get_all("Insights Workbook", {"title": "Chart Gallery"}, pluck="name")[-1]
charts = frappe.get_all("Insights Chart v3", {"workbook": wb}, ["name", "title", "chart_type", "query", "config"], order_by="sort_order asc")
report = [(c.title, c.chart_type, config_errors(c.chart_type, c.query, frappe.parse_json(c.config or "{}")) or len(frappe.get_doc("Insights Chart v3", c.name).get_data(force=True)["rows"])) for c in charts]
print("\n".join(f"{r[2]!s:>6}  {r[1]:8} {r[0]}" for r in report))
PY
```

Every line must end in a row count. A `0` or a list of errors is a failure. A
card that draws nothing is a failed gallery, not a quiet one.

## Notes on the stored shape

Read `insights/insights/doctype/insights_chart_v3/chart_query.py` first. It
turns a chart type and a config into operations, and it is the only thing that
does. These are the parts that surprised us.

- **Sankey aggregates.** `_add_sankey_operation` groups by the source and the
  target. Its base query stays per-row like every other type.
- **Pivot column names depend on the measure count.** One measure and a split
  gives one column per split value, such as `Men`. Two or more measures joins
  the names, such as `Revenue___Men`. Conditional formatting on a pivoted table
  names the joined form.
- **Pivot cells are null where a pair has no rows.** `Jumpsuits & Rompers` has
  no men's revenue, so that cell is null and not zero.
- **The count measure is special-cased.** `column_name: "count"` with
  `aggregation: "count"` counts rows. It does not name a column called `count`.
- **A dimension renames its output column.** `dimension_name` becomes the result
  column's name, and it falls back to `column_name`.
- **Every chart config carries `order_by`, `filters` and `limit`.** Derivation
  reads all three whatever the chart type is.
- **Reference lines sit under `y_axis`,** and a line on a dual-axis chart names
  the axis it belongs to with `align`.
