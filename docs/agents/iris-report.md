# iris — verdict and report

The report format for `/iris-review`, read at phase 3. It lives outside the command so
the format cannot shape the search — length limits change what an agent looks for.

**Looks good** / **Minor nits** / **Concerns**. Score out of 5. Check for a blocker first —
a likely bug that would ship, a guest-reachable data leak, a migration that breaks saved
documents, or state a user can only escape by deleting the object: any blocker → 1.
A bug that already shipped is not a blocker, even when the diff rewrites its lines — the
PR did not cause it and merging makes nothing worse. It becomes one if the PR makes it
worse or easier to hit.

Otherwise: no findings → 5, nits only → 4, one `Concerns` → 3, two or more → 2. Count
distinct causes, not bullets — evidence for one cause is one finding.

**Every finding has three layers. Do not merge them.**

1. **The point, in plain words.** One sentence a reader understands with no context. No
   file paths, no identifiers, no numbers, no API names. If it cannot be said this way,
   you do not understand the finding yet.
2. **Where and what to do.** `path:line`, then the fix in one sentence.
3. **`<details>` — the proof.** Now you may use paths, measurements, call sites and
   upstream reads. This is where facts live.

The reader must be able to stop after layer 1 and still know what is wrong.

- **One fact per sentence, and never in layer 1.** The failure mode is a sentence where
  every clause carries a different fact. Split it, or move the facts down a layer.
- **Visible part is short.** ~4-8 lines for `Concerns`, ~3 for `Minor nits`, 1 for
  `Looks good`. A nit needs no `<details>`.
- Never report `Concerns` without `path:line`, the decision or precedent it breaks, and the
  consequence.
- End a `Concerns` review with one line naming the smaller fix you would rather see.
- **Write the review in STE** — the standard §7 applies to the PR applies to you. One point
  per sentence, max 25 words, active voice, no semicolons, condition before command.
- **Use an example whenever it makes the problem easier to grasp.** A made-up two-line
  before/after is fine and often better than a real one — its job is to explain, not to
  prove. Keep proof and illustration apart: a *claim* about this codebase must be verified,
  an *illustration* need only be clear. Say which it is when it could be read either way.
- Many authors are first-time contributors — "other call sites read this through
  `standard_id`", not "violates the reference-currency invariant".
- Honest confidence ("looks like", "worth checking") is fine, and naming a discomfort
  without a fix is a valid finding — *"i just have some concerns that somethings feels
  'smelly'"*. Say it is a feeling when it is.
- No emoji, no filler. Zero issues → a one-line "Looks good" with what the change does.
  Never manufacture a concern.
- **On re-review, account for the last review first.** One line per earlier finding:
  resolved (name the commit), stands, or settled. Then the new findings, if any. A
  settled finding is out of the score — "Settled: the SSL default, per @<author>" is the
  whole entry, with no re-argument.

Example:

> **Concerns (2/5)** — patches the symptom at every call site, and changes a stored shape
> with no patch.
>
> - **The workbook name is stored as a number but compared as text.** Every caller has to
>   remember to convert it, and this PR adds six more places that must remember.
>   `frontend/src2/query/helpers.ts:212` — drop the `autoincrement` autoname instead.
>   <details><summary>evidence</summary>
>
>   `Insights Workbook` is `autoname: autoincrement`, so `name` is a bigint, and every
>   column referencing it is varchar. The cast appears at 6 sites in this diff
>   (`helpers.ts:212,240`, `workbook.ts:88`, …). An `autoname` method keeps plain numbers,
>   continues the same sequence, and removes all 6.
>   </details>
>
> - **Charts saved before this change will render empty.** A new config key ships with no
>   migration. `insights/insights/doctype/insights_chart_v3/insights_chart_v3.json:88` —
>   add a patch to `insights/patches.txt`.
>
> Suggest: fix the autoname, and keep the cast only where a patch has to run.

> **Looks good (5/5)** — routes the dashboard filter through the existing closure walk
> instead of a second resolver. `insights/tests/test_resolver.py:64` covers the new path. No
> stored shape changed.
