# Runtime version policy

Type: grilling
Status: resolved

## Question

Ticket 02 settled that framework provides Vue and frappe-ui as page singletons
and Insights builds against them as externals. That makes version ownership a
contract question.

- How does Insights declare which frappe-ui version it needs, and how is that
  checked?
- What happens on skew — framework ships a newer frappe-ui than Insights was
  built against, or older? Fail loudly, degrade, or refuse to mount?
- Does Insights' release cadence now follow framework's frappe-ui version, and
  is that acceptable?
- Does the singleton rule reach Vue-frontend apps (CRM-class), which bundle
  their own runtime today, or is it desk-only?
- Which packages are in the shared set — Vue, frappe-ui, echarts, anything
  else?

Consequence already visible: Insights ends up with two build targets from one
source — the standalone SPA at `/insights`, which bundles everything, and the
desk island, which externalises the shared set.

This ticket gates the build and mount-API tickets.

## Answer

Standing input: the person driving this map can make decisions on the
framework side too. Where a runtime check and a framework guarantee both
solve a problem, prefer the guarantee.

**The shared set is one closure, not a list.** Framework's lockfile is the
version authority for Vue, vue-router, frappe-ui, and everything frappe-ui
drags in (echarts, reka-ui, all 77 dependencies). No package is negotiated
individually. Insights drops its own pins on that closure — the `echarts`
dependency and the `reka-ui` resolution in `frontend/package.json` go away.
If Insights needs a different version of something in the closure, the fix
is a PR to framework.

**Versions reconcile at build time, not runtime.** Insights declares no
frappe-ui range and framework checks none. The island is built against
framework's actually-installed runtime, so a second version never exists
and runtime skew is unreachable. No handshake, no degrade path, no
refuse-to-mount logic.

**Skew becomes a build failure, contained by freeze-per-major.** Within a
framework major, the shared runtime surface is append-only: frappe-ui can
be patched and extended, never broken. Breaking bumps ride framework
majors. The whole compatibility policy is one line: an Insights release
targets a framework major and builds against any patch of it. No
compatibility matrix.

**The rule reaches Vue-frontend apps as "at most one framework runtime per
page", not "one Vue per page".** The runtime loads on demand wherever an
island mounts — desk or a CRM-class page. The host app's own bundled Vue is
untouched; the shadow boundary keeps the two apart. The embed contract is
therefore identical across desk and Vue apps. Full convergence (host apps
externalising their own runtime against framework's) is the direction
freeze-per-major enables, recorded as direction — not a requirement this
contract waits on.

**Both Insights build targets follow one version.** The standalone SPA at
`/insights` and the desk island build from one source against the same
frappe-ui — framework's. Otherwise the two targets drift (today they
already would: beta.24 in Insights, beta.29 in framework's checkout).

Fact found while resolving: the framework-provided runtime does not exist
yet. The POC island pipeline (`esbuild/build-islands.mjs`) builds each
island as a self-contained IIFE — Vue and frappe-ui bundled in, no
externals — and framework `develop` has no frappe-ui dependency at all
(the POC adds it as a `link:` to a gitignored checkout). Shipping the
runtime as a real, loadable artifact is a framework deliverable; its build
mechanics belong to the build-ownership ticket.
