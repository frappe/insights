# 28 — Which lockfile is the runtime version authority?

Type: grilling
Status: open
Blocked by: none — the check that makes this loud is in; the second authority is not removed

## Question

[Ticket 07](07-runtime-version-policy.md) is resolved and states that framework's
lockfile is the version authority for the whole runtime closure — Vue, frappe-ui,
and everything they drag in — and that "versions reconcile at build time, so
runtime skew is unreachable".

Skew turned out to be reachable. Framework declares `"frappe-ui":
"link:./frappe-ui"`, so the closure walk crosses into `frappe-ui/node_modules`,
a tree governed by frappe-ui's *own* lockfile. Two lockfiles decide closure
versions, and only one of them is the authority the ticket names.

## Evidence

Every island using frappe-ui died at import on `desk-islands`:

```
The requested module '@vueuse/shared' does not provide an export named 'toArray'
```

`apps/frappe/frappe-ui/node_modules` had drifted from frappe-ui's lockfile:
`@vueuse/shared@10.11.1` sat hoisted where the lockfile says `14.1.0` belongs.
`reka-ui` (declaring `^14.1.0`) and its inlined `@vueuse/core@14.1.0` both
resolved to that one wrong directory, so the closure walk saw a single copy, ran
no version comparison, and published an import map that broke at runtime.

Two facts make this a design question rather than a one-off repair:

- **The repair was `yarn install --check-files` in a checkout framework does not
  govern.** `--frozen-lockfile` reported "Already up-to-date" against the stale
  tree. No `package.json` or `yarn.lock` under framework's control was wrong, so
  no change under framework's control could have prevented it.
- **A `resolutions` entry cannot fix this class.** `@vueuse/core@10.11.1` pins
  `@vueuse/shared@10.11.1` and `@vueuse/core@14.1.0` pins `14.1.0`. Two exact
  pins, no satisfying single version — two copies are genuinely required, and the
  collision lives in a lockfile `apps/frappe/package.json` does not reach.

Five other packages were off-lockfile the same way
(`@tiptap/extension-code-block-lowlight`, `engine.io-client`, `prettier`, `ws`).
They happened not to be load-bearing this time.

## What is already done

The build no longer fails silently. `island/build-runtime.mjs` checks the
declared range on every crossing rather than only when node resolution returns
two different directories, and exits 1 naming the specifier, both versions, the
importer and the path. `island/verify-runtime.mjs` additionally checks that each
module exports the names its importers ask for, following `export *` through the
map — a check that does not depend on manifests being honest.

That makes each instance loud. It does not remove the second authority, and a
loud build failure on a developer's machine is still a blocked build.

## The question to settle

Does ticket 07's "framework's lockfile is the version authority" survive
`link:./frappe-ui`, or does the closure need a different rule?

Options, with what each costs:

- **Make frappe-ui a normal npm dependency.** Restores one lockfile and one
  authority, which is what ticket 07 assumed. Costs the development loop that
  the linked checkout exists to serve — editing frappe-ui and seeing it in an
  app without publishing.
- **Vendor the closure's resolution into framework.** Framework's lockfile
  declares the runtime closure's versions explicitly rather than discovering
  them by walking a linked tree. Honest about the authority; a second list to
  maintain, and it drifts from frappe-ui's real dependencies.
- **Accept two authorities and make the seam explicit.** The current position by
  default: the walk is allowed to cross, the checks make a bad crossing loud.
  Cheapest, and it leaves ticket 07's claim overstated — worth amending the
  ticket rather than leaving it as written.
- **Bound the walk at the link.** Treat a linked package as a closure leaf and
  require it to declare what it contributes. Removes the crossing entirely;
  needs frappe-ui to publish that declaration, which is work in another repo.

Whatever is chosen, ticket 07's wording needs amending: "runtime skew is
unreachable" is now known to be false as stated.
