import { wheneverChanges } from '@/utils'
import { watchDebounced } from '@vueuse/core'
import { computed, reactive, ref, unref } from 'vue'
import { copy, getUniqueId, waitUntil } from '../helpers'
import { createToast } from '../helpers/toasts'
import { column, count } from '../query/helpers'
import { Query, getCachedQuery, makeQuery } from '../query/query'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	DountChartConfig,
	NumberChartConfig,
	TableChartConfig,
} from '../types/chart.types'
import { Dimension, FilterArgs, GranularityType, Measure, Operation } from '../types/query.types'
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
	})

	wheneverChanges(
		() => chart.doc.query,
		() => {
			chart.doc.config = {} as WorkbookChart['config']
			chart.doc.config.order_by = []
			chart.dataQuery.reset()
		},
	)

	wheneverChanges(
		() => chart.baseQuery.result?.totalRowCount,
		() => refresh(),
	)

	watchDebounced(
		() => chart.doc.config,
		() => refresh(),
		{
			deep: true,
			debounce: 500,
		},
	)

	async function refresh(filters?: FilterArgs[], force = false) {
		if (!workbookChart.query) return
		if (!chart.doc.chart_type) return
		if (chart.baseQuery.executing) {
			await waitUntil(() => !chart.baseQuery.executing)
		}

		prepareBaseQuery()
		setFilters(filters || [])
		applyFilters()
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
			return executeQuery(force)
		}
	}

	function prepareAxisChartQuery(config: AxisChartConfig) {
		if (!config.x_axis || !config.x_axis.column_name) {
			console.warn('X-axis is required')
			return false
		}
		if (config.x_axis.column_name === config.split_by?.column_name) {
			createToast({
				message: 'X-axis and Split by cannot be the same',
				variant: 'error',
			})
			return false
		}

		let values = [...config.y_axis, ...(config.y2_axis || [])]
		values = values.length ? values : [count()]

		if (config.split_by) {
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
			return false
		}
		if (!config.value_column) {
			console.warn('Value is required')
			return false
		}

		const label = config.label_column
		const value = config.value_column
		if (!label) {
			console.warn('Label column not found')
			return false
		}
		if (!value) {
			console.warn('Value column not found')
			return false
		}

		chart.dataQuery.addSummarize({
			measures: [value],
			dimensions: [label],
		})
		chart.dataQuery.addOrderBy({
			column: column(value.column_name),
			direction: 'desc',
		})

		return true
	}

	function prepareTableChartQuery(config: TableChartConfig) {
		if (!config.rows.length) {
			console.warn('Rows are required')
			return false
		}
		let rows = config.rows
			.map((r) => chart.baseQuery.getDimension(r))
			.filter(Boolean) as Dimension[]
		let columns = config.columns
			?.map((c) => chart.baseQuery.getDimension(c))
			.filter(Boolean) as Dimension[]
		let values = config.values
			?.map((v) => chart.baseQuery.getMeasure(v))
			.filter(Boolean) as Measure[]

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

	function prepareBaseQuery() {
		chart.dataQuery.autoExecute = false
		chart.dataQuery.setOperations([...chart.baseQuery.doc.operations])
		chart.dataQuery.doc.use_live_connection = chart.baseQuery.doc.use_live_connection
		chart.baseQuery.activeOperationIdx = chart.baseQuery.doc.operations.length - 1
	}
	function setFilters(filters: FilterArgs[]) {
		const _filters = new Set(filters)
		if (_filters.size) {
			chart.dataQuery.addFilterGroup({
				logical_operator: 'And',
				filters: Array.from(_filters),
			})
		}
	}

	const lastExecutedQueryOperations = ref<Operation[]>([])
	async function executeQuery(force = false) {
		if (
			!force &&
			JSON.stringify(lastExecutedQueryOperations.value) ===
				JSON.stringify(chart.dataQuery.currentOperations)
		) {
			return Promise.resolve()
		}
		return chart.dataQuery.execute().then(() => {
			lastExecutedQueryOperations.value = copy(chart.dataQuery.currentOperations)
		})
	}

	function getGranularity(column_name: string) {
		const granularity = Object.entries(chart.doc.config).find(([_, value]) => {
			if (Array.isArray(value)) {
				return value.some((v) => v.column_name === column_name)
			}
			return value.column_name === column_name
		})?.[1].granularity
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

	function applyFilters() {
		if (!chart.doc.config.filters?.filters?.length) return
		chart.dataQuery.addFilterGroup(chart.doc.config.filters)
	}

	return chart
}

export type Chart = ReturnType<typeof makeChart>
