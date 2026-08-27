# 08 — Generate the inventory from the test titles

Type: task
Status: resolved
Blocked by: 02, 07

## Question

Make the flow inventory impossible to drift.

Generate `frontend/tests/FLOWS.md` from the Playwright test titles, using the
built-in JSON reporter. Add a CI check that regenerates it and fails if the
committed copy differs — the same shape as a lockfile check.

Then **delete ticket 02's bootstrap inventory.** Two lists of flows is the
failure this ticket exists to prevent. If the bootstrap list holds anything the
generated one does not, that gap is uncovered flows, and it belongs in a ticket
rather than in a document.

## Answer

`frontend/e2e/FLOWS.md` is generated. `inventory-draft.md` is deleted. The suite
covers **50 of 68 flows, or 74%**, which is below the 81% ticket 02 planned.
Three tickets hold the difference.

### The generator

`frontend/e2e/generate-flows.mjs`, wired as two yarn scripts in
`frontend/package.json`:

- `yarn flows` rewrites `frontend/e2e/FLOWS.md`
- `yarn flows:check` exits 1 when the committed file is stale

It runs `playwright test --list --reporter=json`, walks the suite tree, and
groups the titles by `test.describe` block. It is 120 lines of Node with no
dependency beyond Playwright, which the suite already has.

`--list` reads the spec files and runs nothing. No site, no server, no browser.
That is what lets CI check the file on every pull request.

Three decisions inside it:

1. **It sets `E2E_QUARANTINE=1`.** The config drops `@quarantine` tests from a
   normal run, so without this a quarantined flow would silently vanish from the
   inventory. It lists every flow and prints the tag beside the quarantined ones.
2. **It carries no file or line number.** Both churn on any edit above a test,
   which would fail the freshness check for a change that renamed no flow.
   Playwright's reported line numbers are also wrong: it put "a user pivots
   wider" at `query.spec.ts:538` in a file that is 495 lines long.
3. **It excludes the setup project only.** Everything else the suite holds goes
   in, including the three `seeding` tests, which cover the fixture layer rather
   than a user flow. A hardcoded list of areas to skip is the kind of thing that
   drifts, which is what this ticket exists to stop.

The generator lives in `frontend/e2e/`, not in `frontend/scripts/`. The repo's
root `.gitignore` ignores `scripts/`, so a generator there is invisible to git
and the CI check would run against a file nobody could commit.

### The CI check

A second job named `Flow inventory` in `.github/workflows/playwright.yml`. It
checks out, installs Node, runs `yarn install --frozen-lockfile`, and runs
`yarn flows:check`. It skips the bench, the site, the frontend build and
`playwright install`, so it finishes long before the suite it sits beside.

**Proof it fails when stale.** Renamed one test title in `query.spec.ts`, from
`a user pivots wider` to `a user pivots wider and sees one column per payment
type`, changing nothing else:

```
$ node e2e/generate-flows.mjs --check
frontend/e2e/FLOWS.md is stale. Run `yarn flows` and commit the result.
  committed, no longer a test: a user pivots wider
  a test, not committed:       a user pivots wider and sees one column per payment type
exit=1
```

Reverted the title, and the check passed again with exit 0. It also passed clean
before the edit.

### The real coverage number

Ticket 02 drew 69 flows from the routes and the type definitions, before any
test existed, and set the cut at 56 of 69 or 81%. Writing the tests corrected
the list twice.

**Two drafted flows do not exist in the product**, so they leave the
denominator:

- **Q6, a user reorders operations.** Nothing drags in `QueryOperations.vue` and
  `query.ts` has no move function.
- **Q11, a user sets a limit.** The operation exists in `query.types.ts`, but
  `AddOperationPopover.vue` offers no entry for it.

**One flow the draft missed does exist**, and it joins the denominator: `a user
steps back to an earlier operation and the results rewind`. It is the nearest
real behaviour to the reorder the product does not have.

That makes the denominator **69 − 2 + 1 = 68**.

| Area | Flows | Covered | Uncovered |
|---|---|---|---|
| Query | 19 | 15 | Q17, Q18, Q19, Q20 |
| Charts | 15 | 13 | C14, C15 |
| Dashboard | 9 | 8 | D9 |
| Workbook | 10 | 7 | W8, W9, W10 |
| Shared | 3 | 3 | — |
| Data Source and Data Store | 5 | 0 | DS1, DS2, DS3, DS4, DS5 |
| Permissions | 4 | 4 | — |
| Settings | 3 | 0 | ST1, ST2, ST3 |
| **Total** | **68** | **50** | **18** |

**50 of 68 is 73.5%, which rounds to 74%.** Seven points below the bar.

Of the 18 uncovered flows, **12 are tier C that ticket 02 ruled out on purpose**:
Q17 to Q20, C14, D9, W9, W10, DS5, and ST1 to ST3. The other **six are genuine
gaps**, and each is now a ticket:

- DS1 to DS4, in [ticket 19](19-flows-data-source.md). Four flows, one of them
  tier A, that no ticket ever claimed. This is the whole of the shortfall.
- W8, in [ticket 20](20-template-flow-needs-erpnext.md). Blocked, not forgotten.
- C15, in [ticket 21](21-flow-share-a-chart.md). Ticket 10 pointed at ticket 13,
  and ticket 13 covered the guest half only.

Close all three and the suite reaches **56 of 68, or 82%**, which clears the bar.

**Two other numbers, so the 74% is not read as worse than it is.** Against the
54 flows in ticket 02's cut that turned out to exist, the suite delivers 49, or
91%. And `FLOWS.md` lists 53 flow tests against those 50 flows, because ticket
17 split three of them in two to make them deterministic. Neither number is the
one the map asks for. The map asks for 80% of the inventory, and that is 74%.

### Also changed

- `frontend/e2e/AGENTS.md` — the layout block names `FLOWS.md` and the
  generator, and the title rules say to run `yarn flows` after adding, renaming
  or deleting a test.
- `docs/projects/e2e-tests/issues/resolved/02-flow-inventory.md` — an amendment
  records the corrected count and drops the dead link to the deleted draft.
- `docs/projects/e2e-tests/map.md` — the stable-id question is answered. A flow
  is its title, and a rename reads as a delete plus an add. That is enough for a
  freshness check and nothing yet asks for more.

`yarn lint:e2e` reports 0 errors and the 11 pre-existing `no-nth-methods`
warnings.


### Follow-up: the generator was removed

The generator, `frontend/e2e/FLOWS.md` and the `Flow inventory` CI job are gone.
Saqib's test is whether a thing earns the mental space it costs, and this did
not.

`npx playwright test --list` already prints every title, grouped by file. That
is the inventory. Once the committed file goes, the generator only pretty-prints
that command, so it is all three or none.

The decision that built this was right when it was made. The flow list was then
a live artifact: it sharded work across six agents and defined done, and it had
to not drift. That job is finished. From here the question is whether the suite
catches a regression, which it answers by being green or red. A coverage number
was scaffolding.

The CI gate also had a failure mode that earned nothing. Rename a test, and the
build goes red until someone regenerates a file — a red build that teaches
nothing is what erodes trust in a gate.

What stays deleted either way is `inventory-draft.md`. A hand-written list of 69
flows, already wrong in four places, is a liability.
