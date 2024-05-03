import { DataModel } from '@/datamodel/useDataModel'
import { count } from '@/query/next/query_utils'
import useQuery, { QueryResultColumn, QueryResultRow } from '@/query/next/useQuery'
import { ChartType } from '@/widgets/widgets'
import { reactive, unref, watch } from 'vue'
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

		data: {
			columns: [] as QueryResultColumn[],
			rows: [] as QueryResultRow[],
		},

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

	watch(
		() => chart.options,
		async () => {
			if (AXIS_CHART_TYPES.includes(chart.type)) {
				const _options = unref(chart.options) as AxisChartFormData
				fetchAxisChartData(_options)
			}
		},
		{ deep: true, immediate: true }
	)

	function fetchAxisChartData(options: AxisChartFormData) {
		const row = model.getDimension(options.x_axis)
		if (!row) return

		const column = model.getDimension(options.split_by)
		const values = options.y_axis
			? options.y_axis.map((y) => model.getMeasure(y)).filter(Boolean)
			: []

		const query = prepareQuery(row, column, values as Measure[])
		query.execute().then(() => {
			chart.data.columns = query.result.columns
			chart.data.rows = query.result.rows
		})
	}

	function prepareQuery(row: Dimension, column: Dimension | undefined, values: Measure[]) {
		values = values.length ? values : [count()]
		const query = model.queries[0].duplicate()

		if (column) {
			query.addPivotWider({
				rows: [row],
				columns: [column],
				values: values,
			})
		} else {
			query.addSummarize({
				measures: values,
				dimensions: [row],
			})
		}

		return query
	}

	return chart
}

export type AnalysisChart = ReturnType<typeof useAnalysisChart>
export type AnalysisChartSerialized = ReturnType<AnalysisChart['serialize']>
