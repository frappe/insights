import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function usePieChart() {
	const chart = reactive({
		type: 'Pie',
		icon: 'pie-chart',
		dataSchema: {
			labelColumn: true,
			valueColumn: true,
			multipleValues: false,
		},
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		return defineAsyncComponent(() => import('@/components/Query/Visualize/PieChart.vue'))
	}

	function buildComponentProps(query, options) {
		if (isEmptyObj(options.data.labelColumn, options.data.valueColumn)) {
			return
		}
		const props = buildSingleValueChartProps(query, options.data)
		chart.componentProps = {
			title: options.title,
			...props,
		}
	}

	function columnsExist(query, ...columns) {
		const columnNames = query.doc.columns.map((c) => (c.is_expression ? c.label : c.column))
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
						label: data.valueColumn.label,
						data: labelValues.map((item) => item.value),
					},
				],
			},
		}
	}

	return chart
}

export default usePieChart
