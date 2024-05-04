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
		config: {} as ChartConfig,
		query: useQuery(name),

		serialize() {
			return {
				name: chart.name,
				type: chart.type,
				config: chart.config,
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
		() => chart.config,
		async () => {
			if (AXIS_CHARTS.includes(chart.type)) {
				const _config = unref(chart.config as AxisChartConfig)
				fetchAxisChartData(_config)
			}
			if (chart.type === 'Metric') {
				const _config = unref(chart.config as MetricChartConfig)
				fetchMetricChartData(_config)
			}
		},
		{ deep: true, debounce: 500 }
	)

	function fetchAxisChartData(config: AxisChartConfig) {
		if (!config.x_axis) {
			throw new Error('X-axis is required')
		}
		if (config.x_axis === config.split_by) {
			throw new Error('X-axis and split-by cannot be the same')
		}

		const row = model.getDimension(config.x_axis)
		if (!row) {
			throw new Error('X-axis column not found')
		}

		const column = model.getDimension(config.split_by)
		const values = config.y_axis?.map((y) => model.getMeasure(y)).filter(Boolean) as Measure[]

		prepareAxisChartQuery(row, column, values)
		chart.query.execute()
	}

	function prepareAxisChartQuery(row: Dimension, column?: Dimension, values?: Measure[]) {
		values = values?.length ? values : [count()]
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

		const metric = model.getMeasure(config.metric_column)
		if (!metric) {
			throw new Error('Metric column not found')
		}

		const date = model.getDimension(config.date_column as string)
		const target = config.target_value
			? Number(config.target_value)
			: model.getMeasure(config.target_column as string)

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
