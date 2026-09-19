// What every Insights island entry does before it hands a component to the
// mount shell. One module, because an entry that set this up itself would be a
// second copy of it, and the two would drift.

import { mountVueIsland } from '@framework/ui/island'
import { frappeRequest, setConfig } from 'frappe-ui'
import type { App } from 'vue'
import { APP_PATH } from '../app_path'
import { registerGlobalComponents } from '../globals'
import { setRouter } from '../helpers/navigation'
import session from '../session'

declare global {
	interface Window {
		frappe?: any
	}
}

setConfig('resourceFetcher', frappeRequest)

// frappe-ui reads the CSRF token off `window`, desk publishes it on `frappe`.
// Without this every write the island makes is rejected.
if (!window.csrf_token && window.frappe?.csrf_token) {
	window.csrf_token = window.frappe.csrf_token
}

setRouter({
	// A route named inside the island is a page of Insights, and the host's page
	// is not the SPA's base, so the href is absolute. Only a string route
	// resolves — a named SPA route yields nothing, and the island offers no
	// affordance for it.
	resolveHref: (to) =>
		typeof to === 'string' ? `${window.location.origin}${APP_PATH}${to}` : '',
	// the page around the island is the host's, so leaving it is a page load
	navigate: (to) => {
		if (typeof to === 'string')
			window.location.assign(`${window.location.origin}${APP_PATH}${to}`)
	},
})

/**
 * Mount `component` through the shell, forwarding the context the host gave us.
 *
 * The session is settled first, the way the SPA settles it in its router guard,
 * because an island draws numbers and dates the moment it has rows and the
 * reader's locale and the site's currency are not something a chart re-reads
 * later. A session we could not fetch is not worth an empty page, so a failure
 * draws on the defaults.
 */
export async function mountIsland(component: any, el: HTMLElement, context: Record<string, any>) {
	await session.initialize().catch(() => {})

	return mountVueIsland(el, {
		...context,
		component,
		configure: (app: App) => registerGlobalComponents(app),
	})
}
