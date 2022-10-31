import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function usePieChart() {
	const chart = reactive({
		type: 'Pie',
		icon: 'pie-chart',
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		return defineAsyncComponent(() => import('@/components/Query/Visualize/PieChart.vue'))
	}

	function buildComponentProps(queryChart) {
		if (
			isEmptyObj(queryChart.config.labelColumn, queryChart.config.valueColumn) ||
			queryChart.data.length == 0
		) {
			return
		}

		const props = buildSingleValueChartProps(queryChart)
		return {
			title: queryChart.title,
			options: queryChart.options,
			...props,
		}
	}

	function getColumnValues(column, data) {
		// data = [["col1::type", "col2::type"], ["val1", "val2"], ["val3", "val4"]]
		const columns = data[0].map((d) => d.split('::')[0])
		const index = columns.indexOf(column)
		return data.slice(1).map((row) => row[index])
	}

	function buildSingleValueChartProps(queryChart) {
		const labelColumn = queryChart.config.labelColumn?.label
		const valueColumn = queryChart.config.valueColumn?.label

		const labels = getColumnValues(labelColumn, queryChart.data)
		const values = getColumnValues(valueColumn, queryChart.data)

		let labelValues = labels
			.map((label, idx) => ({ label, value: values[idx] }))
			.sort((a, b) => b.value - a.value)

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
						label: queryChart.config.valueColumn.label,
						data: labelValues.map((item) => item.value),
					},
				],
			},
		}
	}

	return chart
}

export default usePieChart
