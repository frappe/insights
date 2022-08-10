import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

const visualization = reactive({
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
	return defineAsyncComponent(() => import('@/components/Query/Visualization/Table.vue'))
}

function columnsExist(query, ...columns) {
	const columnNames = query.doc.columns.map((c) => (c.is_expression ? c.label : c.column))
	return columns.every((c) => columnNames.includes(c))
}

function buildComponentProps(query, data) {
	if (isEmptyObj(data.columns)) {
		return null
	}
	const columnNames = data.columns.map((c) => c.value)
	if (!columnsExist(query, ...columnNames)) {
		return null
	}

	const columns = data.columns.map((c) => c.label)
	const rows = query.results.getRows(...columnNames)
	visualization.componentProps = { columns, rows }
}

export default visualization
