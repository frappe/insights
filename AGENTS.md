# Insights — agent instructions

Frappe BI app. Backend: Python (Frappe framework) in `insights/`. Frontend: Vue 3 +
frappe-ui in `frontend/src2/`, built with Vite.

## Orientation

- `insights/api/` — whitelisted API endpoints (thin; logic lives in doctype classes).
  Most use `@insights_whitelist()` in `insights/decorators.py`; it adds a role check
- `insights/insights/doctype/` — doctypes; the `_v3` suffix on the core ones (query,
  chart, dashboard, data source, table) is historical, not a variant marker. Others,
  such as `Insights Workbook` and `Insights Team`, have none
- `frontend/src2/` — the whole UI, one folder per area (`workbook/`, `query/`,
  `charts/`, `dashboard/`, `data_source/`, `data_store/`)
- `frontend/src2/types/` — the domain types
- Query engine: operations JSON → ibis → SQL, against the source or the DuckDB data
  store (`insights_data_source_v3/data_warehouse.py`, `ibis_utils.py`)
- `skills/` — product skills for agents that use a live Insights site; not rules for
  working here. A change to what a whitelisted method returns is a change to them
- `CONTEXT.md` — the glossary; use its terms in code, tickets, and commits

## Conventions

- Run `bench` commands from the bench root, not from this app directory
- `develop` is the default branch; pull requests target `frappe/insights`
- Build UI on frappe-ui components and semantic tokens (`text-ink-*`, `bg-surface-*`,
  `border-outline-*`); no raw buttons or hardcoded colors. When frappe-ui has no
  component for it, build one that matches the taste of its frappe-ui neighbors
- Every test names a row of `docs/features.md` in a `@feature` directive;
  `docs/coverage.md` is generated from them, and CI fails when it does not match
- Issues are GitHub Issues on `frappe/insights`; don't create or triage them unasked

## Before you start

- Before you touch query logic, read `frontend/src2/types/query.types.ts`
- Before you install, build, lint, run the dev server, commit or push, read
  `docs/agents/development.md`: the frontend needs frappe's `ui` beside this app
- Before you write or run a test, read `docs/agents/testing.md`: the site needs
  `allow_tests`, and tests write data, so use a site you can throw away
- Before you write a browser test, also read `frontend/e2e/AGENTS.md`
- Before you change an area, read its ADRs in `docs/adr/`; before you name a concept or
  record a decision, read `docs/agents/domain.md`
- Before you review a change, read the criteria in `docs/agents/code-review/`, which
  `/iris-code-review` uses; skip what `insights.md` lists under "Do not flag"
