import { useTimeAgo } from '@vueuse/core'
import { call, toast } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import type { FilterCondition, WireFilters } from '@framework/ui/Filter'
import type { AccessSource } from '../components/access'
import { __ } from '../translation'

export type DashboardListItem = {
	name: string
	title: string
	workbook: string
	owner: string
	folder?: string | null
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
// kept here, not in the list view, so they survive opening a dashboard and coming back
const filters = ref<FilterCondition[]>([])
const mapTimeAgo = (dashboard: any) => ({
	...dashboard,
	created_from_now: useTimeAgo(dashboard.creation),
	modified_from_now: useTimeAgo(dashboard.modified),
})

async function fetchDashboards(limit: number, sources: AccessSource[], filters: WireFilters) {
	loading.value = true
	const result = await call('insights.api.dashboards.get_dashboards', { limit, sources, filters })
	dashboards.value = result.map(mapTimeAgo)
	loading.value = false
}

const updatingPreviewImage = ref<Record<string, boolean>>({})
async function updatePreviewImage(dashboard_name: string) {
	updatingPreviewImage.value[dashboard_name] = true
	toast.info(__('Updating preview image...'))
	return call('insights.api.dashboards.update_dashboard_preview', { dashboard_name })
		.then((file_url: string) => {
			toast.success(__('Preview image updated successfully'))
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
		filters,
		fetchDashboards,

		updatePreviewImage,
		updatingPreviewImage,

		toggleLike,
	})
}
