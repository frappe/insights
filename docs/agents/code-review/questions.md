# Code review: planning a review, and reading by question

One reader covers about 25 changed files. Past that, a single reader reads a different part of the change each round and finds a new defect there each time, so the rounds never settle. *Precedent: a 346-file branch took 16 rounds; the blockers of round 8 sat in files round 1 had already cited.* A large change is read by several readers at once, each tracing one question. *Measured on that branch: six readers with one question each found 9 of its 11 blockers in one round; the single reader's first round found 2.*

## Plan before reading

Count the changed files, leaving out lock files, `insights/locale/**` and generated files. Write the plan at the top of the report, or to `plan.md` in the review directory when there is one:

- **Size.** `one reader` up to about 25 files, else `fan-out`. Say the count.
- **The bar and the settled list** the readers get. The bar is in `brief.md`. The settled list is every decision in the PR thread and in the rulings file, when the review has one.
- **The questions**, for a fan-out.

A single reader that plans a `fan-out` cannot run one. It says so in the first line of its report, "Above one reader's budget: N files. This review covers part of the change.", names the parts it read, and carries on.

## The questions

Three are asked of every large change:

1. **Who can read or write what.** Every whitelisted method, guest door and permission check the change adds or alters, as a guest, a reader the document is shared with, an author who lacks access to something the document refers to, and the owner. Which argument names the document that decides authorisation, and who supplies it.
2. **What happens to a document saved on the base.** Every patch, every default and normalizer on the read path, every shipped fixture and template. What did the base write, and what does the new code make of it.
3. **Does the main path work.** Build, save, view and share, for each kind of thing the change touches.

The rest come from what the change touches: one question per feature area, not per folder. A question that covers more than one reader can exhaust is split. *Measured: "is the value on screen what the query computes" found 1 of 15 known defects; split into number cards, axis values, formatting and tables, it found 6.*

A question has four parts:

- the sentence a reader can answer yes or no
- the entry points to start from
- the cases to exhaust, as a list. Write them from what the feature does, not from a defect you suspect
- the stage it belongs to, `design` or `works`

A later round asks new questions in the areas with the fewest traced paths. It does not repeat a question to go deeper. *Measured: of 39 defects two rounds missed, 32 sat where no question had been asked.*

## How a reader works

A reader gets `brief.md`, one stage file, one question, the bar and the settled list. It reports and never edits.

- **Trace the question end to end,** across files and across the server and the browser. Do not read file by file. Start at the entry points and follow each call until the value is stored, returned or drawn. Read the framework and frappe-ui source a claim depends on. Compare with the base when "did this work before" matters.
- **Exhaust the cases.** Do not stop at the first findings. Every case in the question ends as a finding, a clean line or a dismissal.
- **A clean line names the value checked, and every writer and caller of it.** "The form writes `'Line'`, the adapter passes it through, the component accepts `'line' | 'bar'`" is a check. "The adapter passes a type prop" is not. *Precedent: a reader cleared a path because the prop existed; the form wrote a value the component rejected.*
- **Anything read and not reported is a dismissal,** one line with the reason. Dismissals are checked.
- **A finding carries its trace:** the path from entry point to defect, naming functions, and the deciding lines quoted. A fix worker places the fix from the trace, where the value is written.
- Works readers report what clears the bar. What falls below it is a dismissal with the reason "below the bar".

A reader writes one file:

```
### <the defect in one sentence, in user terms>
- Bar: <1-5>, or Design
- Where: <path:line>, <path:line>
- Trace: <entry point to defect, 2-5 lines>
- Evidence: <the deciding lines, quoted>
- Owner: <the function, layer or document that owns the value>
- Confidence: high | medium | low, and what would raise it

## Traced and clean
## Read and dismissed
```

## Running a fan-out

The session that orchestrates does these in order. Readers within one step run at the same time.

1. **Design.** Readers on `design.md`, one per feature area. They also list the owners and contracts the change introduces: which function, layer or document owns each new value or rule. The orchestrator merges this into one list and stops. The maintainer rules on the design findings and the owners: fix, settled, or a different owner. The rulings go to the rulings file.
2. **Works.** One reader per question, each given the owners list. A value written or guarded outside its owner is a finding.
3. **Merge.** Group the reader files by root cause: two findings with one cause are one finding. Write the report in the format of `report.md`, with each finding's trace and owner in its `<details>`. Keep the reader files beside the report.
4. **Quality.** One reader on `quality.md`, once, after the code has stopped changing. On a branch whose history will be rewritten before merge, commit messages are out of scope.

Two stop rules were tried and dropped. Two readers agreeing does not show an area is done: readers of one area found the same defect for 3 of 21 defects. Reading an area once, or reading only the last fix pass's diff, misses defects in code already read: 9 of 20 sampled clean claims were wrong. A review is done when a round of new questions finds nothing above the bar.
