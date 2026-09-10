// The chart as its author holds it: the document, the config being edited, the
// save. What the config produces is not here — the server derives the operations
// from it and runs them, and `chart_read` is where the rows come back.

import { useDebouncedRefHistory } from '@vueuse/core'
import { computed, reactive, toRefs, watch } from 'vue'
import { copyToClipboard, getUniqueId, safeJSONParse, wheneverChanges } from '../helpers'
import { GranularityType } from '../helpers/constants'
import useDocumentResource from '../helpers/resource'
import useQuery from '../query/query'
import router from '../router'
import { AXIS_CHARTS } from '../types/chart.types'
import { InsightsChartv3 } from '../types/workbook.types'
import { getLinkedQueries } from '../query/linked_queries'
import { ensureConfigSlots, normalizeChartConfig } from './helpers'

const charts = new Map<string, Chart>()

export default function useChart(name: string) {
	const key = String(name)
	const existingChart = charts.get(key)
	if (existingChart) return existingChart

	const chart = makeChart(name)
	charts.set(key, chart)
	return chart
}

function makeChart(name: string) {
	const chart = getChartResource(name)

	function updateGranularity(column_name: string, granularity: GranularityType) {
		if ('x_axis' in chart.doc.config) {
			if (chart.doc.config.x_axis?.dimension?.dimension_name === column_name) {
				chart.doc.config.x_axis.dimension.granularity = granularity
			}
		}

		if ('date_column' in chart.doc.config) {
			if (chart.doc.config.date_column?.dimension_name === column_name) {
				chart.doc.config.date_column.granularity = granularity
			}
		}

		if ('rows' in chart.doc.config) {
			chart.doc.config.rows.forEach((row) => {
				if (row.dimension_name === column_name) {
					row.granularity = granularity
				}
			})
		}
	}

	function getShareLink() {
		const { href } = router.resolve({
			name: 'SharedChart',
			params: { chart_name: chart.doc.name },
		})
		return `${window.location.origin}${href}`
	}

	function updateAccess(is_public: boolean) {
		return chart.call('update_access', { is_public }).then(() => chart.load())
	}

	function getDependentQueries() {
		return [chart.doc.query, ...getLinkedQueries(chart.doc.query)]
	}

	function getDependentQueryColumns() {
		return getDependentQueries().map((q) => {
			const query = useQuery(q)
			query.ensureResult()
			return {
				group: query.doc.title,
				options: query.result.columnOptions.map((c) => {
					const sep = '`'
					const value = `${sep}${query.doc.name}${sep}.${sep}${c.value}${sep}`
					return {
						...c,
						value,
					}
				}),
			}
		})
	}

	function resetConfig() {
		// @ts-ignore
		chart.doc.config = {
			order_by: [],
			filters: chart.doc.config.filters,
			limit: chart.doc.config.limit,
		}
	}

	// when chart type changes from axis to non-axis or vice versa reset the config
	watch(
		() => chart.doc.chart_type,
		(newType: string, oldType: string) => {
			if (!newType || newType === oldType) return
			const crossesAxisBoundary =
				oldType && AXIS_CHARTS.includes(newType) !== AXIS_CHARTS.includes(oldType)
			if (crossesAxisBoundary) {
				resetConfig()
			}
			ensureConfigSlots(chart.doc.config, newType)
		},
	)

	function copyChart() {
		copyToClipboard(chart.call('export').then((data) => JSON.stringify(data, null, 2)))
	}

	const history = useDebouncedRefHistory(
		// @ts-ignore
		computed({
			get: () => chart.doc,
			set: (value) => Object.assign(chart.doc, value),
		}),
		{
			deep: true,
			capacity: 100,
			debounce: 500,
		},
	)

	return reactive({
		...toRefs(chart),

		updateGranularity,
		resetConfig,

		getShareLink,
		updateAccess,

		getDependentQueries,
		getDependentQueryColumns,

		copy: copyChart,
		openInDesk: () => window.open(`/app/insights-chart-v3/${chart.doc.name}`, '_blank'),

		history,
	})
}

export type Chart = ReturnType<typeof makeChart>

const INITIAL_DOC: InsightsChartv3 = {
	doctype: 'Insights Chart v3',
	name: '',
	owner: '',
	title: '',
	workbook: '',
	query: '',
	chart_type: '',
	sort_order: 0,
	is_public: false,
	config: {} as InsightsChartv3['config'],
	operations: [],
	read_only: false,
}

function getChartResource(name: string) {
	const doctype = 'Insights Chart v3'
	const chart = useDocumentResource<InsightsChartv3>(doctype, name, {
		initialDoc: { ...INITIAL_DOC, name },
		enableAutoSave: true,
		disableLocalStorage: true,
		transform: transformChartDoc,
	})
	// A chart is inserted with the config its author already sees, which is the
	// normalized one. Send anything else and the answer comes back in a shape the
	// load normalizes differently — the document is dirty for being created, and
	// creating a chart costs a write and a second run of its data.
	chart.onBeforeInsert(() => {
		chart.doc.config = normalizeChartConfig(chart.doc.config, chart.doc.chart_type)
	})
	wheneverChanges(
		() => chart.doc.read_only,
		() => {
			if (chart.doc.read_only) {
				chart.autoSave = false
			}
		},
	)
	return chart
}

function transformChartDoc(doc: any) {
	doc.config = safeJSONParse(doc.config) || {}
	doc.operations = safeJSONParse(doc.operations) || []

	doc.config = normalizeChartConfig(doc.config, doc.chart_type)

	return doc
}

export function newChart() {
	const chart = makeChart('new-chart-' + getUniqueId())
	// The page that opens next asks for the chart by the name the insert gave it,
	// and has to be handed this store. A second store for one chart writes the
	// document twice and runs its data twice, and the two disagree from the first
	// edit.
	chart.onAfterInsert(() => charts.set(String(chart.doc.name), chart))
	return chart
}
