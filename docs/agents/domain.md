# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — the glossary.
- **`docs/adr/`** — the ADRs that touch the area you are about to work in.

Do not suggest writing an ADR upfront. The `/domain-modeling` skill (reached via
`/grill-with-docs` and `/improve-codebase-architecture`) writes them when a term
or a decision actually gets resolved.

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

> _Contradicts ADR-0001 (type-independent chart config) — but worth reopening because…_
