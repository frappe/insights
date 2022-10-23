import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function useAxisChart(type, icon) {
	const chart = reactive({
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
		if (chart.type == 'Bar') {
			return defineAsyncComponent(() => import('@/components/Query/Visualize/BarChart.vue'))
		}
		if (chart.type == 'Line') {
			return defineAsyncComponent(() => import('@/components/Query/Visualize/LineChart.vue'))
		}
	}

	function buildComponentProps(queryChart) {
		if (
			isEmptyObj(queryChart.config.labelColumn, queryChart.config.valueColumn) ||
			queryChart.data.length == 0
		) {
			return
		}

		if (chart.dataSchema.multipleValues && Array.isArray(queryChart.config.valueColumn)) {
			chart.componentProps = {
				title: queryChart.title,
				data: buildMultiValueData(queryChart),
				options: queryChart.options,
			}
		} else {
			chart.componentProps = {
				title: queryChart.title,
				data: buildSingleValueData(queryChart),
				options: queryChart.options,
			}
		}
	}

	function getColumnValues(column, data) {
		// data = [["col1::type", "col2::type"], ["val1", "val2"], ["val3", "val4"]]
		const columns = data[0].map((d) => d.split('::')[0])
		const index = columns.indexOf(column)
		return data.slice(1).map((row) => row[index])
	}

	function buildSingleValueData(queryChart) {
		const labelColumn = queryChart.config.labelColumn?.label
		const valueColumn = queryChart.config.valueColumn?.label

		const labels = getColumnValues(labelColumn, queryChart.data)
		const values = getColumnValues(valueColumn, queryChart.data)

		let labelValues = labels.map((label, idx) => ({
			label,
			value: values[idx],
		}))

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
					label: queryChart.config.valueColumn.label,
					data: labelValues.map((item) => item.value),
				},
			],
		}
	}

	function buildMultiValueData(queryChart) {
		const labelColumn = queryChart.config.labelColumn?.label
		const valueColumns = queryChart.config.valueColumn.map((col) => col.label)

		const labels = getColumnValues(labelColumn, queryChart.data)
		const values = valueColumns.map((col) => getColumnValues(col, queryChart.data))

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
				label: queryChart.config.valueColumn[idx].label,
				data: labelValues.map((item) => item.values[idx]),
			})),
		}
	}

	return chart
}

export function Bar() {
	return useAxisChart('Bar', 'bar-chart-2')
}
export function Line() {
	return useAxisChart('Line', 'trending-up')
}
