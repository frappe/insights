# Design and review playbook

One method for three jobs: propose a design for an issue, review a pull request, and propose a better design for existing code. The command and the skills that run it stay short. This file is the method.

A review answers in this order: is this the right change, at the right layer, with one owner for each decision; what ships now and what waits; the guards that keep the design in place; then the defects. Finding defects is the last part, not the whole review. *On one pull request reviewed over 11 rounds, more than half of the must-fix findings came from the review's own fix passes. Each class that kept coming back ended with a design change, not a fix.*

Two words have one meaning here:

- An owner is the one function or layer that makes a decision. It is not a document's `owner` field.
- A guard is a lint rule or a test that fails when code goes around an owner.

Inputs every run reads:

- `docs/agents/product-context.md`: who the product is for today. The playbook asks the questions, and that file holds the current answers.
- The repo's own rules: what is must fix, what not to flag, and the repo's own checks. Insights has `insights.md` beside this file. Another repo has its own guide (frappe `code_review.md`, `AGENTS.md`).
- Prior rulings: the maintainer's decisions on this change, and the items deferred from it.

`reading.md` says how a reader plans, searches, traces and confirms. `report.md` gives the report format.

## 1. Users: who uses it, and is it needed now?

Why: the right design depends on who pays for each choice. Name them before you read the code.

- The job in one sentence, and the persona from `product-context.md`.
- Every kind of user the change reaches, and every kind of data it reads or writes. Include the kinds nobody designs for:
  - a document saved before this change, and one from the oldest supported release;
  - each database backend the code runs on, an empty result and a very large one;
  - a second run at the same time: a second click, a second tab, a second queued job;
  - when the change adds or alters an endpoint or a permission check: a guest, a user the document is shared with, a user without read on the parent document, and a desk user with no role in this app.
- What the change adds to their work, and what it removes.
- Is it needed now, and does it affect most users? A change that is not needed now is deferred, not reviewed. Ask this of each parameter, hook, setting and abstraction the change adds too.
- Before you accept that a bug exists, reproduce it on the target branch with the pinned dependencies.
- A pull request holds one idea, plus the same change in similar places. When it holds a second idea, name it for the maintainer. Do not prescribe the split.

## 2. Layer: which layer should own it?

Why: the cheapest correct fix is at the layer that owns the concept. At the wrong layer, the same fix is needed at many call sites.

- The framework, frappe-ui, or the app? It belongs in the framework when the split is clean there, not only when a second app asks for it.
- Does a path that does this job already exist, in the app or in the framework? One job gets one user experience and one implementation.
- A new dependency names its job, and why no installed package does it.
- Before you accept a workaround for a framework limit, read how the framework implements the limit. The limit is often a parameter the app can set. *A client-side scheduler was built around `@concurrent_limit()`, whose `wait_timeout` the app can set.*
- When the app works around a framework gap, the gap gets an issue. A code comment is not a record.
- A dependency across layers is accepted when it makes the design simpler, and the review names it.

## 3. Design: does each decision have one owner?

Why: when two places answer one decision, they drift apart. Give each decision one owner, and make every entry point ask it.

- List the decisions the change adds or touches, not the values. "What may this user get from this chart" is a decision, and the user it runs as is a value. "Is this stored result still current" is a decision, and the timestamp it compares is a value.
- For each decision, find every place that answers it. Search for the question, not for one function name. Two implementations that agree today are still two.
- Each decision gets one owner. Delete a duplicate. Do not keep two in step.
- The default is the path you trust to be correct. A switch that exists only because you were not yet sure is removed when you are.
- Remove a branch that no real case takes. Do not handle it. Ask what would break if you assumed it away.
- Build on the framework's own features, such as DocPerm, DocShare and doc events. Add only what the user can see on top.
- When a feature needs data the user cannot read, a narrow endpoint returns only that data. The permission is not widened.
- A new capability of a document type belongs to that document type, not to a new one beside it. A concept that is shared or permitted on its own gets its own document type, because a child row cannot be shared.
- A stored format has one owner: a patch that rewrites old documents, or code that reads the old format. Not both.
- Delete what the change replaced.
- Code reads as the framework would write it. Fewer lines bought with extra indirection is not simpler.
- Names use the words the framework and the app already use, one name per concept. A name that needs a comment, or a second name for part of a set, usually shows a concept that is wrong. Settle a name that is costly to change after release (a hook, a field, a route) before it ships.
- A check sits at the one boundary every caller crosses. A fallback that no input reaches, or a check away from that boundary, is noise.
- For each check the change adds or depends on, name the value it reads and the fact that value stands for. When they can differ, list the cases: a writer that does not set the value, a document from before it existed, a value from the request. *A native SQL check read the table names a parser found, so every read the parser did not see as a table passed.*

## 4. Scope: what ships now, and what waits?

Why: name the right end design and the step toward it, so a quick fix does not move away from it.

- The end design in one sentence, and the smallest step toward it that can ship now.
- A shortcut is fine when it is cheap and the later step to the right design is known. Name that step.
- A breaking change tells users what happens to their data, removes the old behaviour only after a notice or a setting, and carries no old code into the new path. Count the affected sites from a source that sees all of them, not from opt-in telemetry.
- A feature added only to serve a migration is behind a setting, and names when it is removed.
- A dependency version change is reviewed as code: read what changed upstream between the two versions, and find each caller of what changed. *Four fixes in nine days followed frappe-ui version changes.*
- What the change does not have to fix: a defect older than the change, outside the lines it rewrites, is deferred to an issue, or to a private advisory for security. It becomes this change's defect when the change makes it worse or easier to reach.
- Say when the right design is not known yet. A reuse that works but feels wrong stays flagged.

## 5. Verify: how do we prove it holds?

Why: prove that the design holds, and make the next mistake fail a guard instead of a review round.

**Guards.** Each owner from part 3 gets a guard. Choose it by what the owner decides:

- Who may do what: a semgrep rule that fails the bypass, or a decorator that makes the bypass impossible.
- A stored format: a patch test on a document in the old format, or validation that refuses the old format on save.
- A cost: a query count or a timing against the base.
- Any owner: one test through the real path for each kind of user and data from part 1 that the owner treats differently. The repo's testing guide says at which level it sits.

Do not ask for tests of helpers, configuration or plumbing. The real-path test covers them, and extra tests cost review time.

**Reading.** Readers trace questions, not files, and report against the repo's must-fix rules (`reading.md`). Readers have missed these:

- A value's identity, not only its content. When code keeps an object by reference, find where that object came from on the first write.
- A new field that refines an existing key: list every reader of the old key.
- A failure the user sees as a normal value: an `except`, a `.catch` or a default that turns an error into an empty chart, a zero or a spinner that never stops.
- A defect older than the change, on a line the change touches, is reported with its own severity and marked older. Never drop it or lower it. *A map that drew empty regions black was filed as old and not fixed, and it reached users.*
- A type error on a field that a dependency does not declare is a live defect.
- Whether a path is reachable is judged against the consumers the feature is built for, not only the apps installed today.

**Running.** Before merge: a production build, the patches on a copy of production data, and the most-used paths timed against the base. A number the change states, or a cost it accepts (bundle size, queries, migration time, rates), is measured on this code, or removed. It is not argued or taken from elsewhere.

**Finish.** When the code stops changing, read the comments, prose, commit history and stray changes once. This runs once because only then is the code final. Hold the change to this:

- Each commit holds one logical change, with a plain subject and no ticket ids. It has a body only for a reason the code cannot show. Review fixes are amended into the commit they fix.
- Commits, PR descriptions, docs and comments say each thing once, in Simplified Technical English, at a length that matches the change.
- A PR description explains the change with one short real example, never a list of the files it changed.
- Code comments and docs state the current convention. A comparison of old and new goes only in the PR description, because it goes out of date.
- A comment stays only when it explains a reason the code cannot show.

## Fixing

Why: a fix is a small design change, held to parts 3 to 5. *On the 11-round review, each fix added about 0.6 new must-fix defects. The rate fell after fixes went to planned owners, but other changes happened at the same time, so the cause is not proven.*

- Plan the pass by cause before any code: the owner, how the fix works, and the guard. Only the causes that need a decision go to the maintainer, each with its consequence.
- A larger improvement is welcome when the plan includes it: a new owner, a deleted duplicate. An unplanned change on the way is not.
- A fix's test runs the real path and its nearest untouched neighbour. It fails before the fix and passes after.
- A reader who did not write the fix checks the pass's diff for callers it broke, and the guards run.
- A security fix's branch, commits, tests and comments name the rule it enforces, not the attack.
- Minor findings wait until the code stops changing. Then they get one pass, with the same check.
- The plan sets a limit on passes. At the limit, the open findings go to the maintainer to rule on or defer.
- After the last pass, write a short retro: for each top class of finding, the guard or rule that would have stopped it, as a diff to this playbook or the repo's rules.

## Size

A small change runs all five parts in one reader, and its report still opens with the verdict. A large change runs parts 1 to 4 first, with the guard each owner needs, and stops for rulings on the owners that need a decision. Part 5's reading is then split by question, one reader per question (`reading.md`). Running happens once, before merge.

## For each job

| Job | Parts | Output |
|---|---|---|
| An issue | 1 to 4, and the guards of 5 | A proposed design, the steps to it, and the guards to add |
| A pull request | 1 to 5 | Verdict, owners to decide, scope, guards, defects, deferred items |
| Existing code | 1 to 4 on the code as it is | Steps from today's design to the right one, each one shippable |

The verdict is one line: the right change; the right change at the wrong layer; or the wrong change, with the change it should be.
