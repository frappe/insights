import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function useAxisChart(type) {
	const axisChart = reactive({
		componentProps: null,
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		if (type == 'Bar') {
			return defineAsyncComponent(() => import('@/components/Query/Visualize/BarChart.vue'))
		}
		if (type == 'Line') {
			return defineAsyncComponent(() => import('@/components/Query/Visualize/LineChart.vue'))
		}
	}

	function buildComponentProps(doc) {
		if (isEmptyObj(doc.config.labelColumn, doc.config.valueColumn) || doc.data.length == 0) {
			return
		}
		return {
			title: doc.title,
			data: buildMultiValueData(doc),
			options: doc.options,
		}
	}

	function getColumnValues(column, data) {
		// data = [["col1::type", "col2::type"], ["val1", "val2"], ["val3", "val4"]]
		const columns = data[0].map((d) => d.split('::')[0])
		const index = columns.indexOf(column)
		return data.slice(1).map((row) => row[index])
	}

	function buildMultiValueData(doc) {
		const labelColumn = doc.config.labelColumn?.label
		const valueColumns = doc.config.valueColumn.map((col) => col.label)

		const labels = getColumnValues(labelColumn, doc.data)
		const values = valueColumns.map((col) => getColumnValues(col, doc.data))

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
				label: doc.config.valueColumn[idx].label,
				data: labelValues.map((item) => item.values[idx]),
			})),
		}
	}

	return axisChart
}

export function Bar() {
	return useAxisChart('Bar', 'bar-chart-2')
}
export function Line() {
	return useAxisChart('Line', 'trending-up')
}
