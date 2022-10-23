import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function useNumberChart() {
	const chart = reactive({
		type: 'Number',
		icon: 'hash',
		dataSchema: {
			labelColumn: false,
			valueColumn: true,
			multipleValues: false,
		},
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		return defineAsyncComponent(() => import('@/components/Query/Visualize/NumberCard.vue'))
	}

	function getColumnValues(column, data) {
		// data = [["col1::type", "col2::type"], ["val1", "val2"], ["val3", "val4"]]
		const columns = data[0].map((d) => d.split('::')[0])
		const index = columns.indexOf(column)
		return data.slice(1).map((row) => row[index])
	}

	function buildComponentProps(queryChart) {
		if (isEmptyObj(queryChart.config.valueColumn) || queryChart.data.length == 0) {
			return
		}
		const valueColumn = queryChart.config.valueColumn?.label
		const value = getColumnValues(valueColumn, queryChart.data)[0]
		chart.componentProps = {
			data: {
				value,
				title: queryChart.title,
			},
			options: queryChart.options,
		}
	}

	return chart
}

export default useNumberChart
