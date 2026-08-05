import { call } from 'frappe-ui'
import { computed, ref } from 'vue'

export type ExportBundle = { folder: string; title: string }
export type ExportApp = { app: string; title: string; bundles: ExportBundle[] }
export type ExportTargets = { developer_mode: boolean; apps: ExportApp[] }

export type ExportedItem = {
	doctype: string
	docname: string
	logical_id: string
	path: string
}
export type ExportReport = {
	app: string
	bundle: string
	items: ExportedItem[]
	written: string[]
}

const targets = ref<ExportTargets>()
let request: Promise<any> | null = null

export const exportTargets = computed(() => targets.value)
// outside developer mode the export surface must not exist, and the only way to
// know is to ask - so ask once per session, and only where an export is possible
export const canExportToApp = computed(() => Boolean(targets.value?.developer_mode))

export function loadExportTargets() {
	if (!request) {
		request = call('insights.api.bundles.get_export_targets')
			.then((response: ExportTargets) => (targets.value = response))
			// a bench that cannot answer has no export surface, and saying so in
			// a toast would only alarm the users who can never use one
			.catch(() => undefined)
	}
	return request
}

export function exportDashboard(args: {
	dashboard: string
	app: string
	bundle?: string
	bundle_title?: string
}): Promise<ExportReport> {
	return call('insights.api.bundles.export_dashboard', args)
}

// "Insights Chart v3 → insights/sales_chart" reads as neither, so name the item
// the way the builder does and let the path say the rest
export function itemLabel(item: ExportedItem) {
	const kind = item.doctype.replace(/^Insights /, '').replace(/ v3$/, '')
	return `${kind} · ${item.logical_id}`
}

export const BUNDLE_NAME_PATTERN = /^[a-z0-9][a-z0-9_-]*$/

export function toBundleName(title: string) {
	const name = (title || '')
		.toLowerCase()
		.replace(/[^a-z0-9_-]+/g, '-')
		.replace(/-{2,}/g, '-')
		.replace(/^[-_]+|[-_]+$/g, '')
	return BUNDLE_NAME_PATTERN.test(name) ? name : ''
}
