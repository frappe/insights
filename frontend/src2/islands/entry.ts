// What every Insights island entry does before it hands a component to the
// mount shell. One module, because an entry that set this up itself would be a
// second copy of it, and the two would drift.

import { frappeRequest, setConfig } from 'frappe-ui'
import type { App } from 'vue'
import { APP_PATH } from '../app_path'
import { registerGlobalComponents } from '../globals'
import { setNavigationProvider } from '../helpers/navigation'
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

// The island has no router, so the viewer's navigation seam opens Insights in a
// new tab instead. The href is absolute: it leaves this page for another app on
// the same site, and a desk page is not the SPA's base. Only string routes
// resolve — a named SPA route (the share link) yields nothing, and the island
// surfaces no affordance for it.
function insightsHref(to: unknown) {
	return typeof to === 'string' ? `${window.location.origin}${APP_PATH}${to}` : ''
}

setNavigationProvider({
	resolveHref: insightsHref,
	navigate: (to) => {
		const href = insightsHref(to)
		if (href) window.open(href, '_blank')
	},
})

/**
 * Mount `component` through the shell, forwarding the context desk gave us.
 *
 * The session is settled first, the way the SPA settles it in its router guard,
 * because an island draws numbers and dates the moment it has rows and the
 * reader's locale is not something a chart re-reads later. A session we could
 * not fetch is not worth an empty page, so a failure draws on the defaults.
 */
export async function mountIsland(component: any, el: HTMLElement, context: Record<string, any>) {
	await session.initialize().catch(() => {})

	return window.frappe.ui.mount_vue_island(el, {
		...context,
		component,
		configure: (app: App) => registerGlobalComponents(app),
	})
}
