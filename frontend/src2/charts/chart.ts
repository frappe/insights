import { watchDebounced } from '@vueuse/core'
import { computed, reactive, unref } from 'vue'
import { getUniqueId } from '../helpers'
import { column, count, expression, mutate } from '../query/helpers'
import useQuery, { Query } from '../query/query'
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

function makeChart(workbookChart: WorkbookChart) {
	const chart = reactive({
		doc: workbookChart,

		baseQuery: computed(() => {
			if (!workbookChart.query) return {} as Query
			return useQuery({
				name: workbookChart.query,
				title: '',
				operations: [],
			})
		}),
		dataQuery: useQuery({
			name: 'new-query-' + getUniqueId(),
			title: '',
			operations: [],
		}),
		filters: [] as FilterArgs[],

		refresh,
		setFilters(filters: FilterArgs[]) {
			chart.filters = filters
		},
	})

	watchDebounced(() => chart.doc.config, refresh, { deep: true, debounce: 500 })

	async function refresh() {
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
			throw new Error('X-axis is required')
		}
		if (config.x_axis === config.split_by) {
			throw new Error('X-axis and split-by cannot be the same')
		}

		const row = chart.baseQuery.getDimension(config.x_axis)
		if (!row) {
			throw new Error('X-axis column not found')
		}

		const column = chart.baseQuery.getDimension(config.split_by)
		const values = config.y_axis
			?.map((y) => chart.baseQuery.getMeasure(y))
			.filter(Boolean) as Measure[]

		prepareAxisChartQuery(row, column, values)
		chart.dataQuery.execute()
	}

	function prepareAxisChartQuery(row: Dimension, column?: Dimension, values?: Measure[]) {
		values = values?.length ? values : [count()]
		resetQuery()

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
			throw new Error('Target value and target column cannot be used together')
		}
		if (config.metric_column === config.target_column) {
			throw new Error('Metric and target cannot be the same')
		}
		if (config.target_column && config.date_column) {
			throw new Error('Target and date cannot be used together')
		}

		const metric = chart.baseQuery.getMeasure(config.metric_column)
		if (!metric) {
			throw new Error('Metric column not found')
		}

		const date = chart.baseQuery.getDimension(config.date_column as string)
		const target = config.target_value
			? Number(config.target_value)
			: chart.baseQuery.getMeasure(config.target_column as string)

		prepareMetricQuery(metric, target, date)
		chart.dataQuery.execute()
	}

	function prepareMetricQuery(metric: Measure, target?: Measure | Number, date?: Dimension) {
		resetQuery()

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
			throw new Error('Label is required')
		}
		if (!config.value_column) {
			throw new Error('Value is required')
		}

		const label = chart.baseQuery.getDimension(config.label_column)
		const value = chart.baseQuery.getMeasure(config.value_column)
		if (!label) {
			throw new Error('Label column not found')
		}
		if (!value) {
			throw new Error('Value column not found')
		}

		prepareDonutQuery(label, value)
		chart.dataQuery.execute()
	}

	function prepareDonutQuery(label: Dimension, value: Measure) {
		resetQuery()

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
			throw new Error('Rows are required')
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
		chart.dataQuery.execute()
	}

	function prepareTableQuery(rows: Dimension[], columns: Dimension[], values: Measure[]) {
		resetQuery()

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

	function resetQuery() {
		chart.dataQuery.autoExecute = false
		chart.dataQuery.setOperations([...chart.baseQuery.doc.operations])
		if (chart.filters.length) {
			chart.dataQuery.addFilter(chart.filters)
		}
	}

	return chart
}

export type Chart = ReturnType<typeof makeChart>
