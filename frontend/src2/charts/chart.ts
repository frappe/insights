import { wheneverChanges } from '@/utils'
import { watchDebounced } from '@vueuse/core'
import { computed, reactive, unref } from 'vue'
import { getUniqueId } from '../helpers'
import { column, count, expression, mutate } from '../query/helpers'
import { Query, getCachedQuery, makeQuery } from '../query/query'
import { WorkbookChart } from '../workbook/workbook'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	DountChartConfig,
	MetricChartConfig,
	TableChartConfig,
} from './helpers'

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
		sortOrder: {} as Record<string, 'asc' | 'desc' | undefined>,

		refresh,

		sortByColumn(column: string) {
			const existingDirection = chart.sortOrder[column]
			chart.sortOrder = {
				[column]: !existingDirection ? 'asc' : existingDirection === 'asc' ? 'desc' : undefined,
			}
			refresh()
		},
	})

	wheneverChanges(
		() => chart.baseQuery?.currentOperations,
		() => refresh(),
		{
			deep: true,
			debounce: 500,
		}
	)

	watchDebounced(
		() => chart.doc.config,
		() => refresh(),
		{
			deep: true,
			debounce: 500,
		}
	)

	async function refresh(filters?: FilterArgs[]) {
		if (!workbookChart.query) return
		if (chart.baseQuery.executing) return

		resetQuery(filters)
		if (AXIS_CHARTS.includes(chart.doc.chart_type)) {
			const _config = unref(chart.doc.config as AxisChartConfig)
			fetchAxisChartData(_config)
		}
		if (chart.doc.chart_type === 'Metric') {
			const _config = unref(chart.doc.config as MetricChartConfig)
			fetchMetricChartData(_config)
		}
		if (chart.doc.chart_type === 'Donut') {
			const _config = unref(chart.doc.config as DountChartConfig)
			fetchDonutChartData(_config)
		}
		if (chart.doc.chart_type === 'Table') {
			const _config = unref(chart.doc.config as TableChartConfig)
			fetchTableChartData(_config)
		}
	}

	function fetchAxisChartData(config: AxisChartConfig) {
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

		const column = chart.baseQuery.getDimension(config.split_by)
		const values = config.y_axis
			?.map((y) => chart.baseQuery.getMeasure(y))
			.filter(Boolean) as Measure[]

		prepareAxisChartQuery(row, column, values)
		applySortOrder()
		chart.dataQuery.execute()
	}

	function prepareAxisChartQuery(row: Dimension, column?: Dimension, values?: Measure[]) {
		values = values?.length ? values : [count()]

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

	function fetchMetricChartData(config: MetricChartConfig) {
		if (config.target_value && config.target_column) {
			console.warn('Target value and target column cannot be used together')
			return
		}
		if (config.metric_column === config.target_column) {
			console.warn('Metric and target cannot be the same')
			return
		}
		if (config.target_column && config.date_column) {
			console.warn('Target and date cannot be used together')
			return
		}

		const metric = chart.baseQuery.getMeasure(config.metric_column)
		if (!metric) {
			console.warn('Metric column not found')
			return
		}

		const date = chart.baseQuery.getDimension(config.date_column as string)
		const target = config.target_value
			? Number(config.target_value)
			: chart.baseQuery.getMeasure(config.target_column as string)

		prepareMetricQuery(metric, target, date)
		applySortOrder()
		chart.dataQuery.execute()
	}

	function prepareMetricQuery(metric: Measure, target?: Measure | Number, date?: Dimension) {
		if (typeof target === 'number' && target > 0) {
			chart.dataQuery.addSummarize({
				measures: [metric],
				dimensions: [],
			})
			chart.dataQuery.addMutate(
				mutate({
					new_name: 'target',
					data_type: 'Decimal',
					mutation: expression(`literal(${target})`),
				})
			)
		} else if (typeof target === 'object') {
			chart.dataQuery.addSummarize({
				measures: [metric, target] as Measure[],
				dimensions: [],
			})
		} else if (date) {
			chart.dataQuery.addSummarize({
				measures: [metric],
				dimensions: [date],
			})
		} else {
			chart.dataQuery.addSummarize({
				measures: [metric],
				dimensions: [],
			})
		}
	}

	function fetchDonutChartData(config: DountChartConfig) {
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

		prepareDonutQuery(label, value)
		applySortOrder()
		chart.dataQuery.execute()
	}

	function prepareDonutQuery(label: Dimension, value: Measure) {
		chart.dataQuery.addSummarize({
			measures: [value],
			dimensions: [label],
		})
		chart.dataQuery.addOrderBy({
			column: column(value.column_name),
			direction: 'desc',
		})
	}

	function fetchTableChartData(config: TableChartConfig) {
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

		prepareTableQuery(rows, columns, values)
		applySortOrder()
		chart.dataQuery.execute()
	}

	function prepareTableQuery(rows: Dimension[], columns: Dimension[], values: Measure[]) {
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
		Object.entries(chart.sortOrder).forEach(([column_name, direction]) => {
			if (direction) {
				chart.dataQuery.addOrderBy({
					column: column(column_name),
					direction,
				})
			}
		})
	}

	function resetQuery(filters?: FilterArgs[]) {
		chart.dataQuery.reset()
		chart.dataQuery.autoExecute = false
		chart.dataQuery.setOperations([...chart.baseQuery.currentOperations])
		const _filters = new Set(filters)
		if (_filters.size) {
			_filters.forEach((filter) => {
				chart.dataQuery.addFilter(filter)
			})
		}
	}

	return chart
}

export type Chart = ReturnType<typeof makeChart>
