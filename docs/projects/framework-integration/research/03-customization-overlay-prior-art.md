# Prior art: vendor-shipped content + site customization + flowing updates

Research for the framework-integration effort, 2026-08-04. Question: when a vendor
ships dashboards as synced documents and a site customizes them, is an
**item-keyed structural overlay** (option ii) a bounded, proven pattern — or does
it decay into merge-conflict machinery, making the **whole-document fork /
customize-then-freeze** (option i) the safer call?

Method: primary sources only — official docs, source code (Frappe read locally),
and first-party issue trackers. Each section answers: what the overlay is keyed
on; what happens when upstream deletes/renames a key; documented pains; reset and
diff UX; and whether the mechanism stayed bounded.

---

## 1. Grafana provisioned dashboards

**Model: whole-document fork, not an overlay.** There is no merge at all.

- **Keying.** Whole dashboards, keyed on the dashboard **UID**: "If the dashboard
  in the JSON file contains an UID, Grafana updates the dashboard with that UID
  in the database."
- **Update-vs-edit semantics.** With `allowUiUpdates: false` (default), UI saves
  are refused with a *"Cannot save provisioned dashboard"* dialog — the escape
  hatch is copying the JSON out (a manual Save-As fork under a new UID). With
  `allowUiUpdates: true`, UI edits persist to the DB — but "Grafana always
  overwrites the database dashboard with the one from the provisioning file.
  Grafana ignores the `version` property in the JSON file, even if it's lower
  than the dashboard in the database." Whole-document last-writer-wins; the file
  wins whenever it changes.
- **Upstream delete.** With `disableDeletion: false`, removing the provisioning
  source deletes the dashboard (including any UI edits saved onto it);
  `disableDeletion: true` keeps it as an orphaned local copy.
- **Documented pains.** Years of issues about exactly the tension we're studying:
  [#11778](https://github.com/grafana/grafana/issues/11778) ("We have to
  manually copy and paste the dashboard JSON from the UI so we can commit it"),
  resolved by the `allowUiUpdates` opt-in
  ([PR #19820](https://github.com/grafana/grafana/pull/19820));
  [#20211](https://github.com/grafana/grafana/issues/20211),
  [#37679](https://github.com/grafana/grafana/issues/37679) (read-only bypass via
  JSON tab treated as a bug), [#111525](https://github.com/grafana/grafana/issues/111525)
  (2025 regression). The pain is *about the fork boundary* (can't edit / edits
  clobbered), never about merge conflicts — because there is no merge.
- **Reset/diff UX.** Reset = re-provision (file overwrites DB). No diff UI for
  provisioned-vs-edited.
- **Verdict: bounded, by refusing the problem.** Grafana never grew merge
  machinery; it shipped a binary switch and lets the file clobber. The recurring
  user complaint is that customize-then-freeze forces manual JSON round-trips.

Sources: [Provisioning docs](https://grafana.com/docs/grafana/latest/administration/provisioning/),
issues linked above.

## 2. Odoo view inheritance

**Model: structural patch — and the cautionary tale.**

- **Keying.** Child views reference a parent (`inherit_id`) and carry
  "inheritance specs": **XPath expressions** or element-by-attributes matches
  (`<field name="x" position="after|before|inside|replace|attributes|move">`).
  The key is a *structural locator into the parent's XML tree*, not a stable
  vendor-assigned id.
- **Upstream delete/rename.** A spec that no longer matches is a **hard error**:
  `ValueError: Element '<xpath expr=...>' cannot be located in parent view`. The
  view (and often the whole screen/module load) breaks. This error has a decade
  of forum threads across every version
  ([odoo #29226](https://github.com/odoo/odoo/issues/29226),
  [forum example](https://www.odoo.com/forum/help-1/error-msg-element-xpath-expr-cannot-be-located-in-parent-view-213940),
  [upgrade-triggered example](https://www.odoo.com/forum/help-1/category-form-view-inheritance-problem-cannot-be-located-in-parent-view-upgrade-module-error-only-180770)).
- **Documented pains.** The official upgrade docs put adaptation on the
  customizer: "if a change introduced by a new version breaks a customization,
  it is the responsibility of the maintainer of your custom module to make it
  compatible" ([upgrade.rst](https://github.com/odoo/documentation/blob/18.0/content/administration/upgrade.rst)).
  Odoo sells an upgrade service partly to absorb this; Studio customizations get
  SLA-covered upgrades precisely because raw view patches don't survive alone.
  The ecosystem also grew *extension machinery* for the patch language itself
  (OCA's [`base_view_inheritance_extension`](https://pypi.org/project/odoo-addon-base-view-inheritance-extension)).
- **Reset/diff UX.** None built in; you disable the inheriting view or fix the
  XPath by hand.
- **Verdict: decayed.** This is the system that validates the fear — but note
  *why*: the keys are positional/structural (XPath into someone else's tree) and
  the failure mode is an exception, not a degrade. It is not evidence against
  overlays keyed on stable vendor-owned ids.

Sources: [view_records.rst](https://github.com/odoo/documentation/blob/18.0/content/developer/reference/user_interface/view_records.rst),
upgrade docs and issues above.

## 3. Kubernetes Kustomize + strategic merge patch

**Model: item-keyed structural overlay — the strongest pro case, with an asterisk.**

- **Keying.** Strategic merge patch keys list items on a schema-declared
  **`patchMergeKey`** (e.g. containers merge by `name`); maps merge by field
  name. Deletion is an explicit directive in the patch: `$patch: delete` under
  the merge key, and `$deleteFromPrimitiveList/<key>` for scalar lists
  ([SMP design doc](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-api-machinery/strategic-merge-patch.md)).
  JSON Patch (RFC 6902) is the fallback for types without merge keys — and it is
  positional (paths with array indices), i.e. it reintroduces the Odoo problem.
- **Upstream delete/rename.** A patch entry whose key no longer exists in the
  base simply *adds* that item (merge semantics: patch entries not found are
  appended). Nothing errors; the overlay degrades to noise rather than breakage.
  Kustomize as a build tool errors only when a whole patch *target resource*
  can't be found.
- **Bounded or decayed?** Mixed, and instructive. The keyed-merge idea itself
  proved durable — it is how every `kubectl apply` works and how Kustomize
  overlays run enormous fleets. But the mechanism *did* grow machinery: the
  directive vocabulary (`$patch: replace/delete/merge`, `$setElementOrder`,
  `$retainKeys`) accreted over years, and the design doc now opens with "This
  document is old and probably obsolete. Server-side Apply is the new solution."
  Server-Side Apply replaced client-side three-way merge with **field ownership
  tracking (`managedFields`) and explicit conflict errors** — i.e. Kubernetes
  eventually needed ownership metadata and a conflict protocol once *multiple
  writers* patched the same objects.
- **The asterisk that saves us.** SSA's conflict machinery exists because K8s has
  N independent controllers writing the same object. Our case has exactly two
  layers (app base, one site overlay) with a fixed precedence. Two-layer keyed
  overlay with fixed precedence is the part of the K8s story that stayed simple;
  conflict machinery arrived only with N-writer field ownership.
- **Reset/diff UX.** Delete the overlay file; `kustomize build` output is
  diffable against base — good, but that's VCS-adjacent tooling we wouldn't have.

Sources: [SMP design doc](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-api-machinery/strategic-merge-patch.md),
[Kustomize glossary](https://kubectl.docs.kubernetes.io/references/kustomize/glossary/).

## 4. WordPress child themes (+ WooCommerce template overrides)

**Model: file-level fork by filename — customize-then-freeze with a staleness nudge.**

- **Keying.** Whole files by **path/filename**: "you have the option to overwrite
  any template, part, or pattern that exists in the parent theme by adding a
  file of the same name in your child theme"
  ([Child Themes handbook](https://developer.wordpress.org/themes/advanced-topics/child-themes/)).
  `functions.php` is the one additive layer (both load, child first).
- **Upstream update.** The overridden file **freezes**: parent updates to that
  template never reach the child copy. WooCommerce documents the consequence as
  a first-class product feature — the **System Status "outdated templates"
  warning**, driven by per-template version headers. The remedy is manual:
  back up your override, copy the new default template, re-apply your
  customizations. The docs concede "it can be time-consuming. This is why we try
  to avoid changing WooCommerce templates"
  ([Fixing outdated WooCommerce templates](https://developer.woocommerce.com/docs/theming/theme-development/fixing-outdated-woocommerce-templates)).
- **Documented pains.** Exactly the staleness problem option (i) accepts:
  overrides silently miss upstream fixes until the nudge fires; the vendor's
  main mitigation is *changing templates less often*.
- **Reset/diff UX.** Delete the child file = reset. The version-header nudge is
  the closest thing to diff UX; actual diffing is manual.
- **Verdict: bounded but lossy.** Never grew merge machinery in 15+ years; the
  cost is permanent manual re-merge labor, pushed onto the customizer, plus a
  vendor incentive to not improve shipped templates.

## 5. Android Runtime Resource Overlays (RRO)

**Model: item-keyed value overlay with a declared contract — bounded by design.**

- **Keying.** Resource **name** (Android ≤10: identically-named resource in the
  overlay; Android 11+: an explicit `overlays.xml` target→value map via
  `android:resourcesMap`). Android 10+ adds the **`<overlayable>`** contract: the
  target app declares *which* resources overlays may touch — the vendor curates
  the customization surface ([RRO docs](https://source.android.com/docs/core/runtime/rros)).
- **Upstream delete/rename.** Not explicitly documented; the docs state "An RRO
  can only be used to change the values for an existing resource," implying an
  overlay entry for a removed resource simply has nothing to attach to (overlay
  idmap generation drops unmatched entries). Evidence thin here — but there is
  no documented conflict/merge mechanism at all, and shipping OEM overlays
  across yearly Android upgrades is routine practice.
- **Verdict: bounded.** Key insight for us: it stays bounded because it is
  *value-override only* (no structural moves), and because `overlayable` makes
  the customizable surface an explicit vendor-owned contract.

## 6. Frappe's own mechanisms (read from source)

### 6a. Property Setter / Customize Form — a 15-year-old item-keyed overlay that stayed bounded

- **Keying.** One row per **(doctype, fieldname-or-rowname, property)** — the
  autoname is literally `"{doctype}-{field}-{property}"`
  (`frappe/custom/doctype/property_setter/property_setter.py`). Customize Form
  writes these plus Custom Field rows (keyed by fieldname, positioned via
  `insert_after`).
- **Merge rule.** At meta-load, `Meta.apply_property_setters()`
  (`frappe/model/meta.py:423`) loops the setters and `set()`s each property onto
  the matching field. Deterministic, last-layer-wins, per-key.
- **Upstream delete.** The load loop is `for d in self.fields: if d.fieldname ==
  ps.field_name: ... break` — a setter whose field is gone **matches nothing and
  is silently skipped**. No error, no conflict; the orphan row lingers harmlessly.
  Ordering degrades the same way: `sort_fields()` filters `field_order` to
  `fieldname in self._fields` (stale entries dropped) and a custom field whose
  `insert_after` anchor vanished falls back positionally. *Graceful decay
  everywhere, exceptions nowhere.*
- **Documented pains.** [frappe/frappe#25458](https://github.com/frappe/frappe/issues/25458)
  (sync_on_migrate semantics for exported customizations),
  [#11967](https://github.com/frappe/frappe/issues/11967) (older sync bugs) — the
  complaints are about *sync plumbing*, not about the overlay model itself. The
  mechanism has run on every Frappe site since ~2012 without growing conflict
  machinery.
- **Reset/diff UX.** Customize Form's "Reset to defaults" deletes the setters;
  the Property Setter list *is* the diff (each row is one legible override).

### 6b. Standard Workspaces — the whole-document clobber pain

Upstream sync (`frappe/modules/import_file.py`) is hash/timestamp-based
whole-document import: when the shipped JSON changes, the DB record is
overwritten. Site edits to standard workspaces historically lived in that same
record → clobbered on migrate. Public evidence:
[#36399](https://github.com/frappe/frappe/issues/36399) (workspaces lost on
update to v16.3), [#36424](https://github.com/frappe/frappe/issues/36424)
(desktop icons/workspaces deleted on bench update),
[#37328](https://github.com/frappe/frappe/issues/37328) (can't customize as
documented). This is what *no* customization layer looks like: option (i)
without the fork.

### 6c. Workspace Customization (local `desk-islands` branch) — first-party experiment, both options tried

The strongest evidence in this survey, because it is our own team running exactly
this experiment on exactly this platform
(`frappe/desk/doctype/workspace_customization/workspace_customization.py`):

- The first implementation was **option (ii)**: an item-keyed `content_delta`
  with `hidden_blocks` / `added_blocks` / `block_overrides`, keyed on a semantic
  block key (`"{type}:{label}"`, e.g. `shortcut:My ToDos`), merged onto the live
  base at render time.
- Commit `78e4b14f74` ("refactor: remove logic to merge workspace contents")
  **deleted the content merge** and replaced it with a **snapshot**: "Content is
  a snapshot, not a delta: the site's arrangement is authoritative … so app
  changes to this workspace's layout do not flow through once it has been
  customized."
- But it **kept the delta model for everything that isn't layout**: roles are
  stored as `added_roles`/`removed_roles` against the live base ("so app changes
  to the base roles keep flowing through"), and icon/color/visibility/sequence
  are per-property overrides applied over the live base.
- Reset UX: `reset_workspace_customization` deletes the overlay doc — pristine
  base returns for free, because the base was never written.

The landing point: **delta for keyed scalar/set properties, freeze for free-form
layout**. The part that got abandoned was merging an *editor.js block layout* —
an ordered, position-sensitive, user-rearrangeable list — not keyed item
overrides as such.

## 7. Dashboard products

### Power BI template apps — the closest commercial analog

Vendor ships packaged reports/dashboards; customer installs, customizes,
receives updates ([install/distribute docs](https://learn.microsoft.com/en-us/power-bi/connect-data/service-template-apps-install-distribute)):

- Customization warning, verbatim: "any changes you make will be overwritten
  when you update the app with a new version, unless you save the items you
  changed under different names" — i.e. **the supported customization mechanism
  is Save-As fork**.
- On update the installer chooses: update workspace+app / update workspace only /
  install a fresh copy. Overwrite semantics are **per-document, keyed by
  identity**: "Overwriting never deletes new reports or dashboards you've added
  to the workspace. It only overwrites the original reports and dashboards with
  changes from the original author." Parameters/auth (the config layer) survive.
- So Power BI's answer to our exact question: whole-document ownership per item
  — vendor documents get vendor updates and lose local edits; site-added
  documents are untouchable; config values persist. No structural merge anywhere.

### Salesforce managed packages — attribute-level customize-then-freeze

The ISVforce packaging guide defines per-attribute editability classes
([component attributes](https://developer.salesforce.com/docs/atlas.en-us.packagingGuide.meta/packagingGuide/packaging_component_attributes.htm)):
for "Both Subscriber and Package Developer Can Edit" attributes, "developer
changes are only applied to new subscriber installs. This approach prevents a
package upgrade from overwriting changes made by the subscriber." Note the
mechanism: the moment a subscriber edits an attribute, **upstream flow stops for
that attribute** — freeze at attribute granularity, no merge, no conflict UI.
(Upgrade behavior for packaged reports/dashboards specifically is not spelled
out on that page — evidence thin there.)

### Metabase serialization

Keyed on stable **`entity_id`** (NanoID) per item; import semantics: "If you
import an item with an `entity_id` that already exists in your target Metabase,
the import will overwrite the existing item"
([serialization docs](https://www.metabase.com/docs/latest/installation-and-operation/serialization)).
One-way clobber, no merge, no conflict handling; local-edit protection is "don't
edit the synced copies."

### Superset import/export

Keyed on **UUID**; `overwrite=true` replaces the whole asset, otherwise
conflicting assets are skipped
([docs](https://superset.apache.org/admin-docs/configuration/importing-exporting-datasources/),
[#22127](https://github.com/apache/superset/issues/22127),
[discussion #31306](https://github.com/apache/superset/discussions/31306)).
Same shape as Metabase: whole-document, id-keyed, clobber-or-skip.

**Pattern across all four dashboard products: not one of them attempts a
structural merge of vendor updates into locally edited dashboards.** The design
space they occupy is: clobber / skip / fork-under-new-name / freeze-per-attribute.

## 8. VS Code settings layering

**Model: the cleanest keyed overlay in wide deployment.**

- **Keying.** Flat, stable **setting IDs** (`workbench.colorTheme`) across fixed
  precedence layers: default < user < workspace < folder, with language-specific
  variants; "later scopes override earlier scopes." Primitives/arrays are
  replaced whole; object-valued settings are shallow-merged by key
  ([settings docs](https://code.visualstudio.com/docs/configure/settings)).
- **Upstream delete/rename.** A key that no longer exists in defaults is simply
  ignored at resolution time (the editor flags unknown keys in the JSON as a
  lint, not an error — observed behavior; the docs page doesn't spell this out,
  so weigh accordingly). Renames are handled by shipping deprecation aliases in
  the schema, i.e. the vendor absorbs rename cost.
- **Reset/diff UX.** Per-key "reset to default" gear action; the "modified"
  filter in the settings UI is an exact, legible diff of your overlay.
- **Verdict: bounded, decades-scale.** Works because (a) keys are stable
  vendor-owned ids, (b) precedence is fixed and total, (c) values are replaced,
  not merged (except one shallow, keyed object-merge), (d) there is no ordering
  to fight over.

---

## Verdict

**Item-keyed overlay is a bounded, proven pattern — under specific conditions
that the surveyed failures make legible.** The systems that stayed bounded for a
decade-plus (Property Setter, VS Code settings, RRO, the keyed half of strategic
merge patch) share four properties:

1. **Stable, vendor-owned keys** (fieldname, setting ID, resource name, merge
   key) — never positional/structural locators. Odoo is the decay case, and its
   keys are XPaths into a tree the vendor is free to restructure.
2. **Fixed two-layer precedence, per-key replace semantics.** No three-way
   merge, no value-level merging inside an item. Kubernetes only grew conflict
   machinery (Server-Side Apply, `managedFields`) when it had N independent
   writers; a base + one site overlay never hits that regime.
3. **Graceful decay on upstream delete:** an orphaned override matches nothing
   and is skipped (Property Setter's `for … if fieldname == …: break` loop is the
   canonical implementation). The moment an unmatched key becomes an *error*
   (Odoo) the upgrade story dies.
4. **A declared customization surface** helps (RRO's `<overlayable>`): the vendor
   states which knobs are overridable, which bounds what upstream must keep
   stable.

**Where the fear is real: ordering and free-form layout.** The one first-party
data point we own — the desk-islands Workspace Customization — built exactly
option (ii) for block layout and retreated to a snapshot, while *keeping* keyed
deltas for roles and scalar properties. Ordered, position-sensitive,
user-rearrangeable content is where "hide/add/override" quietly turns into "merge
two orderings," and no surveyed system solved that; they all either freeze
(WordPress, Power BI, Salesforce attributes, desk-islands content) or clobber
(Grafana, Metabase, Superset).

**Closest analog: Power BI template apps** (vendor-shipped analytics content,
customer customization, vendor update stream). Its track record says: per-item
identity keying works; "overwrite originals, never touch site-added items, keep
the config layer" is acceptable to a very large market; and the documented cost
is the standing "your edits will be overwritten unless you Save-As" caveat — the
staleness/fork problem of option (i), which its users simply live with.
**Closest mechanism analog: Frappe's own Property Setter** — same platform, same
migrate cycle, fifteen years of item-keyed overlays with zero conflict machinery,
because deletes degrade silently and every override is one legible row.

**Recommendation shape the evidence supports:** split the surface the way
desk-islands ultimately did, rather than choosing (i) or (ii) wholesale —

- **Overlay (option ii) for keyed, order-free operations:** hide item, add
  site item, override filter defaults, swap a chart behind an item id, role/
  visibility deltas. Precondition: shipped dashboards give every item a stable
  id that the vendor treats as API (rename = new id + deliberate migration;
  our shipped JSON gives us this for free), and orphaned overlay entries are
  skipped silently with a "reset customization" escape hatch.
- **Snapshot/freeze (option i) for layout order/positioning** the moment the
  site rearranges — with the WooCommerce-style staleness nudge (base changed
  under your frozen layout) as the recovery UX.

**Thin-evidence disclosures:** RRO's removed-resource behavior is inferred from
"can only change values for an existing resource," not stated; Salesforce's
packaged report/dashboard upgrade behavior specifically is not documented on the
cited page; VS Code's unknown-key handling is observed editor behavior, not in
the settings doc; Odoo's practice of disabling broken custom views during
managed upgrades is folklore I did not find stated in a primary source and is
omitted from the argument above.
