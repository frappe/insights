import { DataModel } from '@/datamodel/useDataModel'
import { count } from '@/query/next/query_utils'
import useQuery from '@/query/next/useQuery'
import { ChartType } from '@/widgets/widgets'
import { watchDebounced } from '@vueuse/core'
import { reactive, unref } from 'vue'
import storeLocally from './storeLocally'

const AXIS_CHART_TYPES = ['Bar', 'Line', 'Mixed']
export type AxisChartFormData = {
	x_axis: string
	y_axis: string[]
	split_by: string
}

export function useAnalysisChart(name: string, model: DataModel) {
	const chart = reactive({
		name,
		type: 'Bar' as ChartType,
		options: {} as AxisChartFormData,
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
			if (AXIS_CHART_TYPES.includes(chart.type)) {
				const _options = unref(chart.options) as AxisChartFormData
				fetchAxisChartData(_options)
			}
		},
		{ deep: true, debounce: 500 }
	)

	function fetchAxisChartData(options: AxisChartFormData) {
		const row = model.getDimension(options.x_axis)
		if (!row) return

		const column = model.getDimension(options.split_by)
		if (column && row.column_name === column.column_name) {
			throw new Error('X-axis and split-by cannot be the same')
		}

		const values = options.y_axis
			? options.y_axis.map((y) => model.getMeasure(y)).filter(Boolean)
			: []

		prepareQuery(row, column, values as Measure[])
		chart.query.execute()
	}

	function prepareQuery(row: Dimension, column: Dimension | undefined, values: Measure[]) {
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

	return chart
}

export type AnalysisChart = ReturnType<typeof useAnalysisChart>
export type AnalysisChartSerialized = ReturnType<AnalysisChart['serialize']>
