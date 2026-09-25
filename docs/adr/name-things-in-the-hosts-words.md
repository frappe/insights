# Name things in the host's words

Date: 2026-09-10

## Status

Accepted.

## Context

Frappe already has a word for nearly everything Insights names. The words are where a reader already looks: field labels, roles, exceptions, `view` / `form` / `route`. A metaphor is clear in the file that introduced it and unclear everywhere else. A reader must then learn a private vocabulary before they can follow a permission check.

## Decision

**Name a thing by what it is, in the words the host platform already uses: its fields, roles, exceptions, and view/form/route. Never use a metaphor. When a concept has no host word, use the plainest noun, and use it for that one concept only.**

This has three consequences for naming:

- A Frappe idiom wins over a better-sounding new word. Examples: a Check; `frappe.DoesNotExistError` and `Not Found`; `route`; and `is_standard` + `name` to identify shipped content, because Report and Print Format identify it that way.
- One word means one concept in every layer: field, identifier, type, test file and UI string. A word with two meanings is clear in neither.
- A word the framework owns is used as the framework defines it, not redefined. Island, Host, Claim and Action are defined in `apps/frappe/ui/island/decisions`, which is their authority.

Rejected: keep a metaphor and define it in the glossary. The definition does not go with the identifier. `data_authority` was documented, but it still read as a person with a title. A reader who found it in `permission_user.py` had to look it up every time.

## Consequences

The glossary holds the words this rule produced: Visibility and its four levels, Run as owner, View, Builder, Route, Is Standard, Not Found, and the framework's Island, Host, Claim and Action. The retired words are on the `_Avoid_` lines, so an agent that reaches for `rung` learns which word to use instead.

## Kept on purpose

- **The granularity ladder in `chart_drill.py`.** Grains are ordered by the time span they cover, and a derived grain moves up them. So "ladder" describes the thing itself. It is not a metaphor for a permission model.
- **The e2e `viewer` persona** (`frontend/e2e/.auth/viewer.json`, `permissions.spec.ts`). A persona is a person, here one with read access and no Insights role. "View user" does not name a person.
- **`insights.api.authoring`.** The module holds the endpoints the Builder writes through, and it is the counterpart of `api/view.py`. The name `builder` would name the client that calls the endpoints, not what they do.
