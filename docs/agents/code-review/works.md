# Code review: works stage

Read at the works stage of `/iris-code-review`, after `brief.md`.

## Does it work

The baseline the taste sits on. A likely bug that would ship is a blocker.

- **Empty, null and wrong-default paths.** The first call, the zero-row result, the field
  that is unset on old documents.
- **Every layer of a cache.** A stale read survives when one layer is cleared and the
  document cache under it is not. *Precedent: the team cache was cleared, the team
  document that held the grant rows was not.*
- **Watchers and re-runs.** A watcher that writes what it watches, an effect that
  re-triggers on its own output. *Precedent: a fix moved into `.then` re-ran itself.*
- **Background jobs and patches run twice.** Idempotent, or say why not.
- **The other release line.** A stored field renamed or made required on `develop` breaks
  a writer that lives on `version-3-hotfix`. *Precedent: one rename on `develop` needed
  two follow-up fixes on the hotfix line.*

## Evidence

- **A load-bearing assumption with no evidence.** A claim about upstream behaviour, a sign
  convention, a schema, site data, or the field a system of record uses, asserted rather
  than shown. Read the upstream implementation and cite `file:line`. If the assumption is
  wrong and the feature fails silently, hold the approval. *Precedent: the AP sign
  convention, asserted and wrong.*
- **An unmeasured number.** Rates, load times, query counts, row counts. *"don't mention
  MariaDB ~1k per minute … seems immature to mention that confidently"*. Either measure it
  or drop the claim. A published benchmark quoted as your own measurement is worse than no
  number. Measure what the PR publishes or the cost it accepts — bundle, queries, migrate
  time. Do not ask for a measurement to settle a taste call before v1.
- **The premise unchecked.** Sometimes the bug does not exist, or exists only in a local
  checkout. *"the dialog isn't broken on develop branch, are you sure?"* Check the target
  branch and the pins — a frontend fix depending on behaviour newer than the `frappe-ui`
  pin in `frontend/package.json` belongs on the branch that moves the pin. *Precedent: a
  PR was closed for that reason.*
- **Defence that cannot fire, or does not defend.** A fallback no real payload reaches, or
  a guard that is not the real boundary. Both are noise — say which.
- **CI.** When checks fail, say whether the failure exists on the target branch. A
  pre-existing failure is not the PR's; a pass nobody saw is not a pass.

## Frontend

- **frappe-ui first.** A hand-rolled control, picker, tab switcher or button is a finding
  unless the PR states why. Reusing the existing picker beats a second one for one field.
  An "experimental" frappe-ui component is fine to use. In CI you cannot read frappe-ui —
  it resolves from the pin in `frontend/package.json` and is not checked out. So name the
  component you expect and mark the finding "worth checking". Never assert that one exists.
- **Match the surrounding surface.** *"follow the existing control/config style and not
  introduce something new, the controls, layout are thoughfully designed"*. Semantic
  tokens only (`text-ink-*`, `bg-surface-*`, `border-outline-*`); a hardcoded colour breaks
  dark mode. Lucide icons only. One base component per control kind, so styles stay
  consistent.
- **Quiet by default.** No shadows or elevation — an elevated element gets a shadow only,
  never shadow plus border. Minimal borders, at most one primary button per view, no
  coloured buttons, no uppercase labels, no banner or label competing for attention.
  Prefer spacing and typography to borders — but not to the point of no separation at all.
- **Alignment and type scale are defects, not polish.** Baselines that do not line up,
  mismatched text sizes, uneven spacing, labels that wrap, a clipped focus ring. He
  reports these as bugs.
- **Layout must not shift between variants.** An optional part is an addition. *"adding a
  delta or spline should be just additions, and the top part shouldn't move"*. Peers in a
  group get the same treatment — no ornament on one card only.
- **Text on screen must earn its place.** Redundant titles, explainer copy, demo narration,
  em-dashes, "under development" voice, internal vocabulary. User-facing copy is plain
  and never misleading about what a click does.
- **New user-facing text goes through `__()`.** The app is translated through crowdin, and
  a bare string never reaches a translator. Check the strings the diff adds, not the file.
- **Affordant without hover.** A control that appears only on hover, or a disabled control
  with no hint of its precondition. *"the anchor + button is hidden if not hovered, bad
  experience"*.
- **Unrecoverable state is a blocker.** *"the only way to recover is delete the chart and
  create one again"*. An error must not break the layout either. Empty states and container
  sizing are part of the feature.

## Backend

- **Framework primitive without its pattern.** For session, permission, lock, ownership,
  transaction or background-job code, follow how Frappe itself uses the primitive; grep for
  real usage before accepting one read off a signature. *Precedent: `frappe.set_user` in a
  request handler logged the clicking user out.*
- **Guest-reachable code.** Grep `allow_guest=True` under `insights/` to name the doors.
  New code reachable from one, or a new door, names its gate. Guest-reachable code that reads
  user data, or a write into a customer's source database, is a blocker. *"i don't want
  to create tables in the database, that's a hard no"*.
- **Permissions.** `ignore_permissions=True`, a new whitelisted method, or a widened
  visibility rung needs the gate named. Apply the framework's permissions rather than
  invent a per-user scheme. A narrow endpoint beats a widened grant. Do not flag a check
  an earlier layer already enforces — role permissions run before the controller hook.
- **Known defect classes.** The 2026-08 audit found five recurring classes. When the diff
  touches one, check that class:
  1. A document built from the request body instead of the stored row.
  2. Raw SQL or an expression sandbox reached with user input.
  3. `v-html` on user text or server text.
  4. An outbound request to a user-chosen URL. See
     `docs/adr/outbound-http-to-user-chosen-urls.md`.
  5. A connection error echoed with the credential in it.

  A new engine or backend meets the trust bar the old one already paid.
- **A security fix describes the rule, not the attack.** Branch, commits, test names and
  comments.
- **Thin API, logic in the doctype.** Keep core logic on the server, not the client.
- **Stored shape changed.** A doctype field, or the JSON in `config`, `operations` or
  `items`, changed without a patch in `insights/patches.txt` — existing documents break.
  Insights v3 has users, so the default is non-breaking; say what happens to saved documents
  and older clients. A patch must touch only its own rows and must not rewrite
  `creation`/`modified`. A fix must not ask users to edit their own data.
- **Duplicated declaration.** The same fields added to two doctypes, or a purpose-built log
  beside a general one. *"can we create a single new doctype instead of adding same fields
  to two different doctypes?"*
- **Error messages.** Specific to the case, and covering the other paths that raise them.
  One bad input must not take down the whole feature.
- **Redundant work.** Repeated requests or re-renders on open or edit, a database call in
  a loop, a live-source query for a UI convenience, an uncached read on the hot path.
  *"just creating a new chart made this many requests, it flickered twice"*. Load on the
  live source database is the cost that counts; one extra query is not.
