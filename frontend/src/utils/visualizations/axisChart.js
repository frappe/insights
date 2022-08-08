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
			visualization.componentProps = {
				data: buildMultiValueData(query, data),
				options: buildOptions(data),
			}
		} else {
			visualization.componentProps = {
				data: buildSingleValueData(query, data),
				options: buildOptions(data),
			}
		}
	}

	function columnsExist(query, ...columns) {
		const columnNames = query.doc.columns.map((c) => (c.is_expression ? c.label : c.column))
		return columns.every((c) => columnNames.includes(c))
	}

	function buildSingleValueData(query, data) {
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
			labels: labelValues.map((item) => item.label),
			datasets: [
				{
					label: data.valueColumn.label,
					data: labelValues.map((item) => item.value),
				},
			],
		}
	}

	function buildMultiValueData(query, data) {
		const labelColumn = data.labelColumn?.value
		const valueColumns = data.valueColumn.map((col) => col.value)

		if (!columnsExist(query, labelColumn, ...valueColumns)) {
			return null
		}

		console.log('columns exists')

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
			labels: labelValues.map((item) => item.label),
			datasets: valueColumns.map((col, idx) => ({
				label: data.valueColumn[idx].label,
				data: labelValues.map((item) => item.values[idx]),
			})),
		}
	}

	function buildOptions(data) {
		const options = {}
		if (visualization.type == 'Line') {
			options.tension = data.lineSmoothness
		}
		return options
	}

	return visualization
}

export const Bar = axisChart('Bar', 'bar-chart-2')
export const Line = axisChart('Line', 'trending-up')
