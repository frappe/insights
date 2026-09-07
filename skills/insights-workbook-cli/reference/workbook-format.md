# Workbook import format

This is the envelope for `import_workbook`. Use it to import a workbook JSON somebody gave you.
It is not the authoring path. See `documents.md` for that. Import always creates a new workbook,
so it cannot add to one that exists.

`import_workbook` accepts this envelope. It creates the workbook and all its contents in one call.
It remaps the internal names you choose to fresh doc names. The remap covers chart-to-query
references, query-to-query references, and dashboard filter links.

A workbook the site imported from a template shows the envelope. Find one with
`doc list "Insights Workbook" --fields name,title,from_template --all`.

It returns the other half of that remapping:

```jsonc
{
  "workbook": "42",                          // the new workbook name
  "names": { "q-invoices": "17", "c-revenue-trend": "23", "wb-sales": "42" }
}
```

`names` maps every internal name you chose to the doc name it received. It covers queries, charts,
dashboards, folders and the workbook itself. Keep it. It lets you edit what you just created
without a listing call first.

```jsonc
{
  "version": "1.0",
  "type": "Workbook",
  "name": "wb-sales",                      // internal name, remapped on import
  "doc": { "name": "wb-sales", "title": "Sales Performance" },
  "dependencies": {
    "folders": [],
    "queries": {
      "q-invoices": {
        "name": "q-invoices",
        "title": "Sales Invoices",
        "workbook": "wb-sales",
        "folder": null,
        "sort_order": 0,
        "use_live_connection": 1,
        "is_script_query": 0,
        "is_builder_query": 1,
        "is_native_query": 0,
        "operations": [ /* see reference/operations.md */ ],
        "variables": []
      }
    },
    "charts": {
      "c-revenue-trend": {
        "name": "c-revenue-trend",
        "title": "Revenue Trend",
        "workbook": "wb-sales",
        "folder": null,
        "sort_order": 0,
        "query": "q-invoices",              // internal query name
        "chart_type": "Line",
        "config": { /* see reference/charts.md */ }
      }
    },
    "dashboards": {
      "d-overview": {
        "name": "d-overview",
        "title": "Sales Overview",
        "workbook": "wb-sales",
        "items": [ /* see reference/dashboards.md — internal names in `chart` and in filter links */ ]
      }
    }
  }
}
```

Notes:

- Use consistent internal names (`q-*`, `c-*`, `d-*`). Every reference must match the key it points
  at, exactly.
- **The importer drops a reference it cannot resolve, and reports nothing.** A filter link
  disappears from the imported dashboard if its chart key or its `` `query` `` segment is not one
  of your internal names. The filter then does nothing, silently. Check the link names before you
  import.
- Inside a `{ "type": "query", ... }` table reference, the importer remaps only `query_name`. The
  build reads only `query_name`. The `workbook` field there is documentation.
- Import creates a NEW workbook every time. To iterate on a build, patch the created docs directly.
  `names` gives you each doc name. The JSON field is `Insights Query v3.operations`,
  `Insights Chart v3.config` or `Insights Dashboard v3.items`. Import again only after you delete
  the previous attempt.
- To read an existing workbook, fetch its `Insights Query v3`, `Insights Chart v3` and
  `Insights Dashboard v3` docs filtered by `workbook`.
