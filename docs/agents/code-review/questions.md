# Code review: planning a review, and reading by question

One reader covers about 25 changed files. Past that, a single reader reads a different part of the change each round and finds a new defect there each time, so the rounds never settle. *Precedent: a 346-file branch took 16 rounds; the blockers of round 8 sat in files round 1 had already cited.* A large change is read by several readers at once, each tracing one question. *Measured on that branch: six readers with one question each found 9 of its 11 blockers in one round; the single reader's first round found 2.*

## Plan before reading

Count the changed files, leaving out lock files, `insights/locale/**` and generated files. Write the plan at the top of the report, or to `plan.md` in the review directory when there is one:

- **Size.** `one reader` up to about 25 files, else `fan-out`. Say the count.
- **The bar and the settled list** the readers get. The bar is in `brief.md`. The settled list is every decision in the PR thread and in the rulings file, when the review has one.
- **The questions**, for a fan-out.

A single reader that plans a `fan-out` cannot run one. It says so in the first line of its report, "Above one reader's budget: N files. This review covers part of the change.", names the parts it read, and carries on.

## The questions

Four are asked of every large change:

1. **Who can read or write what.** Every whitelisted method, guest door and permission check the change adds or alters, as a guest, a reader the document is shared with, an author who lacks access to something the document refers to, and the owner. Which argument names the document that decides authorisation, and who supplies it.
2. **What happens to a document saved on the base.** Every patch, every default and normalizer on the read path, every shipped fixture and template. What did the base write, and what does the new code make of it.
3. **Does the main path work.** Build, save, view and share, for each kind of thing the change touches. Every action on the path is exercised, not a sample of them.
4. **Is everything the base had still there.** A census, not a trace. List every control, action, menu item, option and endpoint the base had on the surfaces the change touches, from the base's code. Each one is present at HEAD and still wired, or the change removed it on purpose and says so. A value question never finds what is missing. *Precedent: a rebuilt table lost its pager and its export, and one chart type's card lost every button its peers show; no question about a value reached either.*

The rest come from what the change touches: one question per feature area, not per folder. A question that covers more than one reader can exhaust is split. *Measured: "is the value on screen what the query computes" found 1 of 15 known defects; split into number cards, axis values, formatting and tables, it found 6.*

A question has four parts:

- the sentence a reader can answer yes or no
- the entry points to start from
- the cases to exhaust, as a list. Write them from what the feature does, not from a defect you suspect
- the stage it belongs to, `design` or `works`

A later round asks new questions in the areas with the fewest traced paths. It does not repeat a question to go deeper. *Measured: of 39 defects two rounds missed, 32 sat where no question had been asked.*

## How a reader works

A reader gets `brief.md`, one stage file, one question, the bar and the settled list. It reports and never edits. Of `brief.md` a reader runs phases 1 and 2 only, without the step that applies "Do not flag", and its read and check caps do not apply: they are one reader's budget for a whole change. Where this section and `brief.md` disagree, this section wins.

- **Trace the question end to end,** across files and across the server and the browser. Do not read file by file. Start at the entry points and follow each call until the value is stored, returned or drawn. Read the framework and frappe-ui source a claim depends on. Compare with the base when "did this work before" matters.
- **Exhaust the cases.** Do not stop at the first findings. Every case in the question ends as a finding, a clean line or a dismissal.
- **A clean line names the value checked, and every writer and caller of it.** "The form writes `'Line'`, the adapter passes it through, the component accepts `'line' | 'bar'`" is a check. "The adapter passes a type prop" is not. *Precedent: a reader cleared a path because the prop existed; the form wrote a value the component rejected.*
- **Run one real value through a transform.** For a patch, a rescale, a formatter or a parser, pick the value a real document holds, do the arithmetic by hand, and write the numbers in the line. *Precedent: a layout patch was cleared by reading it; its arithmetic assumed a row height no site had run.*
- **A reader does not judge.** Report every defect you confirm, and propose its bar number, or `below`. Do not apply the bar, the settled list or "Do not flag": the merge does, in one place, and lists what it dropped. *Measured: readers reached 47 of 73 known defects, reported 17 and talked 30 away; none of the findings any reader did report was false.*
- **"The base did the same" is never a reason to drop a finding.** Report it and attach the base comparison. The change may have made old code reachable, relied on it, or rewritten the lines around it.
- **A dismissal is only for what turned out not to be a defect,** one line with what you read. Dismissals are checked.
- **A finding carries its trace:** the path from entry point to defect, naming functions, and the deciding lines quoted. A fix worker places the fix from the trace, where the value is written.

A reader writes one file:

```
### <the defect in one sentence, in user terms>
- Bar: <1-5>, `below`, or Design
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
3. **Merge.** Group the reader files by root cause: two findings with one cause are one finding. Then apply the bar, the settled list and "Do not flag" of `brief.md`, here and nowhere earlier. Mark what clears the bar `must fix`; keep what is below it as nits; list what "Do not flag" or the settled list dropped, one line each, under `Dropped:` so the maintainer can overrule it. Write the report in the format of `report.md`, with each finding's trace and owner in its `<details>`. Keep the reader files beside the report.
4. **Quality.** One reader on `quality.md`, once, after the code has stopped changing. On a branch whose history will be rewritten before merge, commit messages are out of scope.

Two stop rules were tried and dropped. Two readers agreeing does not show an area is done: readers of one area found the same defect for 3 of 21 defects. Reading an area once, or reading only the last fix pass's diff, misses defects in code already read: 9 of 20 sampled clean claims were wrong. A review is done when a round of new questions finds nothing above the bar.
