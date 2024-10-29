import { useTimeAgo } from '@vueuse/core'
import { call } from 'frappe-ui'
import { reactive, ref } from 'vue'

export type DashboardListItem = {
	name: string
	title: string
	workbook: string
	charts: number
	modified: string
	modified_from_now: string
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
		// created_from_now: useTimeAgo(workbook.creation),
		modified_from_now: useTimeAgo(dashboard.modified),
	}))
	loading.value = false
	return dashboards.value
}

async function fetchWorkbookName(name: string) {
	return await call('insights.api.dashboards.get_workbook_name', { dashboard_name: name })
}

export default function useDashboardStore() {
	if (!dashboards.value.length) {
		fetchDashboards()
	}

	return reactive({
		dashboards,
		loading,
		fetchDashboards,
		fetchWorkbookName,
	})
}
