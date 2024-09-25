import { useDebouncedRefHistory, UseRefHistoryReturn } from '@vueuse/core'
import { computed, reactive, ref, unref, watch } from 'vue'
import { copy, getUniqueId, waitUntil, wheneverChanges } from '../helpers'
import { createToast } from '../helpers/toasts'
import { column, count, query_table } from '../query/helpers'
import { getCachedQuery, makeQuery, Query } from '../query/query'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	DountChartConfig,
	NumberChartConfig,
	TableChartConfig,
} from '../types/chart.types'
import { FilterArgs, GranularityType, Operation } from '../types/query.types'
import { WorkbookChart } from '../types/workbook.types'

const charts = new Map<string, Chart>()

export default function useChart(workbookChart: WorkbookChart) {
	const existingChart = charts.get(workbookChart.name)
	if (existingChart) return existingChart

	const chart = makeChart(workbookChart)
	charts.set(workbookChart.name, chart)
	return chart
}

export function getCachedChart(name: string) {
	return charts.get(name)
}

function makeChart(workbookChart: WorkbookChart) {
	const chart = reactive({
		doc: workbookChart,

		baseQuery: computed(() => {
			if (!workbookChart.query) return {} as Query
			return getCachedQuery(workbookChart.query) as Query
		}),
		dataQuery: makeQuery({
			name: getUniqueId(),
			operations: [],
		}),

		refresh,
		getGranularity,
		updateGranularity,

		history: {} as UseRefHistoryReturn<any, any>,
	})

	wheneverChanges(
		() => chart.doc.query,
		() => resetConfig()
	)

	function resetConfig() {
		chart.doc.config = {} as WorkbookChart['config']
		chart.doc.config.order_by = []
		chart.dataQuery.reset()
	}

	// when chart type changes from axis to non-axis or vice versa reset the config
	watch(
		() => chart.doc.chart_type,
		(newType: string, oldType: string) => {
			if (newType === oldType) return
			if (!newType || !oldType) return
			if (
				(AXIS_CHARTS.includes(newType) && !AXIS_CHARTS.includes(oldType)) ||
				(!AXIS_CHARTS.includes(newType) && AXIS_CHARTS.includes(oldType))
			) {
				resetConfig()
			}
		}
	)

	async function refresh(filters?: FilterArgs[], force = false) {
		if (!workbookChart.query) return
		if (!chart.doc.chart_type) return
		if (chart.baseQuery.executing) {
			await waitUntil(() => !chart.baseQuery.executing)
		}

		prepareBaseQuery()
		setCustomFilters(filters || [])
		setChartFilters()
		let prepared = false
		if (AXIS_CHARTS.includes(chart.doc.chart_type)) {
			const _config = unref(chart.doc.config as AxisChartConfig)
			prepared = prepareAxisChartQuery(_config)
		} else if (chart.doc.chart_type === 'Number') {
			const _config = unref(chart.doc.config as NumberChartConfig)
			prepared = prepareNumberChartQuery(_config)
		} else if (chart.doc.chart_type === 'Donut') {
			const _config = unref(chart.doc.config as DountChartConfig)
			prepared = prepareDonutChartQuery(_config)
		} else if (chart.doc.chart_type === 'Table') {
			const _config = unref(chart.doc.config as TableChartConfig)
			prepared = prepareTableChartQuery(_config)
		} else {
			console.warn('Unknown chart type: ', chart.doc.chart_type)
		}

		if (prepared) {
			applySortOrder()
			applyLimit()
			if (shouldExecuteQuery(force)) {
				return executeQuery()
			}
		}
	}

	function prepareAxisChartQuery(config: AxisChartConfig) {
		if (!config.x_axis || !config.x_axis.column_name) {
			console.warn('X-axis is required')
			chart.dataQuery.reset()
			return false
		}
		if (config.x_axis.column_name === config.split_by?.column_name) {
			createToast({
				message: 'X-axis and Split by cannot be the same',
				variant: 'error',
			})
			chart.dataQuery.reset()
			return false
		}

		const values = config.y_axis?.series.map((s) => s.measure).filter((m) => m.measure_name) || [
			count(),
		]

		if (config.split_by?.column_name) {
			chart.dataQuery.addPivotWider({
				rows: [config.x_axis],
				columns: [config.split_by],
				values: values,
			})
		} else {
			chart.dataQuery.addSummarize({
				measures: values,
				dimensions: [config.x_axis],
			})
		}

		return true
	}

	function prepareNumberChartQuery(config: NumberChartConfig) {
		if (!config.number_columns?.length) {
			console.warn('Number column is required')
			chart.dataQuery.reset()
			return false
		}

		chart.dataQuery.addSummarize({
			measures: config.number_columns,
			dimensions: config.date_column?.column_name ? [config.date_column] : [],
		})

		return true
	}

	function prepareDonutChartQuery(config: DountChartConfig) {
		if (!config.label_column) {
			console.warn('Label is required')
			chart.dataQuery.reset()
			return false
		}
		if (!config.value_column) {
			console.warn('Value is required')
			chart.dataQuery.reset()
			return false
		}

		const label = config.label_column
		const value = config.value_column
		if (!label) {
			console.warn('Label column not found')
			chart.dataQuery.reset()
			return false
		}
		if (!value) {
			console.warn('Value column not found')
			chart.dataQuery.reset()
			return false
		}

		chart.dataQuery.addSummarize({
			measures: [value],
			dimensions: [label],
		})
		chart.dataQuery.addOrderBy({
			column: column(value.measure_name),
			direction: 'desc',
		})

		return true
	}

	function prepareTableChartQuery(config: TableChartConfig) {
		let rows = config.rows.filter((r) => r.column_name)
		let columns = config.columns.filter((c) => c.column_name)
		let values = config.values.filter((v) => v.measure_name)

		if (!rows.length) {
			console.warn('Rows are required')
			chart.dataQuery.reset()
			return false
		}

		if (!columns?.length) {
			chart.dataQuery.addSummarize({
				measures: values || [count()],
				dimensions: rows,
			})
		}
		if (columns?.length) {
			chart.dataQuery.addPivotWider({
				rows: rows,
				columns: columns,
				values: values || [count()],
			})
		}

		return true
	}

	function applySortOrder() {
		if (!chart.doc.config.order_by) return
		chart.doc.config.order_by.forEach((sort) => {
			if (!sort.column.column_name || !sort.direction) return
			chart.dataQuery.addOrderBy({
				column: column(sort.column.column_name),
				direction: sort.direction,
			})
		})
	}

	function applyLimit() {
		if (chart.doc.config.limit) {
			chart.dataQuery.addLimit(chart.doc.config.limit)
		}
	}

	function prepareBaseQuery() {
		chart.dataQuery.autoExecute = false
		chart.dataQuery.setOperations([])
		chart.dataQuery.setSource({
			table: query_table({
				query_name: workbookChart.query,
			}),
		})
		chart.dataQuery.doc.use_live_connection = chart.baseQuery.doc.use_live_connection
	}
	function setCustomFilters(filters: FilterArgs[]) {
		const _filters = new Set(filters)
		if (_filters.size) {
			chart.dataQuery.addFilterGroup({
				logical_operator: 'And',
				filters: Array.from(_filters),
			})
		}
	}

	const lastExecutedQueryOperations = ref<Operation[]>([])
	function shouldExecuteQuery(force = false) {
		if (force) return true
		return (
			JSON.stringify(lastExecutedQueryOperations.value) !==
			JSON.stringify(chart.dataQuery.currentOperations)
		)
	}
	async function executeQuery() {
		return chart.dataQuery.execute().then(() => {
			lastExecutedQueryOperations.value = copy(chart.dataQuery.currentOperations)
		})
	}

	function getGranularity(column_name: string): GranularityType | undefined {
		const column = Object.entries(chart.doc.config).find(([_, value]) => {
			if (!value) return false
			if (Array.isArray(value)) {
				return value.some((v) => v.column_name === column_name)
			}
			if (typeof value === 'object') {
				return value.column_name === column_name
			}
			return false
		})
		if (!column) return

		if (Array.isArray(column[1])) {
			const granularity = column[1].find((v) => v.column_name === column_name)?.granularity
			return granularity
		}

		const granularity = column[1].granularity
		return granularity
	}

	function updateGranularity(column_name: string, granularity: GranularityType) {
		Object.entries(chart.doc.config).forEach(([_, value]) => {
			if (Array.isArray(value)) {
				const index = value.findIndex((v) => v.column_name === column_name)
				if (index > -1) {
					value[index].granularity = granularity
				}
			}
			if (value.column_name === column_name) {
				value.granularity = granularity
			}
		})
	}

	function setChartFilters() {
		if (!chart.doc.config.filters?.filters?.length) return
		chart.dataQuery.addFilterGroup(chart.doc.config.filters)
	}

	chart.history = useDebouncedRefHistory(
		// @ts-ignore
		computed({
			get: () => chart.doc,
			set: (value) => Object.assign(chart.doc, value),
		}),
		{
			deep: true,
			max: 100,
			debounce: 500,
		}
	)

	return chart
}

export type Chart = ReturnType<typeof makeChart>
