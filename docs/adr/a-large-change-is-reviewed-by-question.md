# A large change is reviewed by question

Date: 2026-09-19

## Status

Accepted. Built in `.claude/commands/iris-code-review.md` and `docs/agents/code-review/`.

## Context

The code review ran as one reader working through every rule, under a budget of about 25 reads. That fits a fix. On a 346-file branch each round read a different part and found a new blocker there, so the review took 16 rounds and 299 fix commits. The score stayed at 1 of 5 while every earlier finding was closed: it measured how much had been read. Every blocker found after round 1 sat in a file an earlier round had already cited. Prose and commit subjects were reviewed and fixed every round, then discarded when the branch was re-cut. A quarter of the serious findings were introduced by fix passes, and half the fixes guarded a reader because no one had settled which layer owned the value.

## Decision

**One review, sized by a plan.** The review counts the changed files first. Up to about 25, one reader runs it. Past that, several readers run at once. There is no second mode: a fix is the same review with one reader.

**A reader traces a question, not a file.** Who can read or write what; what happens to a document saved on the base; does the main path work; then one question per feature area. A reader follows its question across files and across the server and the browser, exhausts the cases it was given, and accounts for each: a finding, a clean line that names the value checked, or a dismissal with a reason.

**Three stages, in order: design, works, quality.** A design finding changes what the rest is worth, so on a large change the maintainer rules on it, and on which layer owns each new value, before the works stage starts. Quality runs once, after the code has stopped changing.

**A bar marks what must be fixed.** Security, data loss, a silently wrong value, a broken main path, a regression for a common configuration. While a review loop runs, a fix pass takes those only.

**A review is done when a round of new questions finds nothing above the bar.** Later rounds ask new questions where the fewest paths were traced. They do not repeat a question to go deeper.

## Rejected

- **Looping one reader until the score passes.** The 16 rounds.
- **Two readers agreeing as the sign an area is done.** Readers of one area found the same defect for 3 of 21 defects.
- **Reading an area once, or reading only the last fix pass's diff.** 9 of 20 sampled clean claims were wrong. After a fix pass, the questions whose files it touched run again in full.
- **A separate command for large changes.** Two rulebooks drift. The rules are one set of files and the plan decides how many readers load them.
- **Scoring works findings only.** The score no longer stops a loop, so nothing is gained, and a fix that patches every call site would read "Looks good".

## Consequences

Measured by replaying the 346-file branch blind at the commit round 1 read: six readers with one question each found 9 of the 11 blockers present in 12 minutes, against 2 for the single reader's first round. Twelve narrower questions brought that to 10 of 11 and found 11 serious defects the 16 rounds never reported. No finding in either round was false. Those questions were written by hand. With the questions planned from `docs/agents/code-review/questions.md` alone, one round found 6 of the 11. It found 8 after readers stopped judging their own findings and a census question was added, and 9 after the main path became a question of its own whose actions are pressed and every question listed the writers of its value. That last round ran 26 readers for 22 minutes, found 36 of the 73 known defects and 11 serious ones nobody had reported, and 1 of its 164 findings was false. It left about 51 findings to fix and 86 nits for the merge and the maintainer to go through. Two rounds still found under half of everything the 16 rounds found, so a large review ends by judgment under the bar, not by exhaustion.

CI runs one reader. Above its budget it says so and reviews the part it can cover. The fan-out needs a session that can start other agents.
