# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `docs/projects/`.

`docs/` is tracked. Effort docs are **branch-scoped**: they live on the feature
branch, and they are removed when that branch merges into `develop`. They record
how the work happened, not what the project is. Only durable documents stay on
`develop` — `CONTEXT.md`, `docs/adr/` and `docs/agents/`.

A few paths stay local-only and are ignored in `.gitignore`. Check it before you
assume a path is committed.

GitHub Issues (frappe/insights) is the public/community queue, not this tracker.
Don't create or triage GitHub issues unless explicitly asked.

## Conventions

- One effort per directory: `docs/projects/<effort-slug>/`
- The spec is `docs/projects/<effort-slug>/spec.md`
- Implementation issues are one file per ticket at
  `docs/projects/<effort-slug>/issues/<NN>-<slug>.md`, numbered from `01` —
  never a single combined tickets file
- Every ticket carries a `Status:` line near the top. Wayfinder tickets use
  `claimed` and `resolved` (see *Wayfinding operations*). Tickets raised from an
  incoming GitHub issue use the triage roles instead: `needs-triage`,
  `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`
- Comments and conversation history append to the bottom of the file under a
  `## Comments` heading
- Concluded efforts are closed out, not left in place. See *Closing out an
  effort*

## Closing out an effort

The effort docs die with the branch. The ADR is the only durable record of why
the work went the way it did, so write it before the branch merges.

1. Write an ADR in `docs/adr/` for each decision the map records. Add any new
   term to the glossary in `CONTEXT.md`.
2. Remove the effort with `git rm -r docs/projects/<effort-slug>/`. Put this in
   the same commit as the ADR. A deletion with no ADR beside it is a lost
   decision, and a reviewer can see that at a glance.
3. Move the working copies to `docs/archive/<effort-slug>/` to keep them on the
   machine. `docs/archive/` is local-only.

When a skill says "publish to the issue tracker", create the file under
`docs/projects/<effort-slug>/`. When it says "fetch the relevant ticket", read
the path or the number the user passed.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `docs/projects/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `docs/projects/<effort>/issues/NN-<slug>.md`, numbered from `01`,
  with the question in the body. A `Type:` line records the ticket type
  (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked
  when every file it lists is `resolved`.
- **Frontier**: scan `docs/projects/<effort>/issues/` for files that are open,
  unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`,
  then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
  Add the ADR filename to that pointer once the decision reaches `docs/adr/`. An
  entry with no filename marks reasoning that still has to be distilled before
  the branch merges.
- **Research findings**: land in `docs/projects/<effort>/research/`, linked from
  the ticket's answer.
