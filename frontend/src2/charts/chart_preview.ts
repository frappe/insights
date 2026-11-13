// The chart-read store's other source: the config being edited, rather than a
// saved chart's name.
//
// It lives apart from the store because of what it imports. The authoring
// endpoints answer with the operations the server derived, and the query editor
// a drill level opens in is the builder — neither of which an island may import.
// A View imports `chart_view` and loads none of it.

import { call } from 'frappe-ui'
import { computed, type InjectionKey } from 'vue'
import { stableStringify } from '../helpers/stable_stringify'
import { getLinkedQueries } from '../query/linked_queries'
import { openedQuery } from '../query/query'
import { dataSelection } from './helpers'
import type { Chart } from './chart'
import {
	cachedChartRead,
	makeChartRead,
	type ChartViewDoc,
	type ChartRead,
	type ChartReadContext,
	type DashboardFilterContext,
} from './chart_view'
import { authoringDrillRows, fetchAuthoringDrillData } from './drill/drill_api'

export const chartPreviewKey: InjectionKey<ChartRead> = Symbol('chartPreview')

export type ChartPreviewContext = ChartReadContext & {
	// whether the user can write the chart here. Asked at read time, like the
	// filters, because a dashboard learns the user's permissions only when its
	// document loads. Left out means the user can write.
	// eslint-disable-next-line no-unused-vars
	canWrite?: () => boolean
}

// one preview per chart per context: every card of one dashboard renders the
// chart from the same rows, while the chart's own page and a second dashboard
// each hold their own — a context's filters are in the rows it rendered. They are
// cached in the store beside the saved source's, so a chart that goes stale
// reaches every read of it.
export default function useChartPreview(chart: Chart, context?: ChartPreviewContext) {
	return cachedChartRead('preview', String(chart.doc.name), context, () =>
		makeChartPreview(chart, context),
	)
}

function makeChartPreview(chart: Chart, context?: ChartPreviewContext) {
	// The saved chart this preview belongs to. Every caller sends it, including
	// the chart's own builder page. The chart decides whose permissions filter
	// the rows, so a caller that leaves it out can show different rows from the
	// card beside it. An unsaved chart has a local name, which matches no
	// stored chart.
	const declaringChart = () => chart.doc.name

	const request = (filterContext?: DashboardFilterContext) => ({
		chart_type: chart.doc.chart_type,
		query: chart.doc.query,
		config: chart.doc.config,
		// unrouted: the server reads the links and decides which query
		// each filter lands on, the same way it does for a reader
		chart_name: filterContext?.chart ?? declaringChart(),
		// the saved dashboard: a user who cannot write the chart gets filters routed by it
		dashboard: filterContext?.dashboard,
		dashboard_items: filterContext?.items,
		filters: filterContext?.filters,
		card_filters: filterContext?.cardFilters,
		page_size: chart.doc.config.limit || 100,
	})

	// the chart as rendered, so a drill matches what is on screen and not an
	// edit still waiting for its rows
	const drilled = (rendered: ChartViewDoc) => ({
		query: rendered.query!,
		chart_type: rendered.chart_type,
		config: rendered.config,
	})

	return makeChartRead(
		{
			doc: computed(
				() =>
					({
						...chart.doc,
						can_write:
							!chart.doc.read_only && (context?.canWrite ? context.canWrite() : true),
					}) as ChartViewDoc,
			),
			requestKey: (filterContext) =>
				stableStringify({
					...request(filterContext),
					// a display option must not re-run the query, so the key names
					// the half of the config that decides which rows come back
					config: dataSelection(chart.doc.config),
					// the server reads the saved queries by name, so a save to any of
					// them is a new question under the same names. Only a query open
					// here can be saved here, so an unopened one is not loaded to ask.
					queries: openedQuery(chart.doc.query)
						? [chart.doc.query, ...getLinkedQueries(chart.doc.query)].map(
								(name) => openedQuery(name)?.doc.modified,
						  )
						: [],
					// where a card sits is not what it asks for: a drag moves every
					// box, and the key it is compared by must not move with it
					dashboard_items: filterContext?.items?.map(
						({ layout, layouts, ...item }) => item,
					),
				}),
			fetchData: (force, filterContext, page) =>
				call('insights.api.authoring.get_chart_data', {
					...request(filterContext),
					force,
					page,
				}),
			fetchCount: (filterContext, force) => {
				const { page_size, ...args } = request(filterContext)
				return call('insights.api.authoring.get_chart_count', { ...args, force })
			},
			fetchExport: (format, filterContext) => {
				const { page_size, ...args } = request(filterContext)
				return call('insights.api.authoring.download_chart_rows', { ...args, format })
			},
			fetchDrillData: (drill_stack, filterContext, rendered) =>
				fetchAuthoringDrillData(
					drilled(rendered),
					drill_stack,
					filterContext,
					declaringChart(),
				),
			rowsSource: (drill_stack, filterContext, rendered) =>
				authoringDrillRows(drilled(rendered), drill_stack, filterContext, declaringChart()),
		},
		context,
	)
}
