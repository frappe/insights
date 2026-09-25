# Code review: brief

Read first by every reader of `/iris-code-review`. The stage files (`design.md`, `works.md`, `quality.md`) hold what to check. This file holds how to check it.

## Run this in three phases, in order

The phases exist to keep the writing rules away from the searching. Length limits shape
what you look for, so you do not get to think about length until phase 3.

**Phase 1 — read and search.** Read `CONTEXT.md` (the glossary), `AGENTS.md`, and the ADRs
in `docs/adr/` that touch the changed area. Cite them; never paraphrase a decision from
memory. If a `docs/projects/<effort>/` directory is about the branch, read the map and any ticket the
diff claims to resolve. Then investigate — spend most of your budget here. Read around the
hunks, not just the hunks. Grep the other call sites of anything the diff touches.
`git log --oneline -n 5 -- <file>` on suspicious files. Work through the stages in the order the command gives.
Cap: ~25 read/grep/glob, ~5 git.

Write the result as a raw candidate list. Ugly is correct here. No format, no length
limit, no filtering — a candidate you are unsure of still goes on the list.

**Phase 2 — confirm each candidate.** One at a time. **Run the check. Do not reason about
it.** If the claim is that a value comes back wrong, read the code that produces it and
say what it returns. If the claim is that a caller breaks, open the caller. If the claim
is about a framework default, read the framework. Your checks are reads — you have no
interpreter, so a check that needs one counts as unconfirmable. A candidate you cannot
confirm is either dropped, or stated as a question with the word "worth checking" in it —
never asserted.

- **Read the whole line you cite.** A decorator's arguments are part of the claim.
  *Precedent: `allow_guest=True` was read, `methods=["GET"]` beside it was not, and every
  member got a blank app the next day.*
- **The fix you suggest is a candidate too.** Before you name it, open what it changes
  and its callers. *Precedent: "move it into `.then`, that is the whole fix" created an
  infinite re-run; another review spent three rounds unwinding a watcher path it pointed
  down.* A fix you did not check is a question, not a suggestion.
- **A deliberate-looking constant gets a blame before a finding.** `Min` was deliberate in
  a prune window; `Max` would have disabled pruning. Read what the window is for.

Budget for this phase is separate: do not skip a check because the comment is getting long.
The comment does not exist yet. Cap: ~20 checks. The job dies at 15 minutes and posts
nothing, so a shorter review beats an unfinished one. At the cap, drop the weakest
candidates and go write.

Then apply "Do not flag" below. Drop everything it forbids.

**Phase 3 — write.** Only now read `docs/agents/code-review/report.md` and write the comment in
its format. You may cut for length here. You may not soften a finding that survived phase
2, and you may not drop one to fit a line count. If everything survived and the limit is
tight, the score carries the weight, not the omission.

## The bar

A works finding is **must fix** when it clears one of these:

1. Security: anyone reads or changes data their permissions do not grant, guest or signed in.
2. Data loss or corruption: a save, migration or patch drops or rewrites stored content wrongly.
3. Wrong value: a chart, card, drill or table shows a value that is not what the query computes, with nothing on screen to signal it.
4. Broken on the main path: an author cannot build, save or view a chart or dashboard, or a reader cannot open a shared or public one. Throws, blanks, hangs.
5. Regression: something that worked on the base and no longer does, for a common configuration.

Mark it `must fix` in the report. The bar does not change the score, and it does not hide a finding below it. It tells the maintainer, and a fix pass, what cannot wait: while a review loop runs, a fix pass takes the must-fix findings only. The maintainer can set a tighter bar for one review; when the rulings name one, it replaces this list.

## Do not flag

The maintainer has told an assistant to stop raising most of these. Raising them costs
trust.

- Missing browser or end-to-end verification, or screenshots. The maintainer tests by hand.
- A thin PR description or a body-less commit. Long prose is the defect.
- Missing comments, docstrings or file headers where the code is self-evident.
- Test coverage on config helpers, plumbing or internals. A missing eval is not a blocker.
- A missing extension point, generic abstraction, registry, option or new concept whose
  second case has not arrived. *"let's go all in with YAGNI"*.
- An interim or surgical fix as under-designed, when the description says so or the
  redesign is tracked. It ships; name the destination in one line and do not score it.
  *"i'll merge this asap first, and can you … suggest a better designed version"*. Same
  for a PR that narrows a pre-existing gap without closing it.
- Guards, options, polish, edge-case coverage or measurement before a first version
  ships. *"keep it simple for now, will experience first and then suggest something"*.
- A missing ADR, ticket or effort doc for a trivial or still-moving change. Effort docs
  are not committed to this repo.
- A dependency on another open branch or a planned framework change, on a feature branch.
  Name it; do not block. A PR into `develop` that needs a pin move is different.
- A missing button, banner, close control, section title, freshness indicator or hover
  emphasis. Affordances get removed until they prove useful. This covers asking for a new
  one. A control the base had, or that every peer of the surface has, going missing is a
  regression.
- One extra query, or a slow one-time job. Insights is not built for heavy sites.
- A shared frappe-ui or framework component lacking what Insights needs. Parity is not a
  goal; Insights bridges on its side.
- Checks that already fail on the target branch, and a bug caught in development that
  never shipped. This does not cover a pre-existing bug in lines the diff rewrites — if
  the PR touches it, it is in scope.
- Timelines, capacity, or migration during exploratory work.
- Security hardening past what comparable framework APIs do, when the exposure is known and
  accepted. Guest-reachable leaks and writes into a customer's database are not in this
  bullet — those are blockers.
- Backward compatibility for something with no users yet — a clean break before v1 is right,
  and no shim is needed. This does not cover shipped Insights v3 behaviour.
- Documentation incompleteness. Concise beats complete.
- A scope punt the maintainer already declared, a split already reasoned about, an item
  marked leave-as-is, or a rename declined.
- Branch hygiene on an integration branch the maintainer plans to split later.
- An illustrative example that is not real. It exists to explain.
- Anything a linter or pre-commit catches, regenerable artifacts, personal-preference
  rewrites, or a finding with no `file:line` and no behavioural consequence.
