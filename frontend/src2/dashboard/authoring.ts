// The dashboard page's other feed: the document being edited, rather than a
// saved dashboard named to the server.
//
// It has to be a feed of its own because the builder needs a document it can
// write. It saves, it adds and removes items, and it tracks what is being
// edited — none of which a rendering response can carry, whatever that response
// includes. So it loads the document resource and everything above the fetch is
// the same page.
//
// It lives apart from `viewer.ts` for the same reason `chart_preview` lives
// apart from `chart_read`: the editing layer drags in the workbook's stores and
// its forms, which an island carries neither the weight nor the rights for. A
// read surface imports `viewer` and gets none of it.

import { useStorage, useWindowSize } from '@vueuse/core'
import { computed, markRaw, provide, reactive, watchEffect } from 'vue'
import { safeJSONParse } from '../helpers'
import { __ } from '../translation'
import type { Layout, WorkbookChart } from '../types/workbook.types'
import useDashboard from './dashboard'
import DashboardEditActions from './DashboardEditActions.vue'
import DashboardItem from './DashboardItem.vue'
import VueGridLayout from './VueGridLayout.vue'
import { defaultFilters, type DashboardSource, type ViewerDashboardItem } from './viewer'

/** The charts this dashboard may draw from — the workbook's, not the site's. */
export const chartOptionsKey = 'dashboardChartOptions'

export function useDashboardAuthoring(name: string, charts: WorkbookChart[]): DashboardSource {
	const dashboard = useDashboard(name)
	// the edit chrome and the cards reach the store the way they always have
	provide('dashboard', dashboard)
	provide(chartOptionsKey, charts)

	const { width } = useWindowSize()
	const isMobile = computed(() => width.value < 1058)

	// A layout the reader is still moving is not one to save on every drag, and a
	// grid too narrow to drag on is one they did not mean to change at all.
	watchEffect(() => {
		dashboard.autoSave = !dashboard.editing && !isMobile.value
	})

	const verticalCompact = useStorage('dashboard_vertical_compact', true)

	function dropChart(event: DragEvent) {
		if (!event.dataTransfer) return
		event.preventDefault()
		const data = safeJSONParse(event.dataTransfer.getData('text/plain'))
		const chart = charts.find((c) => c.name === data?.item?.name)
		if (!chart) return
		dashboard.editing = true
		dashboard.addChart([chart])
	}

	return reactive({
		loading: computed(() => !dashboard.isloaded),
		unavailable: false,
		name: computed(() => dashboard.doc.name),
		title: computed(() => dashboard.doc.title),
		items: computed(() => dashboard.doc.items as ViewerDashboardItem[]),
		// An author sees the default they set, not what they last picked: a default
		// is a property of the document, and checking it is why they set one. So
		// nothing is remembered here and nothing is saved.
		filters: computed(() => defaultFilters(dashboard.doc.items as ViewerDashboardItem[])),
		verticalCompact,
		cell: markRaw(DashboardItem),
		grid: markRaw(VueGridLayout),

		authoring: reactive({
			// the page only reads it — turning it on and off is the chrome's own
			editing: computed(() => dashboard.editing),
			actions: markRaw(DashboardEditActions),
			menuOptions: computed(() =>
				dashboard.editing
					? [
							{
								label: __('Compact Layout'),
								icon: verticalCompact.value ? 'check-square' : 'square',
								onClick: () => (verticalCompact.value = !verticalCompact.value),
							},
							{
								label: __('Reset Layout'),
								icon: 'lucide-refresh-ccw',
								onClick: () => {
									dashboard.discard()
									dashboard.editing = false
								},
							},
					  ]
					: [],
			),
			rename: (title: string) => (dashboard.doc.title = title),
			moveItems: (layouts: Layout[]) => {
				dashboard.doc.items.forEach((item, index) => (item.layout = layouts[index]))
			},
			dragOver: (event: DragEvent) => {
				if (!event.dataTransfer) return
				event.preventDefault()
				event.dataTransfer.dropEffect = 'copy'
			},
			drop: dropChart,
		}),
	}) as DashboardSource
}
