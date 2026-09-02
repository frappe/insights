# Source column defaults

Type: task
Status: ready-for-agent

## Question

A query on a doctype arrives with every framework column — `name`, `owner`,
`creation`, `modified_by`, `_assign`, `_comments`, `_user_tags`, `docstatus`,
`idx`. An author who wants four columns prunes by hand, every time.

This is independent of the rest of the effort. It was found while reading the
target join in `overview_board.py`, where the pruning `select` turned out to be
cleaning up the *left* source, not the join.

## What to build

The builder writes an explicit column list when it creates a source step. The
list holds the doctype's own fields; meta columns are available and unchecked.

**Prune at authoring, never in the engine.** `get_column` throws hard when a
column is absent (`ibis_utils.py:220`), and it already carries four fallback
strategies from past column renames — a pruned column has no fallback available,
because it genuinely is not there. A saved query that filters on `_assign`
would break with no migration possible.

Recording the list in the query document is what makes this safe: documents
written before this ticket carry no list and behave exactly as they do today.
The author can see the list and add a meta column back.

## Done when

- A new query on a doctype opens with the doctype's fields and no meta columns.
- Meta columns are one click away, and adding one back works.
- Every existing saved query returns the same columns it returns today. This is
  the acceptance test that matters.
- `test_insights_table_v3.py`'s `_assign` regression tests still pass. They exist
  because permission filtering once dropped `_assign` silently, and people filter
  on it.

## Notes

Judge this ticket on its own. Once ticket 04 lands, the target table is never
the left source of a query, so this saves nothing on the KPI card that motivated
the effort. Its payoff is every other doctype query in the product.
