// Setup shared by every Insights island entry. It lives in one module so the
// entries cannot drift apart.

import { mountVueIsland } from '@framework/ui/island'
import { frappeRequest, setConfig } from 'frappe-ui'
import { APP_PATH } from '../app_path'
import { setRouter } from '../helpers/navigation'
import session from '../session'
import { configureIsland } from './configure'

declare global {
	interface Window {
		frappe?: any
		translatedMessages?: Record<string, string>
	}
}

setConfig('resourceFetcher', frappeRequest)

// frappe-ui reads the CSRF token from `window`, but desk sets it on `frappe`.
// Without this, the server rejects every write the island makes.
if (!window.csrf_token && window.frappe?.csrf_token) {
	window.csrf_token = window.frappe.csrf_token
}

// The host page already holds the site's translations, so reuse them instead
// of fetching them again.
if (!window.translatedMessages && window.frappe?._messages) {
	window.translatedMessages = window.frappe._messages
}

setRouter({
	// A route in the island is an Insights page, but the host page is not under
	// the SPA's base, so the href is absolute. Only a string route resolves. A
	// named SPA route gives an empty href, and the island shows no link for it.
	resolveHref: (to) =>
		typeof to === 'string' ? `${window.location.origin}${APP_PATH}${to}` : '',
	// the host owns the page, so leaving the island is a full page load
	navigate: (to) => {
		if (typeof to === 'string')
			window.location.assign(`${window.location.origin}${APP_PATH}${to}`)
	},
})

/**
 * Mount `component` with the context the host passed in.
 *
 * Load the session first, as the SPA does in its router guard. An island
 * formats numbers and dates as soon as it has rows, and a chart does not
 * re-read the reader's locale or the site's currency later. If the session
 * fails to load, the island still mounts and uses the defaults.
 */
export async function mountIsland(component: any, el: HTMLElement, context: Record<string, any>) {
	await session.initialize().catch(() => {})

	return mountVueIsland(el, {
		...context,
		component,
		configure: configureIsland,
	})
}
