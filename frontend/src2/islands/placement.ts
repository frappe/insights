// The props a host passes to tell an island what to render.
//
// Each kind of host names the dashboard its own way. A desk document's Claim
// passes the docname as `dashboard`. A Frappe UI page passes the path below its
// own route: `/app/insights-dashboard/<dashboard>` arrives as `route`. A sidebar
// item that names the dashboard in its `route` field opens the same URL. Both
// are props, so the island never reads a desk route itself.

export type DashboardPlacement = {
	dashboard?: string
	route?: string[]
}

/**
 * The dashboard a placement names, or empty when it names none.
 *
 * The View answers an empty name with Not Found. So a misconfigured placement
 * looks the same as a deleted dashboard.
 */
export function placedDashboard(placement: DashboardPlacement): string {
	return placement.dashboard || placement.route?.[0] || ''
}
