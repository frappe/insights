import { wheneverChanges } from '@/utils'
import { watchDebounced } from '@vueuse/core'
import { computed, reactive, ref, unref } from 'vue'
import { copy, getUniqueId, waitUntil } from '../helpers'
import { column, count } from '../query/helpers'
import { Query, getCachedQuery, makeQuery } from '../query/query'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	DountChartConfig,
	NumberChartConfig,
	TableChartConfig,
} from '../types/chart.types'
import { Dimension, FilterArgs, Measure, Operation } from '../types/query.types'
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
			title: '',
			operations: [],
		}),

		refresh,
	})

	wheneverChanges(
		() => chart.doc.query,
		() => {
			chart.doc.config = {} as WorkbookChart['config']
			chart.doc.config.order_by = []
			chart.dataQuery.reset()
		},
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
		if (chart.baseQuery.executing) {
			await waitUntil(() => !chart.baseQuery.executing)
		}

		resetQuery()
		setFilters(filters || [])
		if (AXIS_CHARTS.includes(chart.doc.chart_type)) {
			const _config = unref(chart.doc.config as AxisChartConfig)
			prepareAxisChartQuery(_config)
		}
		if (chart.doc.chart_type === 'Number') {
			const _config = unref(chart.doc.config as NumberChartConfig)
			prepareNumberChartQuery(_config)
		}
		if (chart.doc.chart_type === 'Donut') {
			const _config = unref(chart.doc.config as DountChartConfig)
			prepareDonutChartQuery(_config)
		}
		if (chart.doc.chart_type === 'Table') {
			const _config = unref(chart.doc.config as TableChartConfig)
			prepareTableChartQuery(_config)
		}

		applySortOrder()
		return executeQuery(force)
	}

	function prepareAxisChartQuery(config: AxisChartConfig) {
		if (!config.x_axis) {
			console.warn('X-axis is required')
			return
		}
		if (config.x_axis === config.split_by) {
			console.warn('X-axis and split-by cannot be the same')
			return
		}

		const row = chart.baseQuery.getDimension(config.x_axis)
		if (!row) {
			console.warn('X-axis column not found')
			return
		}

		const column = chart.baseQuery.getDimension(config.split_by as string)
		let values = config.y_axis
			.concat(config.y2_axis)
			?.map((y) => chart.baseQuery.getMeasure(y))
			.filter(Boolean) as Measure[]

		values = values.length ? values : [count()]

		if (column) {
			chart.dataQuery.addPivotWider({
				rows: [row],
				columns: [column],
				values: values,
			})
		} else {
			chart.dataQuery.addSummarize({
				measures: values,
				dimensions: [row],
			})
		}
	}

	function prepareNumberChartQuery(config: NumberChartConfig) {
		if (!config.number_columns?.length) {
			console.warn('Number column is required')
			return
		}

		const numbers = config.number_columns
			?.map((n) => chart.baseQuery.getMeasure(n))
			.filter(Boolean) as Measure[]

		if (!numbers?.length) {
			console.warn('Number column not found')
			return
		}

		const date = chart.baseQuery.getDimension(config.date_column as string)
		chart.dataQuery.addSummarize({
			measures: numbers,
			dimensions: date ? [date] : [],
		})
	}

	function prepareDonutChartQuery(config: DountChartConfig) {
		if (!config.label_column) {
			console.warn('Label is required')
			return
		}
		if (!config.value_column) {
			console.warn('Value is required')
			return
		}

		const label = chart.baseQuery.getDimension(config.label_column)
		const value = chart.baseQuery.getMeasure(config.value_column)
		if (!label) {
			console.warn('Label column not found')
			return
		}
		if (!value) {
			console.warn('Value column not found')
			return
		}

		chart.dataQuery.addSummarize({
			measures: [value],
			dimensions: [label],
		})
		chart.dataQuery.addOrderBy({
			column: column(value.column_name),
			direction: 'desc',
		})
	}

	function prepareTableChartQuery(config: TableChartConfig) {
		if (!config.rows.length) {
			console.warn('Rows are required')
			return
		}
		const rows = config.rows
			.map((r) => chart.baseQuery.getDimension(r))
			.filter(Boolean) as Dimension[]
		const columns = config.columns
			.map((c) => chart.baseQuery.getDimension(c))
			.filter(Boolean) as Dimension[]
		const values = config.values
			.map((v) => chart.baseQuery.getMeasure(v))
			.filter(Boolean) as Measure[]

		if (!columns.length) {
			chart.dataQuery.addSummarize({
				measures: values,
				dimensions: rows,
			})
		}
		if (columns.length) {
			chart.dataQuery.addPivotWider({
				rows: rows,
				columns: columns,
				values: values,
			})
		}
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

	function resetQuery() {
		chart.dataQuery.autoExecute = false
		chart.dataQuery.setOperations([...chart.baseQuery.currentOperations])
	}
	function setFilters(filters: FilterArgs[]) {
		const _filters = new Set(filters)
		if (_filters.size) {
			_filters.forEach((filter) => {
				chart.dataQuery.addFilter(filter)
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

	return chart
}

export type Chart = ReturnType<typeof makeChart>
