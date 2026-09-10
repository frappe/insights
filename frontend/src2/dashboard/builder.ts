// The dashboard the builder is editing, rather than a saved one named to the
// server. It loads the document resource, and everything above the fetch is the
// same page.
//
// It lives apart from `view.ts` for the same reason `chart_preview` lives apart
// from `chart_view`. The editing layer pulls in the workbook's stores and forms,
// which an island carries neither the weight nor the rights for.

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

/** The charts this dashboard may draw from — the workbook's, not the site's. */
export const chartOptionsKey = 'dashboardChartOptions'

export function useDashboardBuilder(name: string, charts: WorkbookChart[]): DashboardInBuilder {
	const dashboard = useDashboard(name)
	// the edit chrome and the editors reach the store the way they always have
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

	// A card collects its rows once the chart it draws has loaded: the preview is
	// drawn from the chart's config. A read it is the first to draw, or one the
	// chart went stale under while nothing drew it, runs — `invalidateChart`
	// marks rather than runs, so the card that has somewhere to put the rows
	// collects the mark.
	const watched = new Set<string>()
	function loadChart(chart_name: string) {
		const chart = dashboard.chartsByName[chart_name]
		waitUntil(() => Boolean(chart?.isloaded)).then(() => {
			const read = dashboard.chartView(chart_name)
			if (!read.ready || read.stale) dashboard.refreshChart(chart_name)
		})
		if (watched.has(chart_name) || !chart) return
		watched.add(chart_name)
		// sorting a table card writes the chart's config, so the card asks again
		watch(
			() => JSON.stringify(chart.doc.config.order_by),
			() => dashboard.refreshChart(chart_name),
		)
	}

	return reactive({
		loading: computed(() => !dashboard.isloaded),
		notFound: false,
		name: computed(() => dashboard.doc.name),
		title: computed(() => dashboard.doc.title),
		items,
		cellRules: computed(() => dashboard.cellRules),
		verticalCompact: computed(() => Boolean(dashboard.doc.vertical_compact_layout)),

		// An owner sees the default they set, not what they last picked: a default
		// is a property of the document, and checking it is why they set one. So
		// nothing is remembered here and nothing is saved.
		filters: computed(() => dashboard.filterStates),
		setFilter: (filter_name: string, filter?: FilterState) =>
			dashboard.updateFilterState(filter_name, filter?.operator, filter?.value),
		// The one thing the builder can ask that a reader cannot: a filter whose
		// link the document has not saved yet, previewed against the chart it names.
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
		loadChart,
		refresh: dashboard.refresh,

		builder: reactive({
			// the page only reads it — turning it on and off is the chrome's own
			editing: computed(() => dashboard.editing),
			// A width is only arranged while editing. Done leaves the owner on the
			// grid their own screen asks for, rather than in the box they last
			// arranged, and nothing has to be put back.
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
								onClick: () => {
									dashboard.discard()
									dashboard.editing = false
								},
							},
					  ]
					: [],
			),
			rename: (title: string) => (dashboard.doc.title = title),
			moveItems: (key: BreakpointKey, layouts: Layout[], before: Layout[]) =>
				dashboard.moveItems(key, layouts, before, dashboard.doc.vertical_compact_layout),
			dragOver: (event: DragEvent) => {
				if (!event.dataTransfer) return
				event.preventDefault()
				event.dataTransfer.dropEffect = 'copy'
			},
			drop: dropChart,
			chartRoute: (chart: string) =>
				dashboard.doc.has_workbook_access
					? `/workbook/${dashboard.doc.workbook}/chart/${chart}`
					: undefined,
		}),
	}) as DashboardInBuilder
}
