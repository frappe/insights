# The documents

A workbook is four doctypes. You create, read and patch them as plain documents. Each of the
three content doctypes requires exactly one field, `workbook`. Each takes its permission from that
workbook. Write on the workbook is write on its contents.

The site assigns names. Create in dependency order. Queries first, then charts, then dashboards.
Keep what each call returns.

## Insights Workbook

Only `title` is required. Create one only when the user asks for a new workbook.

```json
{ "title": "Sales Performance" }
```

If you delete a workbook, you delete its queries, charts, dashboards and folders.

## Insights Query v3

```json
{
  "workbook": "42",
  "title": "Sales Invoices",
  "use_live_connection": 0,
  "is_builder_query": 1,
  "is_native_query": 0,
  "is_script_query": 0,
  "operations": [ ],
  "sort_order": 0
}
```

- `operations` is the pipeline. See `operations.md`.
- The four flags are the builder-query set from `rules.md`. Only a `sql` query flips
  `is_native_query` to 1 and `is_builder_query` to 0.
- `use_live_connection` picks the source: 0 reads the data store, 1 reads the source database.
  It is per query, and every table in the query follows it.
- `folder` is optional and names an `Insights Folder` in the same workbook.
- A query may source from another query **in the same workbook** through
  `{ "type": "query", "query_name": "<query doc name>" }`. A reference to a query in another
  workbook builds and runs. But the workbook's source selector cannot show it, so the user cannot
  edit it. Copy the calculation instead.

## Insights Chart v3

```json
{
  "workbook": "42",
  "title": "Revenue Trend",
  "query": "a1b2c3d4e5",
  "chart_type": "Line",
  "config": { },
  "sort_order": 0
}
```

- `query` is the base query's real document name.
- `chart_type` and `config` shapes are in `charts.md`.
- On save the chart creates its own empty `data_query`. This second `Insights Query v3` document
  holds the aggregation the UI builds at render time. You never write it. Running it proves
  nothing until somebody opens the chart.
- If you delete a chart, its `data_query` goes too.

## Insights Dashboard v3

```json
{
  "workbook": "42",
  "title": "Sales Overview",
  "items": [ ]
}
```

- `items` holds chart and filter items. The model has a third type, `text`. Never author it.
  See `dashboards.md` for the layout grid, the merge rule and the
  filter link syntax.
- A chart item names the chart's real document name. A filter link names the real query name in
  its `` `query`.`column` `` value.
- Every item needs a unique `layout.i`.

## Insights Folder

Optional. It groups queries or charts inside one workbook.

```json
{ "workbook": "42", "title": "Helpers", "type": "query", "sort_order": 0 }
```

`type` is `query` or `chart`. The site deletes an empty folder when its last item goes.
