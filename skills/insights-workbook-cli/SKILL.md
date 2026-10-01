---
name: insights-workbook-cli
version: 3
description: Create, read, update and delete Frappe Insights workbooks — queries, charts and dashboards — on a stock Insights 4 (develop) site through the frappectl CLI. Use when the user asks for an Insights workbook, query, chart or dashboard, or wants an existing one changed, explained or deleted.
---

# Insights workbooks over frappectl

You author workbook content and push it to a live Insights site with `frappectl`. This file is the procedure. `reference/` is the contract.

This skill needs nothing installed on the site. It supports Insights 4 (develop) sites only. Section 1 checks the version.

## Before you start

The user owns the `frappectl` profile for the site. Check it:

```sh
frappectl -s <profile> auth whoami
```

If the site has no profile, stop and tell the user to make one. Do not run `auth` commands. Do not set `FRAPPE_*` variables.

Pass `-s <profile>` on every call. The examples write `$SITE` for it.

To shorten the command, define a shell function: `fc() { frappectl -s <profile> "$@"; }`. Do not put the command in a variable. zsh does not split `$S` into words, so `S="frappectl -s x"; $S ...` fails.

`frappectl` prints a deprecation warning from `authlib` on stderr. It is noise. Parse stdout only, and never merge stderr into it (`2>&1`), or the JSON does not parse.

## The CLI is the only interface

Every action on the site goes through `frappectl`. Never read or write the site's files, database, logs or bench, even when the site runs on this machine. What a local path tells you does not hold on the site the workbook must run on.

**Assume you do not have the Insights source, because most users do not.** Nothing in this skill needs it. Every fact about the site is a call: its tables, its columns, its stored data, its function library. To know whether something exists, ask the site.

### When a call fails and the error names no cause

Insights returns some failures as an exception type and nothing more. An Insights user is a Website User, so the framework suppresses the traceback. Do not read the site's code. Take these three steps.

1. Retry the call once. Change only what could matter.
2. Bisect over the API. Shrink the payload until you have the smallest call that still fails. Say what that proves.
3. Stop and report to the user. Give the exact command and the exact response.

An error you cannot act on is a site or environment fault, not a payload fault. Hand the user a clean reproduction. Before you report it, run the call again with `--debug`. It prints the request and the server's own messages to stderr, and Insights often names its fault only there.

These exception types do name a cause. Fix that part of the payload. Do not bisect:

| Exception | Fix |
|---|---|
| `UnknownColumn` | A column, table or query name. Compare it with the table's columns or the base query's `columns`. An expression that reads a column the table does not have, bare, as `q.col` or as `q['col']`, fails with this type too. |
| `NotPermitted` | The user may not read a table, a query or a column the query reads. Pick another, or ask the user for access. |
| `QueryRefused` | The operation's shape: a join type, operator, aggregation or granularity. Compare it with `reference/operations.md`. |
| `TableNotStored` | A data store run that may not import read a table that is not stored. Store it, or run on the live connection. See "Sample the data" in section 5. |
| `ExpressionSyntaxError` | An expression. Check each function with `get_function_description`. |
| `QueryTimeout` | The query's cost. Filter earlier, join less, or read the data store. |

A failed run names the operation it failed in, and keeps its exception type: `Operation 2 (mutate 'doubled'): UnknownColumn: NameError: name 'foo' is not defined. Expression: foo * 2`. The number counts the query's operations from 1. After the colon comes the cause, `<type>: <text>`. A failure in a query this one reads adds that query's title, and names the inner operation once: `Operation 1 (source): Operation 2 (mutate 'doubled') in query 'Open Tickets': ...`. Only a user who may edit the query reads the cause. Anyone else reads the operation and the exception type, such as `Operation 1 (source): TableNotStored`. `NotPermitted` names no operation. `reference/expressions.md` has the rest of an expression's error. An older site answers only the exception type, or a bare `^`. Then `--debug` shows the cause.

## 1. Read the site before you plan

```sh
frappectl -s $SITE auth whoami
frappectl -s $SITE method call insights.api.get_app_version
frappectl -s $SITE method call insights.api.data_sources.get_all_data_sources
frappectl -s $SITE method call insights.api.workbooks.get_workbooks
```

You act as the profile's user, and you see what that user sees. `get_workbooks` lists what the user created or was given, admins included. An admin finds anyone else's workbook with `sources=["created","shared","others"]`. For anyone else, a workbook it does not list is a missing share, not a missing workbook. Insights reports a missing grant as "not found". Ask the user to share it.

### Read the site's version too, not only its data

Read `get_app_version` before anything else. It returns a string such as `"4.0.0-dev"` or `"3.14.1"`. **If the major version is below 4, stop.** Tell the user this skill supports only Insights develop sites. An older site accepts payloads it does not understand and reports no error: it ignores unknown chart config keys, `import_workbook` returns only a name, and `json_value` is missing. The workbook then looks built and is wrong.

A develop site can still be older than this file, so an endpoint this file names may not be there. Before you depend on one, call it once with no arguments:

```sh
frappectl -s $SITE method call insights.api.ai.lineage.describe_query
```

Only a missing method answers `Failed to get method`, such as `error: Failed to get method insights.api.ai.lineage.describe_query with No module named 'insights.api.ai.lineage'`. Any other answer, a missing-argument error too, means the method is there. Probe each endpoint once per session. Do not use `method search`. It returns no results even for a method that exists.

A query document method, such as `profile_column`, has no path to probe. `profile_column` arrived with `describe_query` and `verify_workbook`, so a site that has one has all three.

**Every procedure here works on a develop site with no newer endpoint.** A newer endpoint does the same job faster, never a different job. A missing endpoint costs round trips, never a result. If one is missing, take the plain path and continue. Do not stop. Do not tell the user their site is behind unless they ask.

The same holds for a function `get_function_list` does not return: the plan changes, the ask does not.

### Translate the ask into the site's vocabulary

The user asks in business language. "Support tickets raised by partner sites" names no table and no column. Most users cannot name one. Only an admin knows what data is where. You must translate the ask, and this step is the most likely to go wrong.

Work the ladder in order. **The corpus comes before the schema.**

A schema tells you a column exists. It never tells you the column is the right one. A query somebody wrote and uses holds a definition that survived contact with the business.

**1. Name the data sources.** `get_all_data_sources`. Their names are the first map: which system holds tickets, which holds sites, which holds billing. An ask that spans two of them is normal.

**2. Search the corpus for every business word in the ask.** This is the step that pays. "Partner", "active customer", "churned" and "enterprise" are decisions somebody encoded once, in a title, a `mutate`, a `case_when`, a filter value or a `sql` query. Section 3 has the searches. Run them for every noun and every qualifier the user used, before you look at a single table.

A hit gives you the calculation *and* the tables it reads, so it settles steps 3 and 4 at once.

Take the definition from a hit, not its framing or its population. A template's metrics are not the user's focus. A workbook built for one audience does not say who the user's population is. And when a table has a column that names the thing directly, such as one row per app, prefer it to the key a corpus query joins through.

**On an ERPNext site, the app's own reports come first.** Gross Profit, Stock Balance and Accounts Receivable are Script Reports, and each is ERPNext's definition of its measure. The user already trusts it. Build to match it, and reconcile against it in check 4 of section 6:

```sh
frappectl -s $SITE doc list "Report" --filters-json '{"ref_doctype":"Sales Invoice"}' --fields name,report_type --all
frappectl -s $SITE report run "Gross Profit" \
  --filters-json '{"company":"Acme","from_date":"2026-01-01","to_date":"2026-03-31","group_by":"Invoice"}'
```

A report's filters are the `fieldname`s its form asks for. Pass every filter the form fills in by default, too: the form sets Gross Profit's `group_by`, and the report fails without it.

**3. Search table labels for what the corpus did not answer.** If you omit `data_source`, `get_data_source_tables` searches the whole instance. It matches the table's `label` and its real name:

```sh
for word in ticket partner site; do
  frappectl -s $SITE method call insights.api.data_sources.get_data_source_tables \
    -F search_term=$word -F limit=50
done
```

Frappe doctype names are business language, so one search per noun cuts hundreds of tables to a handful.

**4. Read the columns of the few tables that survived.**

```sh
frappectl -s $SITE method call insights.api.data_sources.get_data_source_table_columns \
  -F data_source="Frappe Cloud" -F table_name="tabSite"
```

`get_schema -F data_source=<name>` returns every table with its columns in one call. It opens each table on the backend unless the site stores its column lists, so it is the most expensive call in the skill. Use it only when you must search columns rather than tables. Say that you did.

A newer site searches columns directly, across every table the caller may read:

```sh
frappectl -s $SITE method call insights.api.ai.search.search_columns -F term=partner
```

It answers from stored column lists. A table nobody has synced or opened is not in it, so an empty answer is not proof. Fall back to `get_schema` when the answer matters.

**Pick tables the dashboard's reader can read.** A chart runs with its reader's permissions unless its `run_as_owner` is set. A reader who cannot read a table sees the card refused: on one site a Sales Manager could not read Item, and an Expense Approver could not read Employee. Ask who reads the dashboard. If it needs a table that reader cannot read, say so in the scope block.

**5. Ask.** What the ladder does not resolve goes in the scope block as a question, with the candidates you found. Do not guess a definition somebody has already written down.

### Say what you leaned on

Discovery makes choices and the user sees none of them. Name every one, in the scope block and again in the closing summary. One line each:

- **Reused a definition.** The workbook, the query, and the expression you copied. If the user's ask differs from it, say how and ask.
- **Derived a definition yourself.** Say that you found no existing one. Name the columns you built it from. Ask the user to confirm it. **This line matters most.** The people who use a reused definition checked it. Nobody checked the one you derived.
- **Picked one candidate over others.** Name what you rejected, and why. A search that returned three tables and a search that returned one are different situations. Only you can see which happened.
- **Made a load-bearing cut.** A date the data starts, a filter that drops rows, a source you chose because a table was not stored. Each one changes the number. When a JSON payload changed shape over time, split it by the version field it carries, not by a date.
- **Leaned on a source that sees part of the population.** Name the part. Telemetry comes only from sites that opted in. If another source sees more, such as a web analytics tool for website visits, say so.
- **Built ahead of the data.** When the user asks for a chart before its data exists, keep the chart and say it reads empty until the data arrives. Do not drop it.

Silence here reads as certainty. Do not spend certainty you do not have.

### Tip when the ask names a chart but not a question

Users who are not analysts often ask for a chart type ("a pie chart of orders by status") when what they want is an answer ("which orders are stuck"). Build what they asked for. Then, in the closing summary, add one line suggesting they describe what they want to learn next time, so you can choose the query and chart.

Skip the tip when the ask already says what the chart is for. Give it once per conversation.

### A query spanning two data sources needs the data store

One flag decides cross-source. With `use_live_connection: 0` every table resolves through the warehouse, whatever its data source, so tables from two sources join normally. With `use_live_connection: 1` each table opens on its own backend, and a join across two of them cannot run.

So an ask that spans two systems is a data store query, and every table it needs must be stored. See "Choose the data store or the live connection" in section 5.

## 2. Read the contract

Read `reference/rules.md` now. It is short, and every rule in it is load-bearing.

Read the rest when the plan needs it:

| File | Read it before you write |
|---|---|
| `reference/documents.md` | any document you create — the field shapes |
| `reference/operations.md` | any query pipeline |
| `reference/expressions.md` | any `mutate`, expression measure or expression filter |
| `reference/charts.md` | any chart config |
| `reference/dashboards.md` | any dashboard layout or filter link |
| `reference/workbook-format.md` | only when importing a workbook JSON the user gave you |

Plan only with the operation types, chart types and functions these files list. Never invent one.

The site is the authority on the function library. "The site holds the real list" in `reference/expressions.md` gives the two calls that read it. Read a function's docstring before you use one these files do not cover, or describe in one line only.

For worked examples, read what the site already has (section 3). A workbook an app ships is a good one: `doc list "Insights Workbook" --fields name,title,is_standard --all`.

## 3. Reuse what the user already has

People share workbooks. A measure somebody already defined and uses every day is more likely correct than one you derive from column names. **Run these searches before you read the schema.**

Open a `sql` query even when you would not author one. Definitions nobody could express in builder operations end up there, so those queries hold the densest tribal knowledge on the site. Read the SQL, take the calculation, and rebuild it as builder operations.

**Search the corpus. Do not download it.** Titles and the JSON fields are text columns, so the site greps them for you. A `like` filter is the whole search.

**Search titles first.** A person wrote them, in the same business language the user uses. These searches translate "partner" into a real definition:

```sh
frappectl -s $SITE method call insights.api.workbooks.get_workbooks -F search_term=partner
frappectl -s $SITE doc list "Insights Query v3" \
  --filters-json '{"title":["like","%partner%"]}' --fields name,title,workbook --all
frappectl -s $SITE doc list "Insights Chart v3" \
  --filters-json '{"title":["like","%partner%"]}' --fields name,title,workbook,chart_type --all
```

`search_term` matches workbook titles only, so run the query and chart searches too. A workbook titled "Cloud Metrics" can hold the partner definition.

These searches work on every site. A newer site has one endpoint that runs them all in a single call. Probe for it once (section 1). Use it when it is there:

```sh
frappectl -s $SITE method call insights.api.ai.search.search_content -F term=partner -F limit=20
```

A hit names `doctype`, `name`, `title`, `workbook`, `workbook_title`, `matched_field` and a `snippet` of the text around the match. The snippet is the reason to prefer it. You can tell a real definition from a coincidence without fetching the document.

**A hit also includes `used_by_charts`, `used_by_dashboards` and `dashboard_views`.** Read them. Three queries can define "partner" three ways. The one behind a dashboard forty people open every week is the definition the organisation runs on. An orphan query somebody made once is not. Prefer the used one, and say in the scope block how much it is used.

Without the endpoint you get the same documents, in more calls, with no snippet and no usage count. The searches do not change. Rank by hand instead, and say you did.

**For a query you found, read its lineage.** A newer site answers both directions in one call:

```sh
frappectl -s $SITE method call insights.api.ai.lineage.describe_query -F query=<name>
```

`upstream` holds every query it reads, through every hop, and the tables at the end, each with `stored`, `row_limit` and `sync_from`. `downstream` holds the queries built on it, the charts on those, the dashboards that show those charts, and the `filter_links` that name one of those queries. It is permission filtered, so a query you cannot read answers "not found". `downstream` comes from an index a background job rebuilds after each save, so a query saved a moment ago may be missing from it. `upstream` is read from the operations and is always current. Without the endpoint, `doc get` each query in the chain and run the `like` searches above for its name.

**Then search the JSON.** It reaches column names, expression text, filter values and measure names. A definition lives there even when no title says so:

```sh
frappectl -s $SITE doc list "Insights Query v3" \
  --filters-json '{"operations":["like","%partner%"]}' --fields name,title,workbook --all

frappectl -s $SITE doc list "Insights Chart v3" \
  --filters-json '{"config":["like","%base_net_total%"]}' --fields name,title,workbook,chart_type --all
```

Search one word at a time. Search the words the *user* used before the words the schema uses. `like` matches a substring and nothing else. It has no synonyms and no stemming, so "partner" finds "is_partner" and "Partner Sites". "partner persona" finds neither.

Each search returns a shortlist of names. Then `doc get` the two or three worth reading. Read their `operations` for the calculation: the expression, the aggregation, the filter group that defines "revenue" or "active customer" here. Do not list every query with its `operations`. On a site with six hundred workbooks that is useless.

**Copy the calculation into your own query. Do not reference the other workbook's query.** A cross-workbook query reference builds and runs, but the workbook's source selector lists only queries in its own workbook, so the user cannot see or edit where the data came from.

Say what you reused. See "Say what you leaned on" in section 1.

## 4. Converge on scope with the user

Before you author anything, post a scope block. It states:

- the target workbook, by name
- the counting unit: what one counted thing is, such as a site, a team or a signup. A team with three sites counts three times when the unit is a site. Name the dashboard by its unit: "Insights Sites", not "Insights Users", when it counts sites
- the tables to read from, and the grain of each query
- every measure, with the exact columns it computes from
- any definition you reused, and where it came from
- the dimensions and the filters
- what the user is actually looking at, so the dashboard leads with it

When more than one column could serve a measure, name the candidates and ask which one. Never resolve that ambiguity alone. Never put an unasked choice into the closing summary.

A sample writes nothing: an unsaved query saves no document. So sample while you scope. See "Sample the data" in section 5.

**Stop here.** Post the scope block, end your turn, and wait for the user's reply. Agree the scope with the user, not with yourself.

## 5. Author

### Never create a workbook the user did not ask for

The default is to add to a workbook that exists. "Add a chart", "fix this query" and "put a filter on the dashboard" all create documents inside the named workbook. None of them creates a workbook.

Create a workbook only when the user asks for one in those words. When the target workbook is unclear, ask which one. Do not resolve it by making a new one.

Ask before you create a workbook when:

- the user names no workbook and more than one could fit
- the work would fit an existing workbook you can see
- you recover from a failed attempt. Patch or delete what you made. Never leave a second copy

### Write through a build script

Every write goes through a Python script. Reading and exploring stay direct `frappectl` calls.

The reason is verification. The checks in section 6 are list comparisons. An agent that compares lists by hand reports a verdict nobody can audit. In a script the result is an exit code.

`examples/build_workbook.py` is that script. Copy it and edit its `build()`, or import it from your own script:

```python
import sys; sys.path.insert(0, "<skill>/examples")
import build_workbook as bw

bw.configure("<profile>", "<workbook>")
b = bw.Build()
query = b.upsert("invoices", bw.QUERY, {"title": "Sales Invoices", "operations": [...], ...})
b.upsert("revenue", bw.CHART, {"title": "Revenue", "query": query, "chart_type": "Line", "config": {...}})
sys.exit(bw.verify())
```

`Build.upsert(key, doctype, fields)` creates the document behind `key`, or updates it in place, and returns its real name. The keys are yours. Keep them stable, because a key is how a rerun finds its document. The build keeps a state file next to the script, `<script>.state.json`, with the name behind each key and what the build last wrote. So a rerun never makes a second copy, and a field the user edited on the site since keeps the user's value. The run prints each one it kept. Tell the user which.

Run the copy with `--site` and `--workbook`. `--verify` skips the build. `--redesign` replaces a dashboard's `items` whole, for a redesign the user asked for, and only while the live `items` still equal what the build last wrote. See "Write a whole `items` array exactly once" below.

The script also holds the client (`call`, `method`, `get_doc`, `list_docs`), the probes (`run`, `profile`), the dashboard merge (`patch_dashboard`) and the verify. Use them. Do not write them again.

### Sample the data

Run an unsaved pipeline as a query document that is never saved, the way the Builder runs one. Give it a `new-` name and the target workbook. The user needs read on that workbook:

```sh
frappectl -s $SITE method call insights.api.run_doc_method -F method=execute \
  -F 'docs:={"doctype":"Insights Query v3","name":"new-insights-query-v3-1","__islocal":1,"workbook":"<workbook>","is_builder_query":1,"use_live_connection":0,"operations":[{"type":"source","table":{"type":"table","data_source":"Site DB","table_name":"tabSite"}}]}' \
  -F 'args:={"page_size":21,"import_if_not_exists":false}'
```

It answers as `execute` does (`sql`, `columns`, `rows`, `time_taken`). To know whether the result has more rows than you need, ask for one more: 21 rows for a page of 20 means it has. `page_size` is 10,000 at most.

Profile one column with `profile_column`, a method of the query document. Call it on a saved query, or through `run_doc_method` with `-F method=profile_column` on an unsaved one. A raw table is a pipeline of one `source` operation:

```sh
frappectl -s $SITE method call profile_column --doctype "Insights Query v3" --name <query> -X GET \
  -F column_name=status -F by=plan
```

It answers `column`, `row_count`, `null_count`, `distinct_count`, `min`, `max` and `top_values` (`value`, `count`, `share`). With `by` it also answers `coverage`: per value of `by`, its `row_count`, its `non_null_count` and the share of those rows with a value in `column_name`. `limit` caps each list, 20 by default and 1,000 at most. `column_name` and `by` must be the exact column names of the query's result: any other name is `UnknownColumn`. The answer comes from a 10-minute cache. `force` skips it.

**Pass `import_if_not_exists: false` on a data store `execute` sample.** Without it, a table that is not stored reads as an empty table and queues its import. With it, the run fails with `TableNotStored`. `profile_column` never imports, so on such a table it always fails that way. A user who may edit the query reads `Operation 1 (source): TableNotStored: tabSite of Site DB is not stored in the Data Store`, anyone else `Operation 1 (source): TableNotStored`. Match the class, not the text: the site translates the text. A table the user may not read is refused as not permitted before that. An older site ignores the flag, reads empty and queues the import, so check `get_data_store_tables` before a data store sample there.

`examples/build_workbook.py` wraps both as `run()` and `profile()`. `run()` adds `truncated`, and both raise `TableNotStored`. On a site without `profile_column`, `profile()` builds the same answer from `summarize` runs.

**Send a query document method as GET.** `frappectl` sends POST by default, and a document method sent as POST needs write on the document. So `-X GET` on `profile_column`, `execute`, `get_count`, `get_distinct_column_values` and `get_column_range` lets them run on a query you may only read, such as one you found in section 3. `run_doc_method` checks read itself, so either method works. A read-only profile sends every call as GET, and every sample here works there. An older site refuses `args` in a GET to `run_doc_method`. There, use a profile that may POST.

### Create the documents

Queries, charts and dashboards are plain documents. Each requires exactly one field: `workbook`. Permission follows the workbook. Write on the workbook is write on its contents.

Create them in dependency order, and keep the name the site returns for each:

1. **Queries.** Set `workbook`, `title`, `operations`, and the builder flags from `reference/rules.md`.
2. **Charts.** Set `workbook`, `title`, `query` (the query's real document name), `chart_type` and `config`.
3. **Dashboards.** Set `workbook`, `title` and `items`. Chart items name the real document name of a chart in the same workbook; a chart of another workbook is refused. Filter links name the real query name. A `text` item is only a short section heading, written as HTML. See `reference/dashboards.md`.

**Write a whole `items` array exactly once, at creation.** After that the user owns the layout. They move charts, resize them and add filters, and all of it lives in the same array. A second run that writes the array your script computed destroys those edits without a word. Every later change is a merge into the live `items`. `reference/dashboards.md` gives the merge. `examples/build_workbook.py` ships it as `patch_dashboard()`.

So a build script must not rebuild the dashboard to add one chart. Add the chart. Merge one item. `Build.upsert` merges on its own. The one exception is a redesign the user asked for: `--redesign`.

```sh
frappectl -s $SITE doc create "Insights Query v3" --input /tmp/query.json
```

You use real document names throughout, so a reference either resolves or fails loudly.

### Choose the data store or the live connection

A query reads from the data store when `use_live_connection: 0`, and from the source database when it is `1`. The flag is per query. Every table in one query resolves the same way. You cannot mix.

Prefer the data store. It returns faster. A table you query gets stored, so the next run is faster still.

Check what is stored before you choose:

```sh
frappectl -s $SITE method call insights.api.data_store.get_data_store_tables \
  -F data_source="Site DB" -F limit=200
```

If most of the tables your query needs are stored, set `use_live_connection: 0` and take the rest with them.

**The first run then returns zero rows. This is the one case where an empty result is a failure.** A saved query or a chart that reads a table that is not stored yet does not fail. Insights queues the import and substitutes an empty table with the right schema. The import copies the whole table, up to its row limit, so on a large table it takes long. So:

1. Before you set `use_live_connection: 0`, list which of your tables are missing from `get_data_store_tables`.
2. If any is missing, tell the user. The import is queued, and the workbook reads empty until it finishes.
3. Run verify check 1 again after the import. Zero rows from a table you know is not stored yet is an unfinished import, not a result.

A stored table is not live. It refreshes on its `sync_schedule`, daily by default. A question about today's rows needs `use_live_connection: 1`.

Two limits to read before you trust a stored table for a question about history:

```sh
frappectl -s $SITE doc get "Insights Table v3" <name>
```

`row_limit` caps the stored copy and keeps the **newest** rows. An empty `row_limit` falls back to `max_records_to_sync` in Insights Settings, then to 1,000,000. `sync_from` cuts off everything before a date. A stored table is often a recent window, not the whole table. When the ask needs more history than the window holds, use `use_live_connection: 1` and say why.

For a saved query, `describe_query` gives `stored`, `row_limit` and `sync_from` of every table upstream in one call.

## 6. Verify

Verification is your compile step. Never call work finished before it verifies clean. Run the checks from the build script: `verify()` in `examples/build_workbook.py`.

A newer site runs checks 1 to 3 in one call:

```sh
frappectl -s $SITE method call insights.api.ai.verify.verify_workbook -F workbook=<name> \
  -F 'filters:={"Company": {"operator": "=", "value": "Acme"}}'
```

It answers `ok`, and one entry per query, chart and dashboard with its own `ok` and the fault: `error` for a query, `errors` for a chart, `errors` for a dashboard's items and filter links. A column the config names that the query lacks fails the chart's run, so it shows in `errors`. A chart drops a sort its result has no column for without an error, so its entry names that sort in `unresolved_order_by`. That fails the chart only when it has a `limit`, where a lost sort changes which rows it keeps. Each query runs without importing, so a data store query that reads a table not stored yet is not `ok`, and its `error` says so. A chart on that query is not run, and carries the same error. A chart item must name a chart of the same workbook; a save refuses a chart of another workbook. With `filters` it also renders each dashboard's charts under the filters of that state the dashboard has. A filter no dashboard of the workbook has goes in the top-level `errors`. `rows` is the length of one page, never a total. Without the endpoint, or on a read-only profile, which cannot POST, `verify()` runs checks 1 to 3 itself, as below. Check 4 is yours on every site.

### Check 1 — every query builds and runs

```sh
frappectl -s $SITE method call execute \
  --doctype "Insights Query v3" --name <query_name> -X GET -F page_size=5
```

- `sql`, `columns`, `rows` and `time_taken` together mean the query compiled and ran.
- An empty `rows` is not a failure by itself. It **is** a failure on a data store query whose tables are not all stored yet. Compare the query's tables against `get_data_store_tables`. Do not warn and pass. See section 5. Always say the row count. Never accept zero silently.
- `rows` is one page, never a total. `execute` returns 100 rows unless `page_size` asks for more, and never more than 10,000. So `len(rows)` is not a count. A count is a measure: `count()` in a `summarize`, or `get_count` on the query.

### Check 2 — every chart runs

Saving a chart does not validate its config. A broken config shows only when the chart runs: a missing slot comes back as `{"errors": [...]}`, and an unknown column fails. So run every chart:

```sh
frappectl -s $SITE method call insights.api.view.get_chart_data -F chart=<chart_name>
```

The response includes `columns` and `rows`, one page at the chart's own `limit`. To test a config before you create the chart, send it to `insights.api.authoring.get_chart_data` (`chart_type`, `query`, `-F 'config:=<json>'`). A config it cannot render comes back as `{"errors": [...]}`, not as an exception.

When a chart fails, compare its config with its base query. Every column the config names, in dimensions, measures and chart filters, must be in the query's `columns` from check 1. Report any that is not, with the columns the query does have. A count measure and an expression measure name no column.

An `order_by` name is a column of the chart's result, not of its query, and a chart drops a sort its result's `columns` lack without an error. Warn about each one. Fail the chart when it has a `limit`: a top-N without its sort keeps other rows.

### Check 3 — every dashboard reference resolves

For each item in `items`:

- a `chart` item names a chart of the same workbook that you may read
- a `filter` item's `links` name charts that exist, and each link's query segment names a query whose `columns` from check 1 contain the column
- **that query is in the linked chart's chain**: its base query, or a query the base query reads from. Insights appends the filter to the query it names. A link to a query the chart does not read from passes every other check and does nothing.
- on a site without `verify_workbook`, every item has a `layout` with an `i`, `x`, `y`, `w` and `h`. The grid sums `layout.y + layout.h` over every item, so one item without a layout breaks the whole dashboard. A newer site's save fills what an item lacks, and gives a repeated `i` a new one, so it never refuses a layout.

### Check 4 — the numbers are right, not just the columns

Checks 1 to 3 prove the workbook compiles. They do not prove it says anything true. Two wrong charts shipped through a clean run of checks 1 to 3. Only a reproduction of the numbers caught them.

For every chart, run its aggregation with `run()`: the same dimensions, the same measures, the same filters. Read the rows. Then check each of these.

1. **Does the number match the chart's own claim?** An average over a group is the classic trap: a count of distinct dates divided by a site count is not the average days per site. Compute the measure a second way and compare.
2. **How many values does each dimension have, and how are they spread?** `profile()` answers `distinct_count`, the top values with their `share`, and with `by` the coverage per value of a dashboard filter column. One value is not a split at all: the column does not hold what you assumed, and the split lives on another column. A value that holds most of the rows is no split either, nor a dimension with values for only some values of a dashboard filter. Hundreds of values is the wrong chart type. "Making it readable" in `charts.md` maps the count to the chart.
3. **Is the signal present across the whole range?** Group the measure by month and read the series. A signal that starts partway through is not growth. It is the date somebody first recorded it. A signal that stops is retired, not fallen. Both read as a trend and are not one.
4. **Is the last period complete?** The newest bucket is usually a partial day, week or month, and it always plots as a fall. Confirm the maximum timestamp in the data before you call a drop real.
5. **Is there a null bucket?** A null bar after a join means rows the join did not match. Find out why before you label it "Unknown": on one site 36 archived sites had been renamed to `<site>.archived`, so their key no longer matched.
6. **Did a join multiply rows?** After each join, the row count must equal the distinct count of the key you meant to keep one row per. One duplicate row in the right table repeats every row it matches. A duplicate in `tabBench App` added 830 rows.
7. **Did you list the whole category before you called a value missing?** Before you say an event or a status does not exist, group the category it belongs to and read every value, such as every event where `app == 'setup'`. The value is often there under another name.
8. **On a monitoring dashboard, does each anomaly show?** Take incidents the user knows of, or plant one in the probe pipeline, such as a segment removed for one week. Every one must stand out on the chart meant to catch it. A chart that shows none of them monitors nothing.
9. **On a site with a host app report, does the board match it?** On ERPNext, run the Script Report the measure comes from, such as Gross Profit, with the same filters, and compare the totals. A difference is a definition you must explain or fix.

Report the row counts and the headline numbers in your reply. Any date cut, any retired signal, any gap in the data goes in the reply too. Do not put it in a dashboard text item or a chart title.

When a check fails, fix the chart. Do not describe the fault and leave it.

## 7. Read, update and delete

Read a whole workbook:

```sh
frappectl -s $SITE doc get "Insights Workbook" <name>
frappectl -s $SITE doc list "Insights Query v3"     --filters-json '{"workbook":"<name>"}' --fields name,title,operations --all
frappectl -s $SITE doc list "Insights Chart v3"     --filters-json '{"workbook":"<name>"}' --fields name,title,query,chart_type,config --all
frappectl -s $SITE doc list "Insights Dashboard v3" --filters-json '{"workbook":"<name>"}' --fields name,title,items --all
```

**Put every filter in one `--filters-json`, `workbook` with it.** `--filters-json` replaces every `-f` on the same command, it does not add to them. A list that pairs `-f workbook=<name>` with `--filters-json` returns documents of every workbook, and a patch loop over that list edits other users' queries. Before any `doc update`, check that the document's `workbook` is the target workbook.

`doc get` leaves out a field that is null. Read every field as optional. Many queries have no `title`.

Update one JSON field. Write the new value to a file and pass `--input`, or pipe the JSON on stdin. `--input -` does not read stdin:

```sh
frappectl -s $SITE doc update "Insights Query v3" <name> --input /tmp/patch.json
```

The JSON field per doctype is `operations` on `Insights Query v3`, `config` on `Insights Chart v3`, and `items` on `Insights Dashboard v3`.

Change only the field you mean to change. Preserve everything else. `doc update` fails on a concurrent edit. That is correct behaviour, so read the error before you reach for `--force`.

`--force` is not the answer to a dashboard you are about to overwrite either. The check compares `modified`. You read the document a moment before you write it, so the check passes. It guards against an edit made *during* your write, not against one made since your last run. Only the merge in `reference/dashboards.md` protects the user's edits.

**Before you rewrite a query, read what depends on it.** `describe_query` (section 3) lists every query, chart, dashboard and filter link downstream, in any workbook you can read. A query saved a moment ago may not show there yet. A query that other queries read is shared. A change to its columns breaks them. Add a column rather than rename one, or make a new query.

**When the user says "it used to work", read the history.** Queries, charts and dashboards track changes, so each save is a `Version` document with the changed fields. Only a System Manager can read them:

```sh
frappectl -s $SITE doc list "Version" --filters-json '{"ref_doctype":"Insights Query v3","docname":"<name>"}' \
  --fields name,owner,creation,data --all
```

**When the user asks how slow a query is, read the log.** Each run that did not come from the cache writes an `Insights Query Execution Log` with `query`, `time_taken` in seconds, `data_store` and `sql`. It answers without running anything:

```sh
frappectl -s $SITE doc list "Insights Query Execution Log" --filters-json '{"query":"<name>"}' \
  --fields creation,time_taken,data_store --limit 20
```

Delete:

```sh
frappectl -s $SITE doc delete "Insights Chart v3" <name>
frappectl -s $SITE doc delete "Insights Workbook" <name>
```

Deleting a workbook deletes its queries, charts, dashboards and folders. Confirm with the user before you delete anything you did not create in this session.

Verify again after any edit.

## 8. A workbook an app ships

A Frappe app can ship a workbook as a file, so every site that installs the app gets it. The site must run in developer mode, and the caller must be an Insights Admin. Build and verify the workbook as usual. Then mark it standard:

```sh
frappectl -s $SITE method call mark_as_standard --doctype "Insights Workbook" --name <workbook> \
  -F module="<module>" -F name=<new-name>
```

`module` is a module of an installed app. `name` is the name the workbook ships under, the workbook title by default, made URL-safe. The call renames the workbook to it, and each member to `<workbook>-<title slug>`, and rewrites every reference. It returns the new name. From then on, each save writes the file `<app>/<module>/insights_workbook/<name>/<name>.json`. The user commits that file to the app. You cannot read it over the CLI.

It also changes what readers see. A dashboard that named roles keeps them. Every other dashboard becomes visible to the Desk User role, so every desk user sees it. A role the site does not have is dropped. No chart runs as owner. Tell the user all of this before you call it.

Outside developer mode a standard workbook is read-only. On migrate, a site imports the file, and deletes a standard workbook whose file is gone.

To open a shipped dashboard from a Frappe sidebar, add a Sidebar Item with `link_type: Page`, `link_to: insights-dashboard` and `route: <dashboard name>`. The dashboard opens at `/app/insights-dashboard/<dashboard name>`.

## Appendix — importing a workbook JSON

Use this only when the user hands you a workbook JSON to import, such as an export from another site. It is not the authoring path.

```sh
frappectl -s $SITE api method/insights.api.workbooks.import_workbook --input /tmp/wb.json
```

The file holds `{"workbook": <envelope>}`. `reference/workbook-format.md` describes the envelope and its name remapping.

**Import creates a new workbook on every call**, so it cannot add to an existing one. It returns the new workbook name and a `names` map from your internal names to the real document names.

The importer drops a reference it cannot resolve, and reports nothing. Run the section 6 checks after any import.

## Commands

Confirmed against the Insights `develop` code. Do not assume anything outside this list exists. "Newer sites only" marks an endpoint to probe for first (section 1). "POST only" marks one a read-only profile cannot call.

| Purpose | Command |
|---|---|
| Who am I, and on which site | `auth whoami` |
| Insights version | `method call insights.api.get_app_version` — stop below 4 |
| List workbooks | `method call insights.api.workbooks.get_workbooks` (`search_term`, `limit`, `sources`: any of `created`, `shared`, `others`; `filters`: `[field, operator, value]` over workbook columns or `query`, `chart`, `dashboard`, `data_source`, `table_name`) |
| List data sources | `method call insights.api.data_sources.get_all_data_sources` |
| Search tables, all sources | `method call insights.api.data_sources.get_data_source_tables` (`search_term`, `limit`; omit `data_source` to search every source) |
| Table columns and types | `method call insights.api.data_sources.get_data_source_table_columns` (`data_source`, `table_name`) → `[{column, label, type}]` |
| Tables with their columns, one source | `method call insights.api.data_sources.get_schema` (`data_source`) — expensive, opens each table, sees 100 tables and takes no `limit` |
| Search all workbook content, with snippets and usage | `method call insights.api.ai.search.search_content` (`term`, `limit`) — newer sites only |
| Search column names, every table | `method call insights.api.ai.search.search_columns` (`term`, `data_source`, `limit`) — newer sites only |
| A query's upstream and downstream | `method call insights.api.ai.lineage.describe_query` (`query`) — newer sites only |
| Table row count | `method call insights.api.data_sources.get_data_source_table_row_count` (`data_source`, `table_name`) |
| Known joins between two tables | `method call insights.api.data_sources.get_table_links` (`data_source`, `left_table`, `right_table`) |
| Stored tables | `method call insights.api.data_store.get_data_store_tables` (`data_source`, `search_term`, `limit`) |
| Every expression function | `method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list` |
| One function's signature and docstring | `method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description` (`funcName`) |
| Check an expression without running it | `method call insights.insights.doctype.insights_data_source_v3.ibis.utils.validate_expression` (`expression`, `column_options`: a JSON list of `{"value": <column>, "description": <type>}`) → `{is_valid, errors: [{line, column, message, hint}]}` |
| Run an unsaved pipeline | `method call insights.api.run_doc_method` (`method`: `execute`; `docs`: the query with a `new-` name, `__islocal: 1`, `workbook`, `is_builder_query: 1`, `use_live_connection` and `operations`; `args`: `page_size`, 10,000 at most, and `import_if_not_exists: false`) → `execute`'s answer. See section 5 |
| Profile one column | `method call profile_column --doctype "Insights Query v3" --name <n> -X GET` (`column_name`, `by`, `limit` up to 1,000, `force`), or `run_doc_method` with `method: profile_column` on an unsaved query. It never imports — newer sites only, those with `verify_workbook` |
| Verify a workbook | `method call insights.api.ai.verify.verify_workbook` (`workbook`, `filters`) — newer sites only, POST only |
| Run a saved query | `method call execute --doctype "Insights Query v3" --name <n> -X GET` (`page_size`: 100 by default, 10,000 at most; `page`; `force` skips the 10-minute result cache; `active_operation_idx` runs operations 0 to that index only) |
| Count a saved query's rows | `method call get_count --doctype "Insights Query v3" --name <n> -X GET` (`active_operation_idx`) → an integer |
| Real values of a column | `method call get_distinct_column_values --doctype "Insights Query v3" --name <n> -X GET` (`column_name`, `search_term`, `limit`: 20 by default, `active_operation_idx`) |
| Smallest and largest value of a column | `method call get_column_range --doctype "Insights Query v3" --name <n> -X GET` (`column_name`, `active_operation_idx`) → `[min, max]`, or null |
| Run a saved chart | `method call insights.api.view.get_chart_data -F chart=<n>` (`dashboard`; `filters`: `{"<filter name>": {"operator", "value"}}`, applied only with `dashboard`; `force`; `page`, past the first only for a reader who may read the chart's rows) |
| Run an unsaved chart config | `method call insights.api.authoring.get_chart_data` (`chart_type`, `query`, `config`, `page_size`) — returns `{"errors": [...]}` for a config it cannot render |
| The rows behind a chart segment | `method call insights.api.view.get_drill_data` (`chart`, `dashboard`, `filters`, `drill_stack`: one level per click, each with `segment_filters` and an `action` of `{"rows": true}` or `{"breakdown": <column>}`; `sort`, `find`, `page`, `row_filters`) |
| Map regions | `method call insights.api.maps.get_available_regions` (`map_type`: `world` or `india`); `find_unresolved_regions` (`map_type`, `user_regions`, `chart_name`); `save_region_mappings` (`chart_name`, `map_type`, `mappings`), which writes `config.region_mappings.<map_type>` |
| Ship a workbook with an app | `method call mark_as_standard --doctype "Insights Workbook" --name <n>` (`module`, `name`) — developer mode, Insights Admin, POST only. See section 8 |
| Create, read, patch, delete content | `doc create` / `doc get` / `doc list` / `doc update` / `doc delete` |
| Run a Script Report | `report run "<report>" --filters-json '<json>'` |
| Import a workbook JSON | `api method/insights.api.workbooks.import_workbook --input <file>` |

`get_distinct_column_values`, `get_count` and `get_column_range` run on a **query document**, not on a table. To ask a raw table, run them on an unsaved query with a `source` pipeline. See "Sample the data" in section 5.

`-F key=value` sends a typed scalar. `-F 'key:=<json>'` sends raw JSON. `--input <file>` sends a whole JSON body, which is what a document and a JSON field patch need.
