// The chart-read store's other feed: the config being edited, rather than a
// saved chart's name.
//
// It lives apart from the store because of what it drags in. The authoring
// endpoint answers with the operations it derived, and forking those into a
// drill query is the query builder — neither of which an island may carry. A
// read surface imports `chart_read` and gets none of it.

import { call } from 'frappe-ui'
import { computed } from 'vue'
import { makeDrillDownQuery } from '../query/query'
import type { Chart } from './chart'
import { makeChartRead, type ChartRead, type ChartReadDoc } from './chart_read'

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
		fetchData: (force, adhocFilters) => {
			const request = {
				chart_type: chart.doc.chart_type,
				query: chart.doc.query,
				config: chart.doc.config,
				adhoc_filters: adhocFilters,
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
		drillDown: makeDrillDownQuery,
	})
}
