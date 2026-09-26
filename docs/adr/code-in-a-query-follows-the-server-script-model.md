# Code in a query follows the Server Script model

Date: 2026-09-23

## Status

Accepted. Implemented in `insights/insights/doctype/insights_data_source_v3/sandbox.py` and `insights/permissions.py` (`check_trusted_code_author`, `trusted_code_of`).

## Context

A query runs code from three places: a script (a `code` operation), an expression (a calculated column, measure or filter), and a SQL query. Any user who could write a query could write all three. Each ran with Frappe's full Server Script globals: `enqueue`, `frappe.call`, `sendmail`, database writes, commit hooks and the local filesystem. `Insights User` is the app's least privileged role, so that role could run all of this on the server.

Two uses in production need more than a restricted sandbox. Script queries make HTTP requests (log search on insights.frappe.io) and read Frappe data that the reader may not read. `custom_operation` expressions call `q.sql("SELECT …")`, which runs on the connection without the permission checks that a SQL query gets.

## Decision

Code is trusted according to who wrote it, as for a Server Script. There are two kinds of code. One function, `sandbox_globals`, builds the globals for both, with an allow-list for each:

- **Trusted code** is a script, an expression that calls `.sql`, and a SQL query that calls a stored procedure. Only an Insights Admin can add or change it. A script can read Frappe data without permission checks and can make outbound HTTP requests. It cannot use `enqueue`, `frappe.call`, `sendmail`, database writes or commit hooks.
- **An expression** can be written by any user who can write a query. It gets pure helpers (`frappe.utils`, format helpers, `json`, `_`). It reads a document only when the Permission User may read it. It cannot make HTTP requests, call `db.sql` or write. Its source may not name an attribute that reaches a database backend or a file, or that compiles or runs SQL (`assert_expression_has_no_io`).

Trusted code that another user stored keeps running, and a non-admin can still save the document that holds it unchanged. Only a change to it is refused. The check (`check_trusted_code_author`) runs on every path that brings code in: a save, an import, a copy, and a run of content that is not saved yet.

## Consequences

**A non-admin author can no longer edit their own script.** Their stored script keeps running.

**`.sql` in an expression is allowed because production uses it.** Refusing it would break stored `custom_operation` expressions that only read data. An expression that calls `.sql` is trusted code instead.

**A stored procedure names no tables**, so no permission check can apply to it. A call to one is therefore trusted code, whether or not the data source has Enable Stored Procedure Execution checked.
