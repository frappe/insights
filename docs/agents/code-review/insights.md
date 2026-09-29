# Code review: Insights

Insights' own rules for the playbook: what is must fix, what not to flag, and the checks for Insights, by playbook part.

## Must fix

A finding is must fix when it meets one of these rules:

1. Security: anyone, guest or signed in, reads or changes data their permissions do not grant. A guest read of user data, or any write into a customer's source database, is always must fix.
2. Data loss: a save, migration or patch drops or wrongly rewrites stored content.
3. Wrong value: a chart, card, drill or table shows a value the query did not compute, with no error. An unchecked assumption whose failure gives wrong data with no error is must fix too.
4. Broken main path: an author cannot build, save or view a chart or dashboard, or a reader cannot open a shared or public one.
5. Regression: what worked on the base fails for a common configuration.
6. Trapped: a state the user can leave only by deleting the object.

Every other defect is minor. Load on the customer's live source database is the cost that counts.

## Do not flag

The maintainer has asked for these to stop. Raising them costs trust.

- Browser or end-to-end evidence, or screenshots.
- A short PR description or a commit with no body. Long prose is the defect.
- Comments, docstrings or headers on code that explains itself, or more documentation. Concise beats complete.
- A missing ADR, ticket or effort doc on a small or still-changing change.
- New options, polish and edge cases on a feature that has not shipped, or a measurement to settle a matter of taste before its first release.
- Migrations, compatibility code or capacity plans for work with no users yet, on an exploratory branch or an unreleased feature. Shipped v3 behaviour needs them.
- A missing control that the base never had. A control that the base or every similar surface has, going missing, is a regression.
- One extra query per request. A query per row, per keystroke or per chart in a dashboard load is a finding.
- An optimisation that costs readability, unless it removes one of those queries.
- Hardening beyond comparable framework APIs for an accepted exposure. Must-fix rule 1 still applies.
- A check that an earlier layer already makes, such as role permissions before a controller hook.
- On a feature branch, a dependency on an open branch or a planned framework change. Name it, but do not block.
- Commit tidiness or commit messages on a branch whose history will be split or rewritten before merge. The conventional commit prefix, because `commitlint` checks it in CI.
- The glossary's documented pairs of names (grain and `granularity`, Library and `gallery`). They do not allow a new label that differs from its identifier.
- A frappe-ui component marked experimental.
- An example in a doc, for being invented.
- What a linter catches, generated files, rewrites for taste, and any finding with no `file:line` or no effect on behaviour.

## Size

Count reviewable source only. Leave out lock files, `insights/locale/**` and generated files.

## Users

- Read `CONTEXT.md`, `AGENTS.md` and the `docs/adr/` records for the changed area before you judge, so the review argues from recorded decisions.
- When `docs/projects/<effort>/` matches the branch, read its map and the tickets the PR says it resolves, so scope is judged against stated intent.

## Layer

- Logic lives in the doctype controller. API handlers and the client stay thin.

## Design

- New code, labels and docs use the `CONTEXT.md` term for a concept, never a word it retires under `_Avoid_`, and never a new synonym.
- A diff that goes against an ADR names its slug, and says whether it is worth reopening.

## Scope

- A change to a stored field or a stored JSON format (`config`, `operations`, `items`) ships a patch in `insights/patches.txt`, so no user edits their own data.
- A patch changes only its own rows, and keeps `creation` and `modified`.
- A v3 change says what happens to saved documents, and to browsers still on the old bundle.
- A stored field renamed or made required on `develop` is checked against the code that writes it on `version-3-hotfix`.
- A frontend fix that needs frappe-ui behaviour newer than the version in `frontend/package.json` moves that version in the same change.

## Verify

The main path is build, save, view and share, for each kind of chart, dashboard or query the change touches.

Tests are judged by `docs/agents/testing.md`, including its pre-merge prune. A guard for UI state is `yarn typecheck:baseline` plus a test at the lowest layer the testing guide allows.

Security. `allow_guest=True` under `insights/` marks the guest endpoints.

- Code reachable from a guest endpoint, a new whitelisted method, `ignore_permissions=True` or a wider visibility level names the check that protects it.
- A whitelisted method that writes sets `methods=["POST"]`, as `frappe.client` does. Frappe allows GET by default and checks the CSRF token only on POST, PUT, DELETE and PATCH.
- An existing document's stored fields are read from the database, not from the request body.
- User input that reaches raw SQL or the expression sandbox is checked for escaping and for the sandbox's limits.
- `v-html` never renders HTML that a user controls.
- A request to a URL a user chooses follows `docs/adr/outbound-http-to-user-chosen-urls.md`.
- A connection error shown to the user never includes the credential or the connection string.
- A new engine or backend keeps every protection the existing one has.

Values.

- A date filter, time grain or comparison says which time zone it uses and where its boundaries fall: midnight, the first day of the week, and a datetime compared with a date. *Only `between` was padded to the whole day, so `equals` a date matched nothing on a datetime column.*
- A value keeps its type and its null from the source database to the screen. Check numbers stored as text, decimals, large integers, and null against zero or empty. *Rows with no split value went to a column named `"null"` and disappeared from the chart.*

Errors and states.

- An error message names its case and fits every path that raises it.
- One bad item fails alone, and never takes down the page or the list.
- An error state stays inside its component's space.
- Empty states and container sizing are part of the feature.

UI.

- New UI follows the control and layout style of the surface it sits on.
- Colours use frappe-ui semantic tokens (`text-ink-*`, `bg-surface-*`, `border-outline-*`), so dark mode works. Icons come from Lucide.
- Surfaces are flat: only a floating layer gets a shadow, and never a shadow with a border. Spacing and type separate content before borders do, but regions never run together.
- A view has at most one primary button. Controls stay neutral: no coloured buttons, no uppercase labels, no banner that outweighs the content.
- An optional part of a component adds to its layout and never moves the rest. Similar items in a group get the same treatment.
- A control the change adds is visible without hover, and a disabled one says what enables it.
- Every piece of text on screen is needed: no repeated titles, no explainer copy, no em dashes and no internal words. A label says exactly what its click does.
- Strings the change adds go through `__()`. Strings it does not touch are not audited.
- Numbers and dates on screen use the user's locale and the site's formats, never the browser default or a fixed pattern.
- Misalignment, a mismatched type scale, uneven spacing, wrapping labels and clipped focus rings are minor defects. Report them.

## Finish

- A lasting, settled decision gets an ADR, and a small or still-changing one does not. Either miss is minor.
- A term that a new ADR introduces goes into `CONTEXT.md` in the same PR.
