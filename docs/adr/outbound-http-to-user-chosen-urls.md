# Outbound HTTP to user-chosen URLs

Date: 2026-08-11

## Status

Accepted. Implemented in `insights/http.py` alongside the webhook alert channel.

## Context

Webhook alerts are the first feature where a user hands Insights a URL and the
server makes the request. That is a different thing from a request to a URL
written in the code, and the difference is the permission model.

`Insights User` is the least privileged role the app has. It can create and
write an `Insights Alert`, and `send_alert` and `test_alert` are both
whitelisted. So the role can choose the destination and fire the request on
demand, which makes the response timing and the error text readable to it.
The same role cannot create an `Insights Data Source`, so the REST connector
that also makes outbound requests is out of its reach. The webhook URL is the
first outbound sink an `Insights User` can aim.

A server-side request forgery is what that buys an attacker. A URL that
resolves onto the server's own network reaches the database, the admin ports,
the redis instances and the cloud metadata service — all of them things the
role cannot reach through Insights, and several of them things nobody outside
the host can reach at all.

The framework does not solve this. `frappe.utils.get_request_session` applies
no address policy, and the `Webhook` doctype makes no address check either. It
does not need one today, because only a System Manager can configure it. That
is not our situation.

## Decision

One module, `insights/http.py`, owns outbound HTTP to any URL a user chose.
Anything with a user-supplied URL goes through `post_to_public_url`. A fixed
URL in the code — the dashboard preview service, for instance — does not.

Four rules define a permitted destination:

1. **https only.** Checked from the URL text, without a name lookup.
2. **Publicly routable addresses only.** Every address the name resolves to
   must satisfy `ipaddress.is_global`. One private answer refuses the name.
3. **No redirect.** A 3xx is an error, not a hop. Configure the final URL.
4. **No proxy.** The environment's proxy settings are ignored, and a proxy
   passed by a caller is refused.

The address check runs **in the connection**, not before the request. A urllib3
connection subclass resolves the name, refuses a non-public answer, and pins
the surviving address onto the socket. The hostname stays on the connection for
SNI and certificate verification, so pinning does not weaken TLS.

`validate_public_url` holds only rule 1, because it runs inside `validate()`.
A save must not wait on a resolver, and an address that resolves publicly at
save time proves nothing about send time. "Send test" is the button that
answers the question a user actually has.

## Consequences

**Rebinding is closed, and closing it costs private API.** Checking the address
before the request and then letting requests resolve the name again is a
check of one lookup and a connection to another. Doing it in the connection is
the only place where the address checked is the address used. That means
`HTTPSConnection._new_conn`, `_dns_host` and `pool_classes_by_scheme` —
three pieces of urllib3 that carry no compatibility promise.

The failure mode is what makes this dangerous: if a urllib3 upgrade renames
`_new_conn`, the subclass overrides nothing, nothing raises, and the defence
silently stops existing. `insights/tests/test_http.py` drives a request to the
socket to catch that. Match the refusal message in those tests, not just the
exception type — an unreachable socket raises the same type, so a bare
`assertRaises` stays green after the override comes unstuck.

**A deployment behind an egress proxy cannot deliver.** This is the real cost of
rule 4, and it is deliberate: a proxy resolves and connects for us, so there is
no address left here to check, and trusting the proxy to have checked is not a
policy. The connection error names it rather than leaving an operator to guess.
If a customer needs it, the answer is an allow-list of destinations, not a
trusted proxy.

**Ignoring the environment also drops netrc and `REQUESTS_CA_BUNDLE`.** The
netrc part matters: a user picks the host, so a matching netrc entry would hand
that host this server's credentials. That is worth more than reading an
operator's CA bundle from the environment.

**The address check is not an authorization check.** It stops a request onto
this server's own network. It does not stop a request to a public host the user
should not be talking to. If that becomes a requirement, it wants an
allow-list, and the allow-list belongs in this module.

**This belongs in the framework.** Every Frappe app that accepts a URL from a
user has this problem, and `frappe.utils.get_request_session` is where the
answer would serve all of them. Until it moves there, `insights/http.py` is the
one place in this app that knows the policy — do not copy the connection
classes into a second module.
