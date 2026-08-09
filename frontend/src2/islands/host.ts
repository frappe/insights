// The ambient context the framework injects into every island: what the page
// knows or can do that the island's shadow root cannot reach for itself.
//
// It is captured when the island mounts, which is what "where the reader came
// from" means — the island unmounts whenever the reader leaves the page, so a
// new visit brings a new trail.

import { inject } from 'vue'

// The shell provides under the same global symbol.
const HOST_KEY = Symbol.for('frappe:island-host')

export type HostCrumb = {
	label: string
	/** a host route, in whatever form the host's own navigate() takes */
	route: string
}

export type IslandHost = {
	/** ancestors of this page, never the page itself */
	breadcrumbs?: HostCrumb[]
	/** route the host to one of its own pages */
	navigate?: (route: string) => void
	/** name the browser tab, for an island that is the whole page */
	set_title?: (title: string) => void
	locale?: string
	timezone?: string | null
	user?: string | null
	theme?: string
}

// An empty host is a working host: every field is optional, so an island still
// mounts under a host that injects nothing (a test, or a page that predates the
// field it wants).
export function useHost(): IslandHost {
	return inject<IslandHost>(HOST_KEY, {})
}
