import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function useTableChart() {
	const chart = reactive({
		type: 'Table',
		icon: 'grid',
		dataSchema: {
			anyColumn: true,
			multiple: true,
		},
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		return defineAsyncComponent(() => import('@/components/Query/Visualize/Table.vue'))
	}

	function columnsExist(query, ...columns) {
		const columnNames = query.doc.columns.map((c) => (c.is_expression ? c.label : c.column))
		return columns.every((c) => columnNames.includes(c))
	}

	function buildComponentProps(query, options) {
		if (isEmptyObj(options.data.columns)) {
			return null
		}
		const columnNames = options.data.columns.map((c) => c.value)
		if (!columnsExist(query, ...columnNames)) {
			return null
		}

		const columns = options.data.columns.map((c) => c.label)
		const rows = query.results.getRows(...columnNames)
		const title = options.title
		chart.componentProps = { title, columns, rows }
	}

	return chart
}

export default useTableChart
