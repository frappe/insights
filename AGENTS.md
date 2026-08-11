# Insights — agent instructions

Frappe BI app. Backend: Python (Frappe framework) in `insights/`. Frontend: Vue 3 +
frappe-ui in `frontend/src2/`, built with Vite.

## Orientation

- `insights/api/` — whitelisted API endpoints (thin; logic lives in doctype classes)
- `insights/insights/doctype/` — doctypes; the `_v3` suffix on most of them is
  historical, not a variant marker (`Insights Workbook` and a few others have none)
- `insights/workbook_templates/` — shipped workbook templates
  (`insights_workbook_templates` hook, open to other apps)
- `frontend/src2/` — the whole UI, one folder per area (`workbook/`, `query/`,
  `charts/`, `dashboard/`, `data_source/`, `data_store/`)
- `frontend/src2/types/` — the domain types; read `query.types.ts` before touching
  query logic
- Query engine: operations JSON → ibis → SQL, against the source or the DuckDB data
  store (`insights_data_source_v3/data_warehouse.py`, `ibis_utils.py`)
- `CONTEXT.md` — the glossary; use its terms in code, tickets, and commits

## Working here

- Bench: run `bench` commands from the bench root, not from this app directory
- Sites: test against a local development site with Insights installed
- Branches: `develop` is the default branch; pull requests target
  `frappe/insights`
- Frontend dev server: `cd frontend && yarn dev`. Build UI on frappe-ui components
  and semantic tokens (`text-ink-*`, `bg-surface-*`, `border-outline-*`); no raw
  buttons or hardcoded colors
- Run the bench's pre-commit hooks before committing

## Agent skills

### Issue tracker

Markdown under `docs/projects/<effort>/` — a decision map plus one ticket per
question. Effort docs are branch-scoped: they are removed when the branch merges,
and the ADR is what survives. GitHub Issues on `frappe/insights` is the public
queue, not this tracker. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` at the root + `docs/adr/`. See `docs/agents/domain.md`.
