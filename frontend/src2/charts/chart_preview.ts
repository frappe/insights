// The chart-read store's other feed: the config being edited, rather than a
// saved chart's name.
//
// It lives apart from the store because of what it drags in. The authoring
// endpoints answer with the operations the server derived, and the query editor
// a drill level opens in is the builder — neither of which an island may carry.
// A read surface imports `chart_read` and gets none of it.

import { call } from 'frappe-ui'
import { computed } from 'vue'
import type { Chart } from './chart'
import { makeChartRead, type ChartRead, type ChartReadDoc } from './chart_read'
import { fetchAuthoringDrillData } from './drill/drill_api'

// one preview per chart, so the chart page and the builder's dashboard draw the
// same card from the same rows — the same sharing `useChart` gives the document
const previews = new Map<string, ChartRead>()

export default function useChartPreview(chart: Chart) {
	const key = String(chart.doc.name)
	const existing = previews.get(key)
	if (existing) return existing

	const preview = makeChartPreview(chart)
	previews.set(key, preview)
	return preview
}

function makeChartPreview(chart: Chart) {
	let lastRequest: string | undefined

	return makeChartRead({
		doc: computed(() => chart.doc as ChartReadDoc),
		fetchData: (force, filterContext) => {
			const request = {
				chart_type: chart.doc.chart_type,
				query: chart.doc.query,
				config: chart.doc.config,
				// unrouted: the server reads the links and decides which query
				// each filter lands on, the same way it does for a reader
				chart_name: filterContext?.chart,
				dashboard_items: filterContext?.items,
				filters: filterContext?.filters,
				page_size: chart.doc.config.limit || 100,
			}
			// the config is watched deeply, so an edit that leaves the request the
			// same — a display option, a re-normalized slot — must not re-run it
			const serialized = JSON.stringify(request)
			if (!force && lastRequest === serialized) {
				return Promise.resolve(undefined)
			}
			lastRequest = serialized
			return call('insights.api.authoring.get_chart_data', { ...request, force })
		},
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
	})
}
