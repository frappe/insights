import { DataModel } from '@/datamodel/useDataModel'
import { QueryResultColumn, QueryResultRow } from '@/query/next/useQuery'
import { ChartType } from '@/widgets/widgets'
import { reactive, unref, watch } from 'vue'
import storeLocally from './storeLocally'
import { useAnalysisQuery } from './useAnalysisQuery'

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
				if (!_options.x_axis || !_options.y_axis || !_options.y_axis.length) {
					return
				}
				fetchAxisChartData(_options)
			}
		},
		{ deep: true, immediate: true }
	)

	function fetchAxisChartData(options: AxisChartFormData) {
		const xDim = model.getDimension(options.x_axis)
		const splitByDim = model.getDimension(options.split_by)
		const yMeasures = options.y_axis.map((y) => model.getMeasure(y))

		if (!xDim || !yMeasures.length || yMeasures.some((m) => !m)) {
			return
		}

		const query = useAnalysisQuery(Math.random().toString(), model)
		query.reset()
		query.addRow(xDim)
		splitByDim && query.addColumn(splitByDim)
		yMeasures.forEach((m) => m && query.addValue(m))

		query.execute().then(() => {
			chart.data.columns = query.result.columns
			chart.data.rows = query.result.rows
		})
	}

	return chart
}

export type AnalysisChart = ReturnType<typeof useAnalysisChart>
export type AnalysisChartSerialized = ReturnType<AnalysisChart['serialize']>
