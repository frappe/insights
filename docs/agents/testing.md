# Testing

How an agent writes a test during a feature, and how `/iris-review` judges one before merge. Browser flows have their own rules in `frontend/e2e/AGENTS.md`. This file does not repeat them.

## Layers

| Layer | Runner | Files | Owns |
| --- | --- | --- | --- |
| backend | Frappe unittest | `insights/**/test_*.py` | query engine, permissions, derivation of a chart's operations, migrations |
| unit | vitest | `frontend/src2/**/*.test.ts` | the adapter from result to chart props, pure state, helpers |
| e2e | Playwright | `frontend/e2e/tests/<area>.spec.ts` | what only a browser proves |

Run them with `bench --site <site> run-tests --app insights --module <module>`, `cd frontend && yarn test`, and the e2e command in `frontend/e2e/AGENTS.md`.

## The ladder

- Put a test on the lowest layer that can observe the behaviour. The layer is a ladder, not a ratio.
- Ask two questions before you write an e2e case. Does this need a browser? Is there a layer you cannot fake without gutting the test's value? Two "no" answers mean the test goes lower.
- A failure at a high layer with no failure at a low layer means a low-layer test is missing. Write it in the same change.
- A behaviour that is hard to test low is a design signal. Extract the logic; do not escalate the test.

## The regression gate

- A new test names the regression it catches that no existing test catches. Name the bug, the code path and the input. If you cannot, do not write the test.
- Before you add a file, extend or parameterize an existing test. A new file needs a behaviour no existing file is about.
- The PR description justifies every new e2e case: the flow that would break, and why no lower layer would see it.

## E2E shape

- Write few, long flows. A flow does several things and asserts each outcome.
- A case whose only assertion is that something renders or is visible is a unit test filed in the wrong layer. Move it.
- Titles, fixtures, locators and assertions follow `frontend/e2e/AGENTS.md`.

## Names

- The test name is the triage line. It states what a user or the engine does, and it is equivalent to the assertion.
- Write it as a sentence in the present tense, in the words of `CONTEXT.md`. No `should`, no ticket ids, no component names.
- Backend: `test_a_sort_the_author_wrote_outranks_the_date_axis` (`insights/tests/test_chart_derivation.py`).
- Unit: `it('draws a rate as a line over the bars it is read against')` (`frontend/src2/charts/adapter/axis.test.ts`).
- E2E: `test('a user steps back to an earlier operation and the results rewind')` (`frontend/e2e/tests/query.spec.ts`).

## The feature directive

- Every test carries a directive on the line directly above it: `# @feature <slug>` in Python, `// @feature <slug>` in TypeScript. Separate several slugs with spaces.
- A slug is `<area>.<feature>` and is a row in `docs/features.md`, which holds only the slug and the sentence. Which tests pin a row is read off the tests, never written into the list.
- A feature row precedes its first test. To test a new feature, add the row first, then the test.
- `python insights/tests/features.py check` runs in the lint workflow. It fails on a test without a directive, a slug not in the feature list, or a coverage table that does not match the tests.
- `python insights/tests/features.py generate` rewrites `docs/coverage.md`. Run it after you add, rename or move a test, and commit the result.

## Agent rules

Each rule answers a failure someone has recorded; the source is named in brackets.

- Run the test before the fix and confirm it fails; a test that already passes proves nothing (next.js, Grafana, bun, Willison).
- Mock only true boundaries: the network, an external service, the clock. Never mock the code's own helpers; that makes the test a copy of the code (PostHog, supabase, Lightdash).
- Assert the whole outcome, not fields that restate the fixture. A test that compares the output to the input it built is circular (codex, Böckeler).
- Do not test a statically defined value (codex).
- Never delete, skip or weaken a test to make a run green. A red test is a finding; report it (Beck, PostHog).
- The reviewer is not the writer. The agent that wrote the code does not grade its tests; `/iris-review` does (Anthropic).

## Skip and retry

- A `skip` carries an issue link, an owner and an expiry date on the same line. Review checks the date; a skip past its expiry is a finding.
- In e2e, `test.skip` is a lint error. Use the `@quarantine` tag as `frontend/e2e/AGENTS.md` states, and put the same three fields in its comment.
- A retry is a CI allowance, not a fix. `retries: 2` in `playwright.config.ts` absorbs infrastructure noise; it does not license a flaky test.
- Before you land an e2e case, run it with `--repeat-each 3`. Any failure is a real failure.

## The pre-merge pass

Before merge, prune. This pass is part of `/iris-review`; a test that fails it is a finding.

- A test whose failure would not change what a user sees, or what the engine returns.
- A test that pins how the code works rather than what it does: a call sequence, a private helper, a DOM structure, a compiled SQL string in a browser test.
- Two tests across layers that pin one rule. Keep the lower one.
- A test whose name does not match its assertion. Rename or split it.
