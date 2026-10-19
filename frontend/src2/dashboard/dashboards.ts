import { useTimeAgo } from '@vueuse/core'
import { call, toast } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import session from '../session'
import type { FilterCondition, WireFilters } from '@framework/ui/Filter'
import type { AccessSource } from '../components/access'
import { __ } from '../translation'

/** Where a card sits on a dashboard, and what it shows: a chart type, a filter or text. */
export type DashboardCell = { x: number; y: number; w: number; h: number; kind: string }

export type DashboardListItem = {
	name: string
	title: string
	/** Not sent to a reader without an Insights role, who cannot open the workbook. */
	workbook?: string
	/** A reader without an Insights role gets `owner_name` instead. */
	owner?: string
	owner_name?: string
	folder?: string | null
	creation: string
	modified: string
	created_from_now: string
	modified_from_now: string
	preview_image: string
	views: number
	is_favourite: boolean
	/** The title of the app that ships its workbook, when one does. */
	shipped_by: string | null
	cells: DashboardCell[]
	/** Whether the caller may write it, and so update its preview image. */
	can_write: boolean
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
	// a reader without an Insights role gets every dashboard they may open, in one list
	const result = session.isAuthorized
		? await call('insights.api.dashboards.get_dashboards', { limit, sources, filters })
		: await call('insights.api.view.get_dashboards')
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
