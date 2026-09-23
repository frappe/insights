# Name things in the host's words

Date: 2026-09-10

## Status

Accepted.

## Context

Frappe has words for nearly everything Insights names, in the places a reader already looks: field labels, roles, exceptions, `view` / `form` / `route`. A metaphor reads well in the file that coined it and nowhere else, so a reader has to learn a private vocabulary before they can follow a permission check.

## Decision

**Name things by what they are, in the words the host platform already uses — its fields, roles, exceptions, view/form/route. Never by metaphor. When a concept has no host word, pick the plainest noun and use it for one concept only.**

Three corollaries:

- A Frappe idiom outranks a better-sounding coinage: a Check, `frappe.DoesNotExistError` and `Not Found`, `route`, and `is_standard` + `name` as the shape shipped content is identified by, because that is Report's and Print Format's shape.
- One word, one concept, in every layer it appears — field, identifier, type, test file, UI string. A word that means two things means neither.
- A word the framework owns is borrowed, not re-coined. Island, Host, Claim and Action are defined in `apps/frappe/ui/island/decisions`, and that is their authority.

Rejected: keep a metaphor and define it in the glossary. A definition does not travel with the identifier. `data_authority` was documented and still read as a person with a title; the reader who met it in `permission_user.py` had to go and look, every time.

## Consequences

The glossary carries the rule's vocabulary — Visibility and its four levels, Run as owner, View, Builder, Route, Is Standard, Not Found, and Island, Host, Claim and Action as the framework's — with the retired words on the `_Avoid_` lines, so the next agent that reaches for `rung` is told what to say instead.

## Stays unrenamed on purpose

- **The granularity ladder in `chart_drill.py`.** Grains are ordered by the span they cover and a derived grain climbs them, so the ladder is the thing itself, not a picture laid over a permission model.
- **The e2e `viewer` persona** (`frontend/e2e/.auth/viewer.json`, `permissions.spec.ts`). A persona is a person with read access and no Insights role. "View user" names nobody.
- **`insights.api.authoring`.** The module is the endpoints the Builder writes through, and it is the counterpart of `api/view.py`. Naming it `builder` would name the client instead of the surface it serves.
