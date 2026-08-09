# 30 — Who draws the desk page head?

Type: grilling
Status: resolved
Blocked by: none

## Question

The desk dashboard page shows two stacked headers. Desk's shell
(`make_app_page` in `dashboard_view.js`) draws its page head: breadcrumbs, the
generic title "Dashboard", and an empty actions area. Under it the island draws
its own header band (`DashboardIsland.vue`): the dashboard's real title, the
freshness stamp, refresh, the overflow menu, and the filter bar. The reader
sees a head that says nothing above a head that says everything.

Which surface owns the page head, and what does the island tell the shell?

## Evidence

- `dashboard_view.js` sets `page.set_title(__("Dashboard"))` on every show. It
  cannot do better: the title, the freshness, and the menu entries exist only
  after the island's fetch, and the mount envelope (ticket 04) carries nothing
  from island to shell except `on` events the host chose to listen for.
- The island's header band exists because the shell's head could not hold this
  content. Its comment in `DashboardIsland.vue` explains only why the band is
  not `sticky`, not why it exists.
- Desk's page head already has slots for all of it: title, primary/secondary
  actions, the menu. The legacy renderer on the same page uses them
  (`set_title`, `add_menu_item`).

## Direction (raised 2026-08-06)

- The dashboard title belongs in the desk page head, not in a second band.
- Refresh belongs there too.
- Possibly the whole page becomes the island: the shell stops calling
  `make_app_page`, and the island draws the one header the page has.

## Shape of the answer

Two candidate models, one must win — a band that holds "what the shell could
not" is not a model:

1. **The shell's head is the page head.** The island reports upward — title,
   freshness, actions — through the envelope, and draws no header of its own.
   The filter bar stays in the island (it is content, not chrome). This keeps
   ticket 02's ownership split intact but grows the contract: the `on`/`host`
   surface gains an island→shell channel that every future island will use.
   Ticket 29 (host ambient) is the adjacent gap; decide them coherently.
2. **The island is the page.** The shell mounts the island into the full
   content area with no page head, and the island's band becomes the only
   header. Cheaper contract, but the island then re-draws desk conventions
   (breadcrumbs, spacing, menu placement) inside a shadow root, and the legacy
   renderer on the same route still needs the old head — the shell must draw
   two different page shapes.

The answer must also say where the duplicate/edit status line and the denied
state's quiet message live once the band is gone.

## Answer

**The island owns the page. Desk draws no head on this route.** Neither of the
two candidate models won as written: the shell keeps its `frappe.ui.Page`, but
the page head is hidden and every header affordance — breadcrumbs, title,
freshness, refresh, overflow menu, filters — is drawn by the island in its own
tree.

Three facts decided it, all found by reading the shell rather than by argument:

- **Breadcrumbs are page-head markup, not navbar chrome.** `.navbar-breadcrumbs`
  lives in `page.html`, which `make_app_page` renders. A page that draws no head
  has no breadcrumb element to hide or fight — only one to redraw.
- **v16 already moved global chrome off the page.** `workspace_dock.js` carries
  the app logo, search, notifications and the user menu on the left rail, and
  says so itself: it replaces the page header's buttons. The body sidebar has its
  own collapse handle. The v16 navbar holds an announcement widget and nothing
  else. So the page head holds nothing a reader still needs.
- **The page object is the app frame's anchor, not just the head's.**
  `Sidebar.current_page()` reads `frappe.container.page.page`, and
  `page_allows_sidebar` / `page_allows_dock` return false without it. A route
  that skipped `make_app_page` would lose the sidebar and the dock along with
  the head. This is why "no page at all" is not the shape, and it is the one
  thing that cannot be seen from the outside.

**The framework gains one primitive:** `frappe.ui.Page.toggle_page_head(show)`.
A page that draws its own header says so; the page — and with it the sidebar and
dock — stays. `dashboard_view.js` turns the head off at page load, not after the
bridge answers: that answer is a round trip on a site with Insights, and the head
would sit on screen for all of it. The legacy renderer asks for it back when it
draws, so the two renderers keep their own chrome on one route.

**The trail reaches the island as ambient, not as a report upward.**
`build_host()` gains three fields, all generic to any island on any desk page:

- `host.breadcrumbs` — ancestors only, `[{ label, route }]`. Desk fills it from
  the previous route when that route was a workspace, the same rule
  `frappe.breadcrumbs.set_workspace` follows. A cold link yields an empty list
  and the header shows only the dashboard's name — an invented parent the reader
  never came through is worse than none.
- `host.navigate(route)` — desk routing, which the island cannot do for itself: a
  click inside a shadow root is retargeted to the island's host element, so
  desk's anchor delegation never matches it and a plain link would reload.
- `host.set_title(title)` — naming the browser tab, which `page.set_title` used
  to do here. It goes through desk rather than assigning `document.title`: desk
  keeps the unread count as a prefix over a title it remembers, and a direct
  write would be undone the next time that count moved.

Nothing is reported upward. The island draws its own title, so the island→shell
channel that both earlier models needed was never built.

**Rejected:** the report-upward channel (model 1) — a second renderer of island
state, and every future island would inherit it. Hiding only the duplicate
title (the first instinct) — it leaves the shell owning a head it cannot fill.
Building no page object (model 2 as first framed) — it silently takes the
sidebar and dock with it.

**Given up, deliberately:** a client script cannot `add_menu_item` on this route
(customization of Insights content goes through Insights, ticket 10); the page
indicator pill; and cmd-click on an ancestor crumb, because frappe-ui's
`Breadcrumbs` fires `onClick` without preventing an `href` from also navigating,
so a crumb is either a button or a link. The upstream fix is small — prevent the
default when both are given — and belongs in frappe-ui, not here.

## Comments

2026-08-06 — breadcrumbs examined, and they collapse the difference between
the two models.

Breadcrumbs are navbar chrome, not page chrome: `breadcrumbs.js` renders into
`.navbar-breadcrumbs` in desk's top bar, outside anything an island can own.
"Island is the page" loses nothing there. But logical crumbs
("Selling / Sales Performance") need two things:

- the workspace crumb — desk already guesses it from the last route
  (`set_workspace`), but only for non-Custom breadcrumb types; the shell's
  current `type: "Custom"` crumb skips that flow. Framework-owned, fixable in
  the shell.
- the title crumb — the title exists only after the island's fetch, so the
  island must report it upward. Late `frappe.breadcrumbs.add` re-renders fine;
  guard on the route as the renderer bridge does.

So the island→shell channel is required under **both** models: even a
full-page island cannot reach the navbar. Model 2's cheaper contract was its
one advantage, and the title report erases most of it — once the channel
carries a title for breadcrumbs, carrying actions for a page head is marginal.

2026-08-06 — the actions ride the same report, as data.

The island stays the authority on *what* can be done: capabilities
(`can_edit`, `can_duplicate`) arrive with its fetch, and the implementations
live on its state. The shell owns *where* it is shown. Shadow root, not
iframe — one JS realm — so the report carries callbacks:
`{ title, freshness, actions: [{ label, icon, onClick }] }`. The shell maps
them onto the page API it already has (refresh as the head's icon button, the
gated pair via `add_menu_item`) — the same way the legacy renderer populates
the same menu, so the chrome is desk-native.

The report is re-emittable, not one-shot: actions change after load, after a
duplicate starts, after it fails. The head is imperative (`clear_menu` +
re-add), so the shell redraws per report.

Two residues find better homes than the band gave them: the
"Duplicating… / failed" status line becomes a desk toast
(`frappe.show_alert`), fired by the shell around the callback it invoked;
freshness fits the head's indicator/sub-title slot. And the shape is
host-agnostic: the Vue-frontend embed (ticket 06) renders the same report
into its own chrome. This closes the "where does the status line live"
question the ticket body left open — pending only the model choice itself.
