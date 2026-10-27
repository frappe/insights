# Development

How to install, build, lint, commit and push in this repository. Running and writing tests is in `testing.md`.

## Install

- `frontend/package.json` links `@framework/ui` to `../../frappe/ui`, so the frontend installs only with frappe's `ui` at `../frappe/ui`: inside a bench, or in a clone where you put it there, as the lint workflow does.

## Build and lint

- Dev server: `cd frontend && yarn dev`. It cannot host the e2e suite; `frontend/e2e/AGENTS.md` says what can.
- Build: `bench build --app insights` from the bench root builds the frontend and its islands. `cd frontend && yarn build` builds the frontend only.
- Lint: `cd frontend && yarn lint` and `yarn lint:e2e`. CI runs both.

## Commits and hooks

- Commit titles are conventional commits (`feat:`, `fix:`, ...). `commitlint.config.cjs` holds the rules, and the lint workflow checks every commit in a pull request.
- `.pre-commit-config.yaml` holds the hooks CI runs. Install them once in this app's directory with `pre-commit install` and `pre-commit install --hook-type pre-push`.
- Pre-commit runs the file checks, ruff, prettier and `yarn --cwd frontend typecheck:baseline`. Pre-push runs the semgrep rules and `python insights/tests/features.py check`.
- To run the pre-push hooks by hand: `pre-commit run --hook-stage pre-push --from-ref <remote>/develop --to-ref HEAD`, where `<remote>` is your name for the frappe/insights remote.
