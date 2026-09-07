# Workbook import format

This is the envelope for `import_workbook`, which is for importing a workbook JSON somebody gave
you. It is not the authoring path — see `documents.md` for that. Import always creates a new
workbook, so it cannot add to one that exists.

`import_workbook` accepts this envelope and creates the workbook and all its contents in one call,
remapping the internal names you choose to fresh doc names — including chart-to-query references,
query-to-query references, and dashboard filter links. The shipped templates in
`insights/workbook_templates/*/workbook.json` are canonical examples.

It returns the other half of that remapping:

```jsonc
{
  "workbook": "42",                          // the new workbook name
  "names": { "q-invoices": "17", "c-revenue-trend": "23", "wb-sales": "42" }
}
```

`names` maps every internal name you chose — queries, charts, dashboards, folders and the workbook
itself — to the doc name it received. Keep it. It is how you edit what you just created without a
listing call first.

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

- Use consistent internal names (`q-*`, `c-*`, `d-*`). What matters is that every reference matches
  the key it points at, exactly.
- **A reference the importer cannot resolve is dropped, not reported.** A filter link whose chart
  key or whose `` `query` `` segment is not one of your internal names disappears from the imported
  dashboard, and the filter then silently does nothing. Check the link names before importing.
- Inside a `{ "type": "query", ... }` table reference only `query_name` is remapped and only
  `query_name` is read at build time; the `workbook` field there is documentation.
- Import creates a NEW workbook every time. When iterating on a build, patch the created docs
  directly — `names` gives you each doc name, and the JSON field is `Insights Query v3.operations`,
  `Insights Chart v3.config` or `Insights Dashboard v3.items`. Import again only after you delete
  the previous attempt.
- To read an existing workbook, fetch its `Insights Query v3`, `Insights Chart v3` and
  `Insights Dashboard v3` docs filtered by `workbook`.
