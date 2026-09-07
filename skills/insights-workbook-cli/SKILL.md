---
name: insights-workbook-cli
version: 1
description: Create, read, update and delete Frappe Insights v3 workbooks — queries, charts and dashboards — on any stock Insights site through the frappectl CLI. Use when the user asks for an Insights workbook, query, chart or dashboard, or wants an existing one changed, explained or deleted.
---

# Insights workbooks over frappectl

You author workbook content and push it to a live Insights site with `frappectl`. This
file is the procedure. `reference/` is the contract.

This skill needs nothing installed on the site. It calls stock Insights v3 endpoints
only.

## Before you start

The user owns the `frappectl` profile for the site. Check it:

```sh
frappectl -s <profile> auth whoami
```

If the site has no profile, stop and tell the user to make one. Do not run `auth`
commands. Do not set `FRAPPE_*` variables.

Pass `-s <profile>` on every call. The examples write `$SITE` for it.

## The CLI is the only interface

Every action on the site goes through `frappectl`. Never read or write the site's
files, database, logs or bench. This holds even when the site runs on this machine and
those paths sit right there.

A local path is an accident of one developer's setup. What you learn there does not
hold on the site the workbook must run on. A workbook built on it breaks there.

**Assume you do not have the Insights source, because most users do not.** Nothing in this skill
needs it. Every fact about the site is a call: its tables, its columns, its stored data, its
function library. To know whether something exists, ask the site.

### When a call fails and the error names no cause

Insights returns some failures as an exception type and nothing more. An Insights user
is a Website User, so the framework suppresses the traceback. Do not read the site's
code. Take these three steps.

1. Retry the call once. Change only what could matter.
2. Bisect over the API. Shrink the payload until you have the smallest call that still
   fails. Say what that proves.
3. Stop and report to the user. Give the exact command and the exact response.

An error you cannot act on is a site or environment fault, not a payload fault. Your
job is to hand the user a clean reproduction. Only the user can look inside the site.

Run the failing call again with `--debug` before you report it. The flag prints the
request and the server's own messages to stderr. Insights often names its fault there
and nowhere else.

## 1. Read the site before you plan

```sh
frappectl -s $SITE auth whoami
frappectl -s $SITE method call insights.api.data_sources.get_all_data_sources
frappectl -s $SITE method call insights.api.workbooks.get_workbooks
```

You act as the profile's user, and you see what that user sees. If the user names a
workbook that `get_workbooks` does not list, it is a missing share, not a missing
workbook. Insights reports a missing grant as "not found". Ask the user to share it.

### Read the site's version too, not only its data

Sites run different Insights versions, so an endpoint this file names may not be there. Ask before
you depend on one:

```sh
frappectl -s $SITE method search -q <name>
```

**Every procedure here works on a stock site with no newer endpoint.** A newer endpoint does the
same job faster, never a different job. A missing endpoint costs round trips, never a result. If one
is missing, take the plain path and carry on. Do not stop. Do not tell the user their site is behind
unless they ask.

The same holds for a function `get_function_list` does not return: the plan changes, the ask does
not.

### Translate the ask into the site's vocabulary

The user asks in business language. "Support tickets raised by partner sites" names no table and no
column. Most users cannot name one. Only an admin knows what data is where. You must translate the
ask, and this step is the most likely to go wrong.

Work the ladder in order. **The corpus comes before the schema.**

A schema is large and low-signal: hundreds of tables, hundreds of columns each, and no statement of
meaning. It tells you a column exists. It never tells you the column is the right one. The corpus is
small and already correct. Somebody wrote that query, somebody uses it, and its definition survived
contact with the business. On a mature site most of what you need is tribal knowledge in a query,
not a fact you read off a column name.

**1. Name the data sources.** `get_all_data_sources`. Their names are the first map: which system
holds tickets, which holds sites, which holds billing. An ask that spans two of them is normal.

**2. Search the corpus for every business word in the ask.** This is the rung that pays. "Partner",
"active customer", "churned" and "enterprise" are decisions somebody encoded once, in a title, a
`mutate`, a `case_when`, a filter value or a `sql` query. Section 3 has the searches. Run them for
every noun and every qualifier the user used, before you look at a single table.

A hit gives you the calculation *and* the tables it reads, so it settles rungs 3 and 4 at once.

**3. Search table labels for what the corpus did not answer.** If you omit `data_source`,
`get_data_source_tables` searches the whole instance. It matches the table's `label` and its real
name:

```sh
for word in ticket partner site; do
  frappectl -s $SITE method call insights.api.data_sources.get_data_source_tables \
    -F search_term=$word -F limit=50
done
```

Frappe doctype names are business language, so one search per noun cuts hundreds of tables to a
handful.

**4. Read the columns of the few tables that survived.**

```sh
frappectl -s $SITE method call insights.api.data_sources.get_data_source_table_columns \
  -F data_source="Frappe Cloud" -F table_name="tabSite"
```

`get_schema -F data_source=<name>` returns every table with its columns in one call. It opens each
table on the backend unless the site stores its column lists, so it is the most expensive call in
the skill. Use it only when you must search columns rather than tables. Say that you did.

A newer site searches columns directly, across every table the caller may read:

```sh
frappectl -s $SITE method call insights.api.ai.search.search_columns -F term=partner
```

It answers from stored column lists. A table nobody has synced or opened is not in it, so an empty
answer is not proof. Fall back to `get_schema` when the answer matters.

**5. Ask.** What the ladder does not resolve goes in the scope block as a question, with the
candidates you found. Do not guess a definition somebody has already written down.

### Say what you leaned on

Discovery makes choices and the user sees none of them. Name every one, in the scope block and again
in the closing summary. One line each:

- **Reused a definition.** The workbook, the query, and the expression you copied. If the user's ask
  differs from it, say how and ask.
- **Derived a definition yourself.** Say that you found no existing one. Name the columns you built
  it from. Ask the user to confirm it. **This line matters most.** The people who use a reused
  definition checked it. Nobody checked the one you derived.
- **Picked one candidate over others.** Name what you rejected, and why. A search that returned three
  tables and a search that returned one are different situations. Only you can see which happened.
- **Made a load-bearing cut.** A date the data starts, a filter that drops rows, a source you chose
  because a table was not stored. Each one changes the number.

Silence here reads as certainty. Do not spend certainty you do not have.

### A query spanning two data sources needs the data store

One flag decides cross-source. With `use_live_connection: 0` every table resolves through the
warehouse, whatever its data source, so tables from two sources join normally. With
`use_live_connection: 1` each table opens on its own backend, and a join across two of them cannot
run.

So an ask that spans two systems is a data store query, and every table it needs must be stored.
See "Choose the data store or the live connection" in section 5.

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

Plan only with the operation types, chart types and functions these files list. Never
invent one.

The site is the authority on the function library. It is one call away:

```sh
frappectl -s $SITE method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list
frappectl -s $SITE method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description \
  -F funcName=json_value
```

`get_function_description` returns the signature and the docstring. The docstring says what the
function does. Read it before you use a function these files do not cover. Read it before you trust
one they describe in a line. The parameter is `funcName`, in camelCase. `function` gives nothing
back.

For worked examples, read what the site already has (section 3). A workbook the site imported from a
template is a good one: `doc list "Insights Workbook" --fields name,title,from_template --all`.

## 3. Reuse what the user already has

People share workbooks. A metric somebody already defined and uses every day is more
likely correct than one you derive from column names. **Run these searches before you read the
schema.**

Open a `sql` query even though you must not author one. Definitions nobody could express in builder
operations end up there, so those queries hold the densest tribal knowledge on the site. Read the
SQL, take the calculation, and rebuild it as builder operations.

**Search the corpus. Do not download it.** Titles and the JSON fields are text columns, so the site
greps them for you. A `like` filter is the whole search.

**Search titles first.** A person wrote them, in the same business language the user uses. These
searches translate "partner" into a real definition:

```sh
frappectl -s $SITE method call insights.api.workbooks.get_workbooks -F search_term=partner
frappectl -s $SITE doc list "Insights Query v3" \
  --filters-json '{"title":["like","%partner%"]}' --fields name,title,workbook --all
frappectl -s $SITE doc list "Insights Chart v3" \
  --filters-json '{"title":["like","%partner%"]}' --fields name,title,workbook,chart_type --all
```

`get_workbooks` searches titles only, so run the query and chart searches too. A workbook titled
"Cloud Metrics" can hold the partner definition.

These searches work on every site. A newer site carries one endpoint that runs them all in a single
call. Probe for it once. Use it when it is there:

```sh
frappectl -s $SITE method search -q search_content
frappectl -s $SITE method call insights.api.ai.search.search_content -F term=partner -F limit=20
```

A hit names `doctype`, `name`, `title`, `workbook`, `workbook_title`, `matched_field` and a
`snippet` of the text around the match. The snippet is the reason to prefer it. You can tell a real
definition from a coincidence without fetching the document.

**A hit also carries `used_by_charts`, `used_by_dashboards` and `dashboard_views`.** Read them.
Three queries can define "partner" three ways. The one behind a dashboard forty people open every
week is the definition the organisation runs on. An orphan query somebody made once is not. Prefer
the used one, and say in the scope block how much it is used.

Without the endpoint you get the same documents, in more calls, with no snippet and no usage count.
The searches do not change. Rank by hand instead, and say you did.

**Then search the JSON.** It reaches column names, expression text, filter values and measure names.
A definition lives there even when no title says so:

```sh
frappectl -s $SITE doc list "Insights Query v3" \
  --filters-json '{"operations":["like","%partner%"]}' --fields name,title,workbook --all

frappectl -s $SITE doc list "Insights Chart v3" \
  --filters-json '{"config":["like","%base_net_total%"]}' --fields name,title,workbook,chart_type --all
```

Search one word at a time. Search the words the *user* used before the words the schema uses.
`like` matches a substring and nothing else. It has no synonyms and no stemming, so "partner" finds
"is_partner" and "Partner Sites". "partner persona" finds neither.

Each search returns a shortlist of names. Then `doc get` the two or three worth reading.

The unfiltered form `doc list "Insights Query v3" --fields name,title,workbook,operations --all`
pulls every readable query's whole pipeline. It is fine on a site with six workbooks and useless on
a site with six hundred. Search first. Fetch what the search names.

Both are permission filtered, so what comes back is what the user can read. Look for a
query over the same tables. Read its `operations` for the calculation: the expression,
the aggregation, the filter group that defines "revenue" or "active customer" here.

**Copy the calculation into your own query. Do not reference the other workbook's
query.** A cross-workbook query reference builds and runs, but the workbook's source
selector lists only queries in its own workbook, so the user cannot see or edit where
the data came from.

Say what you reused. See "Say what you leaned on" in section 1.

## 4. Converge on scope with the user

Before you author anything, post a scope block. It states:

- the target workbook, by name
- the tables to draw from, and the grain of each query
- every metric, with the exact columns it computes from
- any definition you reused, and where it came from
- the dimensions and the filters
- what the user is actually looking at, so the dashboard leads with it

When more than one column could serve a metric, name the candidates and ask which one.
Never resolve that ambiguity alone. Never carry an unasked choice into the closing
summary.

Ask before you sample real values from a column. Wait for the answer. A sample needs a scratch
query, so it is a write. See section 5.

**Stop here.** Post the scope block, end your turn, and wait for the user's reply.
Agree the scope with the user, not with yourself.

## 5. Author

### Never create a workbook the user did not ask for

The default is to add to a workbook that exists. "Add a chart", "fix this query" and
"put a filter on the dashboard" all create documents inside the named workbook. None of
them creates a workbook.

Create a workbook only when the user asks for one in those words. When the target
workbook is unclear, ask which one. Do not resolve it by making a new one.

Ask before you create a workbook when:

- the user names no workbook and more than one could fit
- the work would fit an existing workbook you can see
- you recover from a failed attempt. Patch or delete what you made. Never leave a
  second copy

### Write through a build script

Every write goes through one Python script you author for the task. Reading and
exploring stay direct `frappectl` calls.

The reason is verification. The checks in section 6 are list comparisons. An agent that
compares lists by hand reports a verdict nobody can audit. In a script the result is an
exit code.

Copy `examples/build_workbook.py` and edit it. It is a template, not a library. You own
every line. `frappectl` prints clean JSON when piped, so the whole client is:

```python
import json, subprocess

def call(*args):
    p = subprocess.run(["frappectl", "-s", SITE, *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"{' '.join(args)}\n{p.stderr}")
    return json.loads(p.stdout) if p.stdout.strip() else None
```

Keep the script a build tool. One file, standard library only, no abstraction the
workbook did not ask for.

### Sample with a scratch query

There is no endpoint that reads the real values of a raw table column. The only sampler,
`get_distinct_column_values`, runs on a query document.

So make one. Create a query in the target workbook, titled `Scratch — <what you are asking>`, whose
pipeline is the source table and nothing else. Then ask it:

```sh
frappectl -s $SITE method call get_distinct_column_values \
  --doctype "Insights Query v3" --name <scratch> -F column_name=status -F limit=20
```

The same query answers any question you can express as a pipeline. Rewrite its `operations`,
`execute` it, read the rows, rewrite again. That is how you count a value, check a date range, or
reproduce a chart's aggregation without touching a real query.

Two rules:

- **One scratch query per session.** Reuse it. Do not leave a trail.
- **Delete it before you report.** A `Scratch —` query left in the workbook is your working paper in
  the user's workbook. `doc delete "Insights Query v3" <scratch>`.

`examples/build_workbook.py` ships this as `scratch()`, `probe()`, `distinct_values()` and
`drop_scratch()`. Its verify step fails when a `Scratch` query is still in the workbook.

### Create the documents

Queries, charts and dashboards are plain documents. Each requires exactly one field:
`workbook`. Permission follows the workbook. Write on the workbook is write on its
contents.

Create them in dependency order, and keep the name the site returns for each:

1. **Queries.** Set `workbook`, `title`, `operations`, and the builder flags from
   `reference/rules.md`.
2. **Charts.** Set `workbook`, `title`, `query` (the query's real document name),
   `chart_type` and `config`. The chart creates its own empty `data_query` on save.
3. **Dashboards.** Set `workbook`, `title` and `items`. Chart items name the chart's
   real document name. Filter links name the real query name. Author `chart` and `filter`
   items only. Never a `text` item.

**Write a whole `items` array exactly once, at creation.** After that the user owns the layout. They
move charts, resize them and add filters, and all of it lives in the same array. A second run that
writes the array your script computed destroys those edits without a word. Every later change is a
merge into the live `items`. `reference/dashboards.md` gives the merge.
`examples/build_workbook.py` ships it as `patch_dashboard()`.

So a build script must not rebuild the dashboard to add one chart. Add the chart. Merge one item.

```sh
frappectl -s $SITE doc create "Insights Query v3" --input /tmp/query.json
```

You use real document names throughout, so a reference either resolves or fails
loudly. There is no name remapping. Nothing drops silently.

### Choose the data store or the live connection

A query reads from the data store when `use_live_connection: 0`, and from the source
database when it is `1`. The flag is per query. Every table in one query resolves the
same way. You cannot mix.

Prefer the data store. It returns faster. A table you query gets stored, so the next
run is faster still.

Check what is stored before you choose:

```sh
frappectl -s $SITE method call insights.api.data_store.get_data_store_tables \
  -F data_source="Site DB" -F limit=200
```

If most of the tables your query needs are stored, set `use_live_connection: 0` and
take the rest with them.

**The first run then returns zero rows. This is the one case where an empty result is a
failure.** A table that is not stored yet does not fail the query. Insights
enqueues the import and substitutes an empty table with the right schema. So:

1. Before you set `use_live_connection: 0`, list which of your tables are missing from
   `get_data_store_tables`.
2. If any is missing, tell the user. The import is queued, and the workbook reads empty
   until it finishes.
3. Run verify check 1 again after the import. Zero rows from a table you know is not
   stored yet is an unfinished import, not a result.

Two limits to read before you trust a stored table for a question about history:

```sh
frappectl -s $SITE doc get "Insights Table v3" <name>
```

`row_limit` caps the stored copy and keeps the **newest** rows. `sync_from` cuts off
everything before a date. A stored table is often a recent window, not the whole table.
When the ask needs more history than the window holds, use `use_live_connection: 1` and
say why.

## 6. Verify

Verification is your compile step. Never call work finished before it verifies clean.
Run these checks from the build script.

### Check 1 — every query builds and runs

```sh
frappectl -s $SITE method call execute \
  --doctype "Insights Query v3" --name <query_name> -F page_size=5
```

- The response carries `sql`, `columns`, `rows` and `time_taken`. All four together
  mean the query compiled and ran.
- A failure here is often opaque. Run it again with `--debug` and read the server
  messages.
- An empty `rows` is not a failure by itself. It **is** a failure on a data store query
  whose tables are not all stored yet. Compare the query's tables against
  `get_data_store_tables` and decide. Do not warn and pass. See section 5. Always say
  the row count. Never accept zero silently.
- `page_size=5` is enough. You check that the query runs, not what the data says.

### Check 2 — every chart's columns exist

A chart has no result of its own until the UI opens it. `data_query` is empty at
creation, so executing it proves nothing.

Verify a chart against its base query:

1. Take `columns` from check 1 for the chart's `query`.
2. Read every column name the chart's `config` names: dimensions, measures and chart
   filters.
3. Every one must appear in `columns`. Report any that does not, and name the columns
   the query does have.

A count measure and an expression measure name no column. Skip them.

Then check the sort. `order_by` names are **post-aggregation** names, so they must match
what the chart's aggregation produces: a measure by its `measure_name`, a dimension by
its `dimension_name or column_name`. Insights drops a sort the chart cannot resolve, and
the chart renders in an arbitrary order. A ranking or a time series then reads as wrong
data. Skip this on a `Table` with non-empty `columns`, which makes its column names out
of the data.

This proves the column exists. It does not prove it is the right column, or that the
number is right. Check 4 does that.

### Check 3 — every dashboard reference resolves

For each item in `items`:

- a `chart` item names a chart document that exists in this workbook
- a `filter` item's `links` name charts that exist, and each link's query segment names
  a query whose `columns` from check 1 contain the column
- **that query is in the linked chart's chain**: its base query, or a query the base
  query reads from. Insights appends the filter to the query it names. A link to a query
  the chart does not read from passes every other check and does nothing.
- every item has a `layout` with an `i`, and no two share it. The grid sums
  `layout.y + layout.h` over every item, so one item without a layout breaks the whole
  dashboard.

### Check 4 — the numbers are right, not just the columns

Checks 1 to 3 prove the workbook compiles. They do not prove it says anything true. Two wrong charts
shipped through a clean run of checks 1 to 3. Only a reproduction of the numbers caught them.

For every chart, build its aggregation in the scratch query: the same dimensions, the same measures,
the same filters. Read the rows. Then look at four things.

1. **Does the number match the chart's own claim?** An average over a group is the classic trap: a
   count of distinct dates divided by a site count is not the average days per site. Compute the
   measure a second way and compare.
2. **How many values does each dimension have?** Count it with `summarize` and `count_distinct` in
   the scratch query. One value is not a split at all. The column does not carry what you assumed,
   and the split lives on another column. Hundreds of values is the wrong chart type. "Making it
   readable" in `charts.md` maps the count to the chart.
3. **Is the signal present across the whole range?** Group the measure by month and read the series.
   A signal that starts partway through is not growth. It is the date somebody first recorded it. A
   signal that stops is retired, not fallen. Both read as a trend and are not one.
4. **Is the last period complete?** The newest bucket is usually a partial day, week or month, and
   it always draws as a fall. Confirm the maximum timestamp in the data before you call a drop real.

Report the row counts and the headline numbers in your reply. Any date cut, any retired signal, any
gap in the data goes in the reply too. Do not put it in a dashboard text item or a chart title.

When a check fails, fix the chart. Do not describe the fault and leave it.

## 7. Read, update and delete

Read a whole workbook:

```sh
frappectl -s $SITE doc get "Insights Workbook" <name>
frappectl -s $SITE doc list "Insights Query v3"     -f workbook=<name> --fields name,title,operations --all
frappectl -s $SITE doc list "Insights Chart v3"     -f workbook=<name> --fields name,title,query,chart_type,config --all
frappectl -s $SITE doc list "Insights Dashboard v3" -f workbook=<name> --fields name,title,items --all
```

Update one JSON field. Write the new value to a file and pass `--input`:

```sh
frappectl -s $SITE doc update "Insights Query v3" <name> --input /tmp/patch.json
```

The JSON field per doctype is `operations` on `Insights Query v3`, `config` on
`Insights Chart v3`, and `items` on `Insights Dashboard v3`.

Change only the field you mean to change. Preserve everything else. `doc update` fails
on a concurrent edit. That is correct behaviour, so read the error before you reach for
`--force`.

`--force` is not the answer to a dashboard you are about to overwrite either. The check compares
`modified`. You read the document a moment before you write it, so the check passes. It guards
against an edit made *during* your write, not against one made since your last run. Only the merge in
`reference/dashboards.md` protects the user's edits.

Delete:

```sh
frappectl -s $SITE doc delete "Insights Chart v3" <name>
frappectl -s $SITE doc delete "Insights Workbook" <name>
```

Deleting a workbook deletes its queries, charts, dashboards and folders. Confirm with
the user before you delete anything you did not create in this session.

Verify again after any edit.

## Appendix — importing a workbook JSON

Use this only when the user hands you a workbook JSON to import: a template, or an
export from another site. It is not the authoring path.

```sh
frappectl -s $SITE api method/insights.api.workbooks.import_workbook --input /tmp/wb.json
```

The file holds `{"workbook": <envelope>}`. `reference/workbook-format.md` describes the
envelope and its name remapping.

**Import creates a new workbook on every call**, so it cannot add to an existing one.
It returns the new workbook name and a `names` map from your internal names to the
real document names.

The importer drops a reference it cannot resolve, and reports nothing. Run the section 6
checks after any import.

## Commands

Confirmed against the Insights `develop` code. Do not assume anything outside this list
exists.

| Purpose | Command |
|---|---|
| Who am I, and on which site | `auth whoami` |
| List workbooks | `method call insights.api.workbooks.get_workbooks` (`search_term`, `limit`, `scope`) |
| List data sources | `method call insights.api.data_sources.get_all_data_sources` |
| Search tables, all sources | `method call insights.api.data_sources.get_data_source_tables` (`search_term`, `limit`; omit `data_source` to search every source) |
| Table columns and types | `method call insights.api.data_sources.get_data_source_table_columns` (`data_source`, `table_name`) |
| Tables with their columns, one source | `method call insights.api.data_sources.get_schema` (`data_source`) — expensive, opens each table, sees 100 tables and takes no `limit` |
| Search all workbook content, with snippets and usage | `method call insights.api.ai.search.search_content` (`term`, `limit`) — newer sites only |
| Search column names, every table | `method call insights.api.ai.search.search_columns` (`term`, `data_source`, `limit`) — newer sites only |
| Table row count | `method call insights.api.data_sources.get_data_source_table_row_count` (`data_source`, `table_name`) |
| Real values of a column | `method call get_distinct_column_values --doctype "Insights Query v3" --name <n>` (`column_name`, `search_term`, `limit`, `active_operation_idx`) |
| Known joins between two tables | `method call insights.api.data_sources.get_table_links` (`data_source`, `left_table`, `right_table`) |
| Stored tables | `method call insights.api.data_store.get_data_store_tables` (`data_source`, `search_term`, `limit`) |
| Every expression function | `method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list` |
| One function's signature and docstring | `method call insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description` (`funcName`) |
| Run a saved query | `method call execute --doctype "Insights Query v3" --name <n> -F page_size=5` |
| Create, read, patch, delete content | `doc create` / `doc get` / `doc list` / `doc update` / `doc delete` |
| Import a workbook JSON | `api method/insights.api.workbooks.import_workbook --input <file>` |

`get_distinct_column_values` returns at most 20 values, and it runs on a **query document**, not
on a table. There is no endpoint that samples a raw table. Build a scratch query first. See
"Sample with a scratch query" in section 5.

`-F key=value` sends a typed scalar. `-F 'key:=<json>'` sends raw JSON. `--input <file>`
sends a whole JSON body, which is what a document and a JSON field patch need.
