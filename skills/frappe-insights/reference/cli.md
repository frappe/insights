# frappectl

Read this when you reach the site through `frappectl` from a shell. `SKILL.md` names each call as a method or a document read or write. This page maps them to commands, and adds the build script.

## The profile

The user owns the `frappectl` profile for the site. Check it:

```sh
frappectl -s <profile> auth whoami
```

If the site has no profile, stop and tell the user to make one. Do not run `auth` commands. Do not set `FRAPPE_*` variables.

Pass `-s <profile>` on every call. The examples write `$SITE` for it.

To shorten the command, define a shell function: `fc() { frappectl -s <profile> "$@"; }`. Do not put the command in a variable. zsh does not split `$S` into words, so `S="frappectl -s x"; $S ...` fails.

`frappectl` prints a deprecation warning from `authlib` on stderr. It is noise. Parse stdout only, and never merge stderr into it (`2>&1`), or the JSON does not parse.

## Calls

| `SKILL.md` says | Command |
|---|---|
| call `<method>` with `{"a": 1}` | `frappectl -s $SITE method call <method> -F a=1` |
| a JSON argument | `-F 'filters:={"Company": {"operator": "=", "value": "Acme"}}'` |
| list documents with filters | `frappectl -s $SITE doc list "Insights Query v3" --filters-json '{"workbook":"<name>"}' --fields name,title --all` |
| read a document | `frappectl -s $SITE doc get "Insights Query v3" <name>` |
| create a document | `frappectl -s $SITE doc create "Insights Query v3" --input /tmp/query.json` |
| update a document | `frappectl -s $SITE doc update "Insights Query v3" <name> --input /tmp/patch.json` |
| delete a document | `frappectl -s $SITE doc delete "Insights Chart v3" <name>` |
| call a document's method | `frappectl -s $SITE method call <method> --doctype "Insights Workbook" --name <name> -F a=1` |
| run a Script Report | `frappectl -s $SITE report run "Gross Profit" --filters-json '<json>'` |
| import a workbook JSON | `frappectl -s $SITE api method/insights.api.workbooks.import_workbook --input /tmp/wb.json` |

`-F key=value` sends a typed scalar. `-F 'key:=<json>'` sends raw JSON. `--input <file>` sends a whole JSON body, which is what a document and a JSON field patch need. `--input -` does not read stdin. Pipe the JSON on stdin instead.

**Put every filter in one `--filters-json`, `workbook` with it.** `--filters-json` replaces every `-f` on the same command, it does not add to them. A list that pairs `-f workbook=<name>` with `--filters-json` returns documents of every workbook, and a patch loop over that list edits other users' queries.

**Send a query document method as GET.** `frappectl` sends POST by default, and a document method sent as POST needs write on the document. So `-X GET` on `profile_column`, `execute`, `get_count`, `get_distinct_column_values` and `get_column_range` lets them run on a query you may only read. `run_doc_method` checks read itself, so either works. A read-only profile sends every call as GET, and every sample works there. An older site refuses `args` in a GET to `run_doc_method`. There, use a profile that may POST. `verify_workbook` is POST only, so a read-only profile cannot call it.

```sh
frappectl -s $SITE method call execute --doctype "Insights Query v3" --name <query> -X GET -F page_size=5
```

Do not use `method search`. It returns no results even for a method that exists. Probe a method by calling it, as section 1 of `SKILL.md` says.

`doc update` fails on a concurrent edit. That is correct behaviour, so read the error before you reach for `--force`. `--force` is not the answer to a dashboard you are about to overwrite either. The check compares `modified`. You read the document a moment before you write it, so the check passes. It guards against an edit made *during* your write, not against one made since your last run. Only the merge in `reference/dashboards.md` protects the user's edits.

Before you report a failure whose error names no cause, run the call again with `--debug`. It prints the request and the server's own messages to stderr, and Insights often names its fault only there. On an older site that answers only the exception type, `--debug` shows the cause.

## Write through a build script

Every write goes through a Python script. Reading and exploring stay direct `frappectl` calls.

The reason is verification. The checks in section 6 of `SKILL.md` are list comparisons. An agent that compares lists by hand reports a verdict nobody can audit. In a script the result is an exit code.

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

Run the copy with `--site` and `--workbook`. `--verify` skips the build. `--redesign` replaces a dashboard's `items` whole, for a redesign the user asked for, and only while the live `items` still equal what the build last wrote. `Build.upsert` merges a dashboard's `items` on its own.

The script also holds the client (`call`, `method`, `get_doc`, `list_docs`), the probes (`run`, `profile`), the dashboard merge (`patch_dashboard`) and the verify. Use them. Do not write them again. `run()` adds `truncated`, and both probes raise `TableNotStored`. On a site without `profile_column`, `profile()` builds the same answer from `summarize` runs. `verify()` calls `verify_workbook` where the site has it and the profile may POST, and runs checks 1 to 3 itself otherwise.
