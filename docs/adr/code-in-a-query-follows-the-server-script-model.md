# Code in a query follows the Server Script model

Date: 2026-09-23

## Status

Accepted. Implemented in `insights/insights/doctype/insights_data_source_v3/sandbox.py` and `insights/permissions.py` (`check_trusted_code_author`, `trusted_code_of`).

## Context

A query runs code from three places: a script (a `code` operation), an expression (a calculated column, measure or filter), and a SQL query. Any query writer could write each of them, and each ran with frappe's full Server Script globals: `enqueue`, `frappe.call`, `sendmail`, DB writes, commit hooks and the local filesystem. An `Insights User` is the least privileged role the app has, so the least privileged role could run all of it on the server.

Two uses in production pull the other way. Script queries call out over HTTP (log search on insights.frappe.io) and read Frappe data past the reader's permissions. `custom_operation` expressions call `q.sql("SELECT …")`, which runs on the connection without the permission binding a SQL query gets.

## Decision

Code is trusted by who wrote it, as a Server Script is. There are two kinds of code and one sandbox builder (`sandbox_globals`) with an allow-list for each:

- **Trusted code** is a script, an expression that calls `.sql`, and a SQL query that calls a stored procedure. Only an Insights Admin adds or changes it. A script reads Frappe data past permissions and may make outbound HTTP requests. It has no `enqueue`, `frappe.call`, `sendmail`, DB writes or commit hooks.
- **An expression** is written by any query writer. It gets pure helpers (`frappe.utils`, format helpers, `json`, `_`) and reads documents only through the permission user's read permission. No HTTP, no `db.sql`, no writes. Its source may not name an attribute that reaches a backend, a file, or compiles or runs SQL (`assert_expression_has_no_io`).

Trusted code someone else stored keeps running and saving. Only a change to it is refused, on every door: a save, an import, a copy, and a run of unsaved content (`check_trusted_code_author`).

## Consequences

**A non-admin author loses the editor for their own script.** Their stored script keeps running, but they can no longer change it.

**`.sql` in an expression is allowed because production uses it.** Refusing it would break stored `custom_operation` expressions that only read. An expression that calls it is trusted code instead.

**A stored procedure names no tables**, so no permission binding can apply to it. Calling one is therefore trusted code, whether or not the source has stored procedures on.
