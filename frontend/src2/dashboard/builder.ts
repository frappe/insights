// The dashboard the builder edits. It loads the document resource instead of
// asking the view endpoints by name. Above the fetch, the page is the same.
//
// It is separate from `view.ts` for the same reason `chart_preview` is separate
// from `chart_view`. The builder imports the workbook's stores and forms. An
// island must not carry their weight, and its reader lacks the rights for them.

import { computed, provide, reactive, watch } from 'vue'
import { safeJSONParse, waitUntil } from '../helpers'
import { __ } from '../translation'
import type { BreakpointKey, Layout, WorkbookChart } from '../types/workbook.types'
import useDashboard from './dashboard'
import { BASE_BREAKPOINT } from './grid_placement'
import {
	cellRulesFor,
	type DashboardInBuilder,
	type DashboardViewItem,
	type FilterState,
} from './view'

/** The charts this dashboard may use: the workbook's, not every chart on the site. */
export const chartOptionsKey = 'dashboardChartOptions'

export function useDashboardBuilder(name: string, charts: WorkbookChart[]): DashboardInBuilder {
	const dashboard = useDashboard(name)
	provide('dashboard', dashboard)
	provide(chartOptionsKey, charts)

	const items = computed(() => dashboard.doc.items as DashboardViewItem[])

	function dropChart(event: DragEvent) {
		if (!event.dataTransfer) return
		event.preventDefault()
		const data = safeJSONParse(event.dataTransfer.getData('text/plain'))
		const chart = charts.find((c) => c.name === data?.item?.name)
		if (!chart) return
		dashboard.editing = true
		dashboard.addChart([chart], 'drag')
	}

	// A card loads its rows after its chart loads, because the preview is built
	// from the chart's config. Every mount calls load, because the chart or its
	// query may have been saved while no card showed it. The read skips the load
	// if its request is unchanged. `invalidateChart` only marks the read stale, so
	// the next mounted card runs the load.
	const watched = new Set<string>()
	function loadChart(chart_name: string) {
		const chart = dashboard.chartsByName[chart_name]
		waitUntil(() => Boolean(chart?.isloaded)).then(() => dashboard.refreshChart(chart_name))
		if (watched.has(chart_name) || !chart) return
		watched.add(chart_name)
		// sorting a table card writes the chart's config, so the card reloads
		watch(
			() => JSON.stringify(chart.doc.config.order_by),
			() => dashboard.refreshChart(chart_name),
		)
	}

	return reactive({
		loading: computed(() => !dashboard.isloaded),
		notFound: false,
		failed: false,
		name: computed(() => dashboard.doc.name),
		title: computed(() => dashboard.doc.title),
		items,
		cellRules: computed(() => dashboard.cellRules),
		verticalCompact: computed(() => Boolean(dashboard.doc.vertical_compact_layout)),

		// The owner sees the defaults they set, not their last choice. A default
		// belongs to the document, and the owner is here to check it. So nothing is
		// stored in the browser.
		filters: computed(() => dashboard.filterStates),
		setFilter: (filter_name: string, filter?: FilterState) =>
			dashboard.updateFilterState(filter_name, filter?.operator, filter?.value),
		// Unlike a reader, the builder can get values for a filter whose link is not
		// saved yet. The values come from the linked chart.
		filterValues: (filter_name: string, search_term?: string) => {
			const filter = dashboard.doc.items.find(
				(item) => item.type === 'filter' && item.filter_name === filter_name,
			)
			const linked = Object.keys((filter?.type === 'filter' && filter.links) || {})[0]
			if (!linked) return Promise.resolve([])
			return dashboard.getDistinctColumnValues(filter_name, search_term, linked)
		},
		filterRange: (filter_name: string) => dashboard.getFilterColumnRange(filter_name),
		cardFilters: computed(() => dashboard.cardFilters),
		setCardFilters: dashboard.setCardFilters,
		cardValues: (chart: string, column: string, search_term?: string) =>
			dashboard.getCardColumnValues(chart, column, search_term),
		cardRange: (chart: string, column: string) => dashboard.getCardColumnRange(chart, column),
		filtered: dashboard.cardIsFiltered,
		resetCardFilters: dashboard.resetCardFilters,
		chartView: dashboard.chartView,
		chartRoute: (chart: string) =>
			dashboard.doc.has_workbook_access
				? `/workbook/${dashboard.doc.workbook}/chart/${chart}`
				: undefined,
		loadChart,
		refresh: dashboard.refresh,

		builder: reactive({
			// read-only here. `DashboardEditActions` turns editing on
			editing: computed(() => dashboard.editing),
			// A breakpoint is arranged only while editing. After Done, the owner sees
			// the grid for their own screen, not the last breakpoint they arranged, and
			// nothing needs resetting.
			arranging: computed(() =>
				dashboard.editing ? dashboard.arranging : BASE_BREAKPOINT.key,
			),
			menuOptions: computed(() =>
				dashboard.editing
					? [
							{
								label: __('Compact Layout'),
								icon: dashboard.doc.vertical_compact_layout
									? 'check-square'
									: 'square',
								onClick: () =>
									(dashboard.doc.vertical_compact_layout =
										!dashboard.doc.vertical_compact_layout),
							},
							{
								label: __('Reset Layout'),
								icon: 'refresh-ccw',
								onClick: dashboard.discardEditing,
							},
					  ]
					: [],
			),
			moveItems: (key: BreakpointKey, layouts: Layout[], before: Layout[]) =>
				dashboard.moveItems(key, layouts, before, dashboard.doc.vertical_compact_layout),
			dragOver: (event: DragEvent) => {
				if (!event.dataTransfer) return
				event.preventDefault()
				event.dataTransfer.dropEffect = 'copy'
			},
			drop: dropChart,
		}),
	}) as DashboardInBuilder
}
