// The chart-read store's other feed: the config being edited, rather than a
// saved chart's name.
//
// It lives apart from the store because of what it drags in. The authoring
// endpoints answer with the operations the server derived, and the query editor
// a drill level opens in is the builder — neither of which an island may carry.
// A read surface imports `chart_read` and gets none of it.

import { call } from 'frappe-ui'
import { computed } from 'vue'
import { stableStringify } from '../helpers'
import type { Chart } from './chart'
import {
	cachedChartRead,
	makeChartRead,
	type ChartReadDoc,
	type ChartReadSurface,
	type DashboardFilterContext,
} from './chart_read'
import { fetchAuthoringDrillData } from './drill/drill_api'

// one preview per chart per surface: every card of one dashboard draws the
// chart from the same rows, while the chart's own page and a second dashboard
// each hold their own — a surface's filters are in the rows it drew. They are
// cached in the store beside the saved feed's, so a chart that goes stale
// reaches every read of it.
export default function useChartPreview(chart: Chart, surface?: ChartReadSurface) {
	return cachedChartRead('preview', chart, surface, () => makeChartPreview(chart, surface))
}

function makeChartPreview(chart: Chart, surface?: ChartReadSurface) {
	// the config is watched deeply, so an edit that leaves the request the same —
	// a display option, a re-normalized slot, a save that came back with its keys
	// sorted — must not re-run it
	const request = (filterContext?: DashboardFilterContext) => ({
		chart_type: chart.doc.chart_type,
		query: chart.doc.query,
		config: chart.doc.config,
		// unrouted: the server reads the links and decides which query
		// each filter lands on, the same way it does for a reader
		chart_name: filterContext?.chart,
		dashboard_items: filterContext?.items,
		filters: filterContext?.filters,
		page_size: chart.doc.config.limit || 100,
	})

	return makeChartRead(
		{
			doc: computed(() => chart.doc as ChartReadDoc),
			requestKey: (filterContext) => stableStringify(request(filterContext)),
			fetchData: (force, filterContext) =>
				call('insights.api.authoring.get_chart_data', { ...request(filterContext), force }),
			// the same config the picture was drawn from, so a drill answers for what
			// is on screen rather than for whatever was last saved
			fetchDrillData: (drill_stack, filterContext) =>
				fetchAuthoringDrillData(
					{
						query: chart.doc.query,
						chart_type: chart.doc.chart_type,
						config: chart.doc.config,
					},
					drill_stack,
					filterContext,
				),
		},
		() => surface?.filterContext(String(chart.doc.name)),
	)
}
