import { get, useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { createInfoToast, createSuccessToast } from '../helpers/toasts'
import { showErrorToast } from '../helpers'

export type DashboardListItem = {
	name: string
	title: string
	workbook: string
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
const favorites = ref<DashboardListItem[]>([])

const loading = ref(false)
const mapTimeAgo = (dashboard: any) => ({
	...dashboard,
	created_from_now: useTimeAgo(dashboard.creation),
	modified_from_now: useTimeAgo(dashboard.modified),
})
async function fetchDashboards(search_term?: string, limit: number = 50) {
	loading.value = true

	const [regular, fav] = await Promise.all([
		call('insights.api.dashboards.get_dashboards', { search_term, limit }),
		call('insights.api.dashboards.get_dashboards',{get_favorites: true}),
	])

	dashboards.value = regular.map(mapTimeAgo)
	favorites.value = fav.map(mapTimeAgo)
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
		.then(() => fetchDashboards())
}

export default function useDashboardStore() {
	if (!dashboards.value.length) {
		fetchDashboards()
	}

	return reactive({
		dashboards,
		favorites,
		loading,
		fetchDashboards,

		updatePreviewImage,
		updatingPreviewImage,

		toggleLike,
	})
}
