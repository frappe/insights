import { useTimeAgo } from '@vueuse/core'
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
}

const dashboards = ref<DashboardListItem[]>([])

const loading = ref(false)
async function fetchDashboards(search_term?: string, limit: number = 50) {
	loading.value = true
	dashboards.value = await call('insights.api.dashboards.get_dashboards', {
		search_term,
		limit,
	})
	dashboards.value = dashboards.value.map((dashboard: any) => ({
		...dashboard,
		created_from_now: useTimeAgo(dashboard.creation),
		modified_from_now: useTimeAgo(dashboard.modified),
	}))
	loading.value = false
	return dashboards.value
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

export default function useDashboardStore() {
	if (!dashboards.value.length) {
		fetchDashboards()
	}

	return reactive({
		dashboards,
		loading,
		fetchDashboards,

		updatePreviewImage,
		updatingPreviewImage,
	})
}
