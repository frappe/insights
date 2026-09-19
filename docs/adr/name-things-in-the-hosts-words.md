# Name things in the host's words

Date: 2026-09-10

## Status

Accepted. Applied in full on `feat/islands` (`03f8efb67`..`2d44aed80`), names only, no logic changed.

## Context

The branch opened two seams at once — declared visibility and the island read path — and named both as it built them. What it reached for was metaphor: content sat on a `rung` of a `ladder`, declared an `audience`, ran with a `data_authority` held by an `author`, and a card was filled from a `feed`; authoring took a `seat`, and a reader came in through `one door`. Each word was coined in one file and then spread. `authority` alone reached a doctype field, a TypeScript type, four functions, a test suite and every string in the share dialog.

Frappe has words for nearly all of it, in the places a reader already looks: field labels, roles, exceptions, `view` / `form` / `route`. A metaphor reads well in the file that coined it and nowhere else, so a reader had to learn a private vocabulary before they could follow a permission check — and the API said `viewer` where the framework says `view`.

## Decision

**Name things by what they are, in the words the host platform already uses — its fields, roles, exceptions, view/form/route. Never by metaphor. When a concept has no host word, pick the plainest noun and use it for one concept only.**

Three corollaries the rename leaned on:

- A Frappe idiom outranks a better-sounding coinage: a Check labelled "Apply User Permissions", `frappe.DoesNotExistError` and `Not Found`, `route`, and `is_standard` + `name` as the shape shipped content is identified by, because that is Report's and Print Format's shape.
- One word, one concept, in every layer it appears — field, identifier, type, test file, UI string. A word that means two things means neither.
- A word the framework owns is borrowed, not re-coined. Island, Host, Claim and Action are defined in `apps/frappe/ui/island/decisions`, and that is their authority.

Rejected: keep a metaphor and define it in the glossary. A definition does not travel with the identifier. `data_authority` was documented and still read as a person with a title; the reader who met it in `permission_user.py` had to go and look, every time.

## Consequences

| old | new |
| --- | --- |
| `data_authority` Select (`Viewer` / `Author`) | `apply_user_permissions` Check, label "Apply User Permissions" |
| Author (the value, in code and strings) | Owner (`doc.owner`) |
| `slug`, `set_slug`, `_by_slug` | `route`, `set_route`, `_by_route` |
| `standard_id`, `_by_standard_id` | dropped: `is_standard` + `name` |
| visibility value `Specific Roles` | `Roles` |
| `insights/api/viewer.py`, `insights.api.viewer.*` | `insights/api/view.py`, `insights.api.view.*` |
| `RUNGS`, `OPEN_RUNGS`, `rung_of()` | `VISIBILITY_LEVELS`, `OPEN_LEVELS`, `visibility_level()` |
| `check_audience_widening()` | `validate_visibility()` |
| `name_the_author_at_the_public_rung()` | `validate_public_permissions()` |
| `cascade_public_data_authority()` | `update_linked_charts_permissions()` |
| `public_dashboard_carrying()` | `public_dashboards_linking()` |
| `check_authoring_seat()` | `has_insights_role()` |
| `can_edit`, `can_duplicate` | `can_write`, `can_copy` |
| `ContentNotAvailableError`, `not_available()` | `frappe.DoesNotExistError`, `not_found()` |
| `dashboard/viewer.ts`, `useSavedDashboard`, `ViewerDashboard*` | `dashboard/view.ts`, `useDashboardView`, `DashboardView*` |
| `dashboard/authoring.ts`, `useDashboardAuthoring`, `AuthoredDashboard` | `dashboard/builder.ts`, `useDashboardBuilder`, `DashboardInBuilder` |
| `charts/chart_read.ts`, `useSavedChart`, `ChartFeed` | `charts/chart_view.ts`, `useChartView`, `ChartSource` |
| `ViewerChart.vue`, `ViewerItem.vue` | `ChartView.vue`, `DashboardItemView.vue` |
| `setNavigationProvider`, `NavigationProvider` | `setRouter`, `Router` |
| `ViewerFilters` | `FilterValues` |
| `unavailable` state | `notFound` |
| "Who can view", "Whose data access", "Data Authority" | "Visible To", "Apply Permissions Of", "Apply User Permissions" |

Nothing is released, so the two visibility patches were rewritten to the new field names in place. `insights.patches.rename_visibility_fields` runs after them for sites that already migrated: it renames the fields, maps the Select values onto the Check, and no-ops when the old column is absent.

The glossary carries the rule's vocabulary — Visibility and its four levels, Apply User Permissions, View, Builder, Route, Is Standard, Not Found, and Island, Host, Claim and Action as the framework's — with the retired words on the `_Avoid_` lines, so the next agent that reaches for `rung` is told what to say instead.

## Stays unrenamed on purpose

- **The granularity ladder in `chart_drill.py`.** Grains are ordered by the span they cover and a derived grain climbs them, so the ladder is the thing itself, not a picture laid over a permission model.
- **The e2e `viewer` persona** (`frontend/e2e/.auth/viewer.json`, `permissions.spec.ts`). A persona is a person with read access and no Insights role. "View user" names nobody.
- **`insights.api.authoring`.** The module is the endpoints the Builder writes through, and it is the counterpart of `api/view.py`. Naming it `builder` would name the client instead of the surface it serves.
