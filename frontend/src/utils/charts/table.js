import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function useTableChart() {
	const chart = reactive({
		type: 'Table',
		icon: 'grid',
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		return defineAsyncComponent(() => import('@/components/Query/Visualize/Table.vue'))
	}

	function getRows(columns, data) {
		const columnLabels = data[0]?.map((d) => d.split('::')[0])
		const columnIndexes = columnLabels.map((label) => columns.indexOf(label))
		return data.slice(1).map((row) => columnIndexes.map((index) => row[index]))
	}

	function buildComponentProps(queryChart) {
		if (isEmptyObj(queryChart.config.columns)) {
			return null
		}
		const columns = queryChart.config.columns.map((c) => c.label)
		const rows = getRows(columns, queryChart.data)
		const title = queryChart.title
		return { title, columns, rows, options: queryChart.config.options }
	}

	return chart
}

export default useTableChart
