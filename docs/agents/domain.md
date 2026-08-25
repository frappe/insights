# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary.
- **`docs/adr/`** — the ADRs that touch the area you are about to work in.

Do not suggest writing an ADR upfront. The `/domain-modeling` skill (reached via
`/grill-with-docs` and `/improve-codebase-architecture`) writes them when a term
or a decision actually gets resolved.

## Most work produces no ADR

The `/domain-modeling` test decides, and all three must hold: the decision is
hard to reverse, it is surprising without context, and it is the result of a
real trade-off. Two or three out of three is a no.

Resolving a ticket is not by itself a reason to write one. Two failures this
repo has had:

- **A bug fix is not a decision.** If the fix is the only correct
  implementation, nobody will reopen it and nothing is at stake in recording
  it. The commit message is the record.
- **Timing is not durable.** "There is no v1 yet", a token count, what the runs
  said this week — that is true for a month and expires with the branch. It
  belongs in the ticket. An ADR holds what stays true after the effort is gone.

Write an ADR at the moment the decision is made, not when the ticket closes.
Close-out is for the ones you missed, and there should be few.

## Naming

`docs/adr/<slug>.md`. No number.

Numbers were dropped because they are allocated on a feature branch and
collide on merge — two branches both took `0003`, and `iris-review.md` cited
two ADR numbers that resolved to the wrong documents. The slug is the stable
name and the `Date:` line is the ordering, so the number carried nothing and
broke on the one operation that matters.

Cite an ADR by slug, never by number: `` `declared-tool-policy` ``, or a
relative link to the file.

## Durable documents and effort documents

Two kinds of document live in this repo, and they have different lifetimes.

**Durable** documents describe the project. They live on `develop` and they
change with the code:

- `CONTEXT.md` — the glossary
- `docs/adr/` — the decisions
- `docs/agents/` — these conventions

**Effort** documents describe how one piece of work got done. They live under
`docs/projects/<effort-slug>/` on a feature branch, and they are removed when
that branch merges. See `issue-tracker.md` for the close-out.

Never move an effort document into `docs/adr/` to keep it alive. Distill the
decision and let the rest go.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts `type-independent-chart-config` — but worth reopening because…_
