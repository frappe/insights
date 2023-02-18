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

	function getRows(columnLabels, data) {
		const resultHeader = data[0]?.map((d) => d.split('::')[0])
		const resultData = data.slice(1)
		return resultData.map((row) => {
			const newRow = []
			columnLabels.forEach((label) => {
				const index = resultHeader.indexOf(label)
				newRow.push(row[index])
			})
			return newRow
		})
	}

	function buildComponentProps(queryChart) {
		if (isEmptyObj(queryChart.config.columns)) {
			return null
		}
		const columns = queryChart.config.columns.map((c) => c.label)
		const rows = getRows(columns, queryChart.data)
		const title = queryChart.title
		const props = { title, columns, rows, options: queryChart.config.options }
		return props
	}

	return chart
}

export default useTableChart
