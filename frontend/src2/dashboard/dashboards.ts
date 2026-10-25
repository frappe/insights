import { useStorage, useTimeAgo } from '@vueuse/core'
import { call, toast } from 'frappe-ui'
import { reactive, ref } from 'vue'
import { showErrorToast } from '../helpers'
import session from '../session'
import type { FilterCondition, WireFilters } from '@framework/ui/Filter'
import type { AccessSource } from '../components/access'
import { __ } from '../translation'

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
	/** Set only while `same_rows_for_every_reader`, and once a preview was rendered. */
	preview_image: string | null
	/** Whether every reader sees the same rows, so one preview image may show to all of them. */
	same_rows_for_every_reader: boolean
	views: number
	is_favourite: boolean
	/** Set only for a caller who may read the workbook. Not sent to a reader without an Insights role. */
	workbook_title?: string | null
	/** When the caller last opened it. */
	last_opened: string | null
	last_opened_from_now: string
	/** Who else may open it. Not sent to a reader without an Insights role. */
	shared_with?: string[]
	shared_with_organization?: boolean
	visible_to_roles?: string[]
	is_public?: boolean
	/** The title of the app that ships its workbook, when one does. */
	shipped_by: string | null
	/** That app's `app_logo_url`, when it declares one. */
	shipped_by_logo: string | null
	/** Whether the caller may write it, and so update its preview image. */
	can_write: boolean
}

/** The server names the workbook only to a caller who may read it. */
export function canOpenWorkbook(dashboard: Pick<DashboardListItem, 'workbook' | 'workbook_title'>) {
	return Boolean(dashboard.workbook && dashboard.workbook_title != null)
}

const dashboards = ref<DashboardListItem[]>([])

const loading = ref(false)
// kept here, not in the list view, so they survive opening a dashboard and coming back
const filters = ref<FilterCondition[]>([])
const mapTimeAgo = (dashboard: any) => ({
	...dashboard,
	created_from_now: useTimeAgo(dashboard.creation),
	modified_from_now: useTimeAgo(dashboard.modified),
	last_opened_from_now: dashboard.last_opened ? useTimeAgo(dashboard.last_opened) : '',
})

export type DashboardView = 'grid' | 'list'

/** The view the Dashboards page shows, kept in the browser for each user. */
export function useDashboardView() {
	return useStorage<DashboardView>(
		`insights:dashboard-view:${session.user.email}`,
		'list',
		localStorage,
	)
}

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
