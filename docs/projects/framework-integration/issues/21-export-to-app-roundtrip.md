# 21 — Export to app and the developer-mode round-trip

Type: task
Status: ready-for-agent
Blocked by: 20
Spec: [spec-insights-foundation.md](../spec-insights-foundation.md), "Authoring flows"

## What to build

An app developer authors in the builder and releases through git.

Birth: "Export to app…" writes the closure — dashboard, its charts, their
queries — into the chosen app's bundle as one JSON file per item, and flags
the docs standard. The action requires a developer-mode bench with the
target app installed. Volatile fields are stripped (no `modified`, no
`owner`, no hash names, no cached results), so diffs are content-only.
Exports assign each dashboard item a stable vendor-owned key.

Iteration: on a developer-mode bench, standard docs are editable in the
builder, and save writes the JSON back to the app folder — the Builder
`is_standard` round-trip idiom.

The blessed release path is author → export into the app repo → git review →
normal app release. There is no production-site export flow.

## Acceptance criteria

- [ ] "Export to app…" writes the full closure into the target app's bundle
      and flags the docs standard
- [ ] Exported files carry no volatile fields, and a re-export with no edits
      is byte-identical
- [ ] Dashboard items carry stable vendor-owned keys that survive re-export
- [ ] On a developer-mode bench, editing a standard doc in the builder
      writes the change back to the bundle file
- [ ] Outside developer mode, no export or write-back surface exists
