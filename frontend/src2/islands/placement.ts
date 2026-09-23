// What a host told an island to draw.
//
// A placement is any host that names an island and passes it props, and each
// kind of host names the content its own way. A desk document's claim passes the
// docname outright. A Frappe UI page passes what is below its own route instead:
// `/app/insights-dashboard/<dashboard>` arrives as `route`, and a sidebar item
// naming that dashboard in its own `route` field lands on the same URL. Every
// one of them is a prop, so the island still never reads a desk route of its own.

export type DashboardPlacement = {
	dashboard?: string
	route?: string[]
}

/**
 * The dashboard a placement asked for.
 *
 * Empty when it named none. That is a reference resolving to nothing, which the
 * view already answers as Not Found, so a misconfigured placement reads the same
 * as a dashboard that is gone.
 */
export function placedDashboard(placement: DashboardPlacement): string {
	return placement.dashboard || placement.route?.[0] || ''
}
