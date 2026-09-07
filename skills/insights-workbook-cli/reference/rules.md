# Hard rules

Frappe Insights v3 stores everything as JSON. A **query** is a linear pipeline of operations, a
**chart** aggregates one query, a **dashboard** lays out charts and filters. You author that JSON.
The app compiles it to ibis and runs it against the source database.

These rules are not stylistic. If you break one, you get a broken workbook, a wrong number, or a
resource the user cannot edit in the UI.

1. **Queries return per-row data. Charts aggregate.** A chart builds its own `summarize` at render
   time from its config. A pre-aggregated query leaves the chart nothing to group, and dashboard
   filters nothing to filter on. It also breaks drill-down. Insights cuts the pipeline off before
   the last `summarize`, so a per-row query puts the source rows one click away. See "Drill down"
   in `charts.md`.
2. **`summarize` is a mid-pipeline grain change only.** For example, roll ledger rows up to one row
   per invoice before you join back to invoice detail. Never use it as the last operation of a
   query. That is the chart's job.
3. **Never emit a bare `filter` operation. Always `filter_group`**, even for one condition. The
   UI's filter editor renders only filter groups, so a bare `filter` is invisible and uneditable.
4. **No `code`, no `custom_operation`, no script queries.** Authoring does not support them. They
   bypass the builder UI, and you cannot validate them. Use builder operations.
5. **`sql` is a last resort.** Use it only when builder ops cannot express the ask. Say so in your
   reply. A native query loses UI editability and portability across databases.
6. **Never invent a table, column, or operation type.** Use exact names from the schema you were
   given, and the operation types listed below. If something looks impossible, compose the allowed
   ops. A calculated value is a `mutate` or an expression measure, not a new operation type.
7. **Column names are resolved against the pipeline state at that point.** After `rename`,
   `summarize`, or `pivot_wider`, refer to the new (sanitized, snake_case) names.
8. **Keep every column a chart or dashboard filter will need.** Trim with `select` for width, but a
   column you drop is a filter that cannot be wired later.

# Builder query flags

Queries you create are builder queries: `is_builder_query: 1`, `use_live_connection: 1`,
`is_native_query: 0`, `is_script_query: 0`. Only a `sql` query flips to `is_native_query: 1`,
`is_builder_query: 0`.
