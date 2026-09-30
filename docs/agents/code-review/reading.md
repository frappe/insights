# Code review: reading

How a reader plans, searches, traces and confirms, how it writes its file, and how a large change is split and merged. The reading rules in playbook Verify apply throughout.

## Plan

- One reader plans before it reads code. It writes down the decisions the change touches (playbook Design), the kinds of users and data (playbook Users), and the questions below that apply. Then it answers each question in turn. *Past misses came from questions nobody asked. When the question was asked, readers found most of those defects.*
- One reader covers about 25 changed files of reviewable source. The repo's rules say what to leave out. Above that, the change is split by question, one reader per question (playbook Size). *On a 346-file branch reviewed in 16 rounds, the blockers of round 8 were in files that round 1 had cited.*
- The four standing questions. With several readers, each is its own question: split it when it is too wide, and never fold it into a feature question. *A plan that folded the main path into its feature questions missed five defects that throw.*
  1. Who can read or write what? Ask it when the change adds or alters a whitelisted method, a guest endpoint or a permission check. For each one and each kind of user from playbook Users, find the argument that names the document the permission check reads, and ask whether the caller controls it.
  2. What happens to a document saved on the base? Take what the base stored and run it through every patch, default, read-time conversion and shipped fixture.
  3. Does the main path work? The repo's rules define it. Follow each action's handler to its end with a real document's state, for every type the surface serves. Finding the handler is not enough. *A reset action present on every chart type threw on three.* Compare a surface's actions across every type that shows it. A type that lacks what the others show is a defect.
  4. Is everything the base had still there? List every control, action, option and endpoint the base had on the changed surfaces. Name where each one is at HEAD, or where the change says it removed it. *A rebuilt table lost its pager and its export.*
- Beyond the four, one question per user-facing feature area, not per folder.
- Split a question that one reader cannot finish. *"Is the value on screen what the query computes" found 1 of 15 known defects as one question, and 6 when split four ways.*
- A question is a yes-or-no sentence with its entry points and the cases to cover. Write it from what the feature does, not from a suspected defect.

## Search

- Search and confirm before you write, so the report's length never decides what you look for or keep.
- Trace each question from its entry points to its end, across files and across server and browser. Never read hunk by hunk or file by file.
- For every value or function the change touches, find all its writers and readers by search, not only the path the diff shows. *A flag was traced from the form to the chart and cleared, but a setup function nobody traced also wrote it.*
- Trace the first call, the zero-row result, and documents saved before the field existed.
- When a cache is cleared, clear it at every layer that holds the same data, the document cache included.
- A watcher or effect never writes what it watches, and never starts again the call that fed it.
- A patch or a background job gives the same result when it runs twice, and when two copies run at the same time. If it cannot, the change says why.
- A patch that writes without the controller (`db_insert`, `db_set`, a hook called by hand) names each hook it skips. *One such patch needed four later fixes.*
- Before you call deliberate-looking code wrong, read its history for why it was chosen. *`Min` was deliberate in a prune window, and `Max` would have turned pruning off.*
- Read the base when the finding depends on whether something worked before.
- Every candidate, doubtful ones included, goes on the list. Filtering waits for confirmation.
- Every case in a question ends as a finding, a traced-and-clean line or a dismissal. Do not stop at the first findings.

## Confirm

- Confirm each candidate on its own by reading the code that decides it, framework and frappe-ui source included. Never confirm by reasoning from what you expect.
- Check a claim, a "resolved" reply or a premise in the PR description in the code before you accept it, whoever wrote it.
- A claim that a finding depends on (a recorded decision, a tool that exists, how upstream behaves, how the framework uses a feature) cites the line you read, not memory.
- Read a cited line whole. A decorator's arguments are part of the claim. *`allow_guest=True` was read and `methods=["GET"]` beside it was not. Every member got a blank app the next day.*
- Check a suggested fix against what it changes and against its callers, or offer it as a question. *"Move it into `.then`" caused an infinite loop.*
- For a patch, a rescale, a formatter or a parser, run one real stored value through it by hand and write the numbers. *A layout patch was cleared by reading, but it assumed a row height that no site had.*
- Never assert an unconfirmed candidate. Drop it, or state it as a question that names what would settle it.
- A traced-and-clean line names the value checked and every writer and caller of it, not only that a prop exists. *A path was cleared because the prop existed, but the form wrote a value the component rejected.*
- Dismiss only what proved not to be a defect, in one line that names what was read, so it can be checked.

## The reader's file

A reader writes one file: findings, then traced-and-clean lines, then dismissals. Each finding carries what a fixer needs to find the owner. The severity is a proposal. `report.md` says who decides it.

```
### <the defect in one sentence, in user terms>
- Where: <path:line>
- Trace: <entry point to defect, naming functions>
- Evidence: <the deciding lines, quoted>
- Owner: <the function, layer or document that owns the decision>
- Severity: <the must-fix rule it meets>, or minor
- Confidence: high, medium or low, and what would raise it

## Traced and clean
## Read and dismissed
```

## Merge

The merge groups reader findings by cause: two findings with one cause are one finding. Then it writes the report by `report.md`.
