// The `insights.chart` island: one saved chart, wherever the framework mounts it.

import { frappeRequest, setConfig } from 'frappe-ui'
import type { App } from 'vue'
import { APP_PATH } from '../app_path'
import { registerGlobalComponents } from '../globals'
import { setNavigationProvider } from '../helpers/navigation'
import ChartIsland from './ChartIsland.vue'

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
// new tab instead. Only string routes resolve — a named SPA route (the share
// link) yields nothing, and the island surfaces no affordance for it.
setNavigationProvider({
	resolveHref: (to) => (typeof to === 'string' ? `${APP_PATH}${to}` : ''),
	navigate: (to) => {
		const href = typeof to === 'string' ? `${APP_PATH}${to}` : ''
		if (href) window.open(href, '_blank')
	},
})

export function mount(el: HTMLElement, context: Record<string, any>) {
	return window.frappe.ui.mount_vue_island(el, {
		...context,
		component: ChartIsland,
		configure,
	})
}

function configure(app: App) {
	registerGlobalComponents(app)
}
