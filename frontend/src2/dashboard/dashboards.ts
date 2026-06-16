import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { createInfoToast, createSuccessToast } from '../helpers/toasts'
import { showErrorToast } from '../helpers'

export type DashboardListItem = {
	name: string
	title: string
	workbook: string
	folder?: string | null
	charts: number
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
	preview_image: string
	views: number
	is_favourite: boolean
}

const dashboards = ref<DashboardListItem[]>([])

const loading = ref(false)
const mapTimeAgo = (dashboard: any) => ({
	...dashboard,
	created_from_now: useTimeAgo(dashboard.creation),
	modified_from_now: useTimeAgo(dashboard.modified),
})

// dashboards of the current folder (favorites = the personal lens). subfolders
// + breadcrumb are derived on the client from the shared workbook folder tree.
async function fetchDashboards(folder?: string | null, search_term?: string, favorites = false) {
	loading.value = true
	const result = await call('insights.api.dashboards.get_dashboards', {
		folder: folder ?? 'root',
		search_term,
		get_favorites: favorites,
		limit: 0,
	})
	dashboards.value = result.map(mapTimeAgo)
	loading.value = false
}

const updatingPreviewImage = ref<Record<string, boolean>>({})
async function updatePreviewImage(dashboard_name: string) {
	updatingPreviewImage.value[dashboard_name] = true
	createInfoToast('Updating preview image...')
	return call('insights.api.dashboards.update_dashboard_preview', { dashboard_name })
		.then((file_url: string) => {
			createSuccessToast('Preview image updated successfully')
			const dashboard = dashboards.value.find((d) => d.name === dashboard_name)
			if (dashboard) {
				dashboard.preview_image = file_url
			}
		})
		.catch(showErrorToast)
		.finally(() => {
			updatingPreviewImage.value[dashboard_name] = false
		})
}

async function toggleLike(dashboard_name: string, add: boolean) {
	return call('frappe.desk.like.toggle_like', {
		doctype: 'Insights Dashboard v3',
		name: dashboard_name,
		add: add ? 'Yes' : 'No',
	})
}

export default function useDashboardStore() {
	return reactive({
		dashboards,
		loading,
		fetchDashboards,

		updatePreviewImage,
		updatingPreviewImage,

		toggleLike,
	})
}
