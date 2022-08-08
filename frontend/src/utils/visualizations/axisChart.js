import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function axisChart(type, icon) {
	const visualization = reactive({
		type,
		icon,
		dataSchema: {
			labelColumn: true,
			valueColumn: true,
			multipleValues: true,
		},
		getComponent,
		componentProps: null,
		buildComponentProps,
	})

	function getComponent() {
		if (visualization.type == 'Bar') {
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualization/BarChart.vue')
			)
		}
		if (visualization.type == 'Line') {
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualization/LineChart.vue')
			)
		}
	}

	function buildComponentProps(query, data) {
		if (isEmptyObj(data.labelColumn, data.valueColumn)) {
			return
		}

		if (visualization.dataSchema.multipleValues && Array.isArray(data.valueColumn)) {
			visualization.componentProps = buildMultiValueChartProps(query, data)
		} else {
			visualization.componentProps = buildSingleValueChartProps(query, data)
		}
	}

	function columnsExist(query, ...columns) {
		const columnNames = query.doc.columns.map((c) => c.column)
		return columns.every((col) => columnNames.indexOf(col) !== -1)
	}

	function buildSingleValueChartProps(query, data) {
		const labelColumn = data.labelColumn?.value
		const valueColumn = data.valueColumn?.value

		if (!columnsExist(query, labelColumn, valueColumn)) {
			return null
		}

		const labels = query.results.getColumnValues(labelColumn)
		const values = query.results.getColumnValues(valueColumn)

		let labelValues = labels.map((label, idx) => ({ label, value: values[idx] }))

		// if the labels are not unique, add the values of the same label
		labelValues = labelValues.reduce((acc, curr) => {
			const existing = acc.find((item) => item.label == curr.label)
			if (existing) {
				existing.value += curr.value
			} else {
				acc.push(curr)
			}
			return acc
		}, [])

		return {
			data: {
				labels: labelValues.map((item) => item.label),
				datasets: [
					{
						label: data.valueColumn.label,
						data: labelValues.map((item) => item.value),
					},
				],
			},
		}
	}

	function buildMultiValueChartProps(query, data) {
		const labelColumn = data.labelColumn?.value
		const valueColumns = data.valueColumn.map((col) => col.value)

		if (!columnsExist(query, labelColumn, ...valueColumns)) {
			return null
		}

		const labels = query.results.getColumnValues(labelColumn)
		const values = valueColumns.map((col) => query.results.getColumnValues(col))

		let labelValues = labels.map((label, idx) => ({
			label,
			values: values.map((col) => col[idx]),
		}))

		// if the labels are not unique, add the values of the same label
		labelValues = labelValues.reduce((acc, curr) => {
			const existing = acc.find((item) => item.label == curr.label)
			if (existing) {
				existing.values = existing.values.map((value, idx) => value + curr.values[idx])
			} else {
				acc.push(curr)
			}
			return acc
		}, [])

		return {
			data: {
				labels: labelValues.map((item) => item.label),
				datasets: valueColumns.map((col, idx) => ({
					label: data.valueColumn[idx].label,
					data: labelValues.map((item) => item.values[idx]),
				})),
			},
		}
	}

	return visualization
}

export const Bar = axisChart('Bar', 'bar-chart-2')
export const Line = axisChart('Line', 'trending-up')
