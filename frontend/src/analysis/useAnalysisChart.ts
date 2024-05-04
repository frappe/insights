import { DataModel } from '@/datamodel/useDataModel'
import { count, expression, mutate } from '@/query/next/query_utils'
import useQuery from '@/query/next/useQuery'
import { watchDebounced } from '@vueuse/core'
import { reactive, unref } from 'vue'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	ChartConfig,
	ChartType,
	MetricChartConfig,
} from './components/chart_utils'
import storeLocally from './storeLocally'

export function useAnalysisChart(name: string, model: DataModel) {
	const chart = reactive({
		name,
		type: 'Bar' as ChartType,
		options: {} as ChartConfig,
		query: useQuery(name),

		serialize() {
			return {
				name: chart.name,
				type: chart.type,
				options: chart.options,
			}
		},
	})

	const storedChart = storeLocally<AnalysisChartSerialized>({
		key: 'name',
		namespace: 'insights:analysis-chart:',
		serializeFn: chart.serialize,
		defaultValue: {} as AnalysisChartSerialized,
	})
	if (storedChart.value.name === chart.name) {
		Object.assign(chart, storedChart.value)
	}

	watchDebounced(
		() => chart.options,
		async () => {
			if (AXIS_CHARTS.includes(chart.type)) {
				const _options = unref(chart.options as AxisChartConfig)
				fetchAxisChartData(_options)
			}
			if (chart.type === 'Metric') {
				const _options = unref(chart.options as MetricChartConfig)
				fetchMetricChartData(_options)
			}
		},
		{ deep: true, debounce: 500 }
	)

	function fetchAxisChartData(options: AxisChartConfig) {
		if (!options.x_axis) {
			throw new Error('X-axis is required')
		}
		if (options.x_axis === options.split_by) {
			throw new Error('X-axis and split-by cannot be the same')
		}

		const row = model.getDimension(options.x_axis)
		if (!row) {
			throw new Error('X-axis column not found')
		}

		const column = model.getDimension(options.split_by)
		const values = options.y_axis?.map((y) => model.getMeasure(y)).filter(Boolean) as Measure[]

		prepareAxisChartQuery(row, column, values)
		chart.query.execute()
	}

	function prepareAxisChartQuery(row: Dimension, column: Dimension | undefined, values: Measure[]) {
		values = values.length ? values : [count()]
		const modelQuery = model.queries[0]
		chart.query.autoExecute = false
		chart.query.setDataSource(modelQuery.dataSource)
		chart.query.setOperations([...modelQuery.operations])

		if (column) {
			chart.query.addPivotWider({
				rows: [row],
				columns: [column],
				values: values,
			})
		} else {
			chart.query.addSummarize({
				measures: values,
				dimensions: [row],
			})
		}
	}

	function fetchMetricChartData(options: MetricChartConfig) {
		if (options.target_value && options.target_column) {
			throw new Error('Target value and target column cannot be used together')
		}
		if (options.metric_column === options.target_column) {
			throw new Error('Metric and target cannot be the same')
		}
		if (options.target_column && options.date_column) {
			throw new Error('Target and date cannot be used together')
		}

		const metric = model.getMeasure(options.metric_column)
		if (!metric) {
			throw new Error('Metric column not found')
		}

		const date = model.getDimension(options.date_column as string)
		const target = options.target_value
			? Number(options.target_value)
			: model.getMeasure(options.target_column as string)

		prepareMetricQuery(metric, target, date)
		chart.query.execute()
	}

	function prepareMetricQuery(metric: Measure, target?: Measure | Number, date?: Dimension) {
		const modelQuery = model.queries[0]
		chart.query.autoExecute = false
		chart.query.setDataSource(modelQuery.dataSource)
		chart.query.setOperations([...modelQuery.operations])

		if (typeof target === 'number' && target > 0) {
			chart.query.addSummarize({
				measures: [metric],
				dimensions: [],
			})
			chart.query.addMutate(
				mutate({
					new_name: 'target',
					data_type: 'Decimal',
					mutation: expression(`literal(${target})`),
				})
			)
		} else if (typeof target === 'object') {
			chart.query.addSummarize({
				measures: [metric, target] as Measure[],
				dimensions: [],
			})
		} else if (date) {
			chart.query.addSummarize({
				measures: [metric],
				dimensions: [date],
			})
		} else {
			chart.query.addSummarize({
				measures: [metric],
				dimensions: [],
			})
		}
	}

	return chart
}

export type AnalysisChart = ReturnType<typeof useAnalysisChart>
export type AnalysisChartSerialized = ReturnType<AnalysisChart['serialize']>
