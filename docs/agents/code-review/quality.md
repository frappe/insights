# Code review: quality stage

Read at the quality stage of `/iris-code-review`, after `brief.md`.

## Vocabulary and decisions

- **The glossary rules.** `CONTEXT.md` defines the terms and retires words under
  `_Avoid_`. A retired word in new code, UI or docs is a `Concerns` finding. A new name
  for a concept the glossary defines is the same finding.
- **A name that is not self-explanatory.** *"alias isn't understandable just by reading
  code"*. Match the Frappe ecosystem's nouns; challenge invented jargon. Known and plain
  beats abstract: *"pick something simple and known, instead of abstract"*.
- **UI and code drifting apart.** A label renamed without the internals, or the reverse.
  *"why not change the internals too? wouldn't it cause confusion?"* The glossary's live
  double-names (grain/`granularity`, Library/`gallery`) are the exception, not the licence.
- **A hard-to-change name settled later.** Hook names, field names, URLs. *"changing the
  hook name would be a difficult change, so shouldn't we decide it right now?"* A working
  name the maintainer has parked stays parked.
- **ADRs.** Read the ones in `docs/adr/` that touch the changed area. A diff that
  contradicts one names it by slug and says whether it is worth reopening. The other
  direction too: a long-horizon decision the PR makes without an ADR is a nit; a trivial
  one with an ADR is the same nit. *"we are too eager to create one, even though it was a
  trivial decision"*. A new term an ADR needs lands in the glossary in the same PR.

## Diff hygiene and tests

- **Scope.** One PR ships one thing. The cause-level fix and the sibling sweep belong in
  this PR; a second idea does not. *"drop the config key, keep it to one idea, raise a
  PR"*. Do not propose the split — name the second idea and let the maintainer decide.
  *"why not in this PR only?"* Unrelated docs, generated files and reformat churn get
  reverted, not explained.
- **Size.** *"this seems like a less line of change, but a PR has more, can you review if
  all this is needed?"* A fix should shrink the diff where it can. Dead code, uncalled
  helpers, stale comments and docs the change made wrong all go.
- **Commits.** One logical change each, no ticket ids, no body where the tree says it. A
  review fix is amended into the commit that introduced the code, and history is rewritten
  freely before merge. Leave the conventional prefix alone — `commitlint` gates it in CI,
  against a wider type list than you remember.
- **Tests.** Ask for a test on the **public surface** when behaviour changed and nothing
  covers it. *"i prefer tests that are broader, that check the public surface/APIs, instead
  of testing internals"*. A behaviour fix carries the test that fails without it, covering
  the refusal and the legitimate path. Do **not** ask for tests on config helpers, plumbing,
  or internals — test bulk is review cost. If the change is risky and untested, say what
  single test would settle it, not that coverage is missing.
- **Stale sweep.** Name what the change made wrong elsewhere: sibling call sites, the same
  bug in the other copy, comments, README, the writer on the other release line.

## Prose

The most repeated standard in the maintainer's history. Treat verbosity as a defect,
not a nit.

- Commit messages, PR descriptions, docs and comments say it once. Length must match the
  size of the change. *"the PR is still verbose, reduce the verbosity, too detailed for a
  minor change"*.
- Simplified Technical English: active voice, short sentences, no marketing tone, no wall of
  text. A PR description never restates the diff. It explains with a short example or
  snippet, not abstract prose — *"code snippets are best medium to explain to a dev like
  me"*. The description is the one place old-versus-new reasoning belongs.
- Comments earn their place only by explaining a non-obvious *why* — a constraint, a gotcha,
  a rejected alternative. A file header plus a docstring saying the same thing means one
  goes.
- Docs state the convention and stay state-agnostic. Nothing that goes stale, nothing the
  code already shows, nothing the audience already knows, no before/after narration.
