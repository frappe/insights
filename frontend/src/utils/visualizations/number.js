import { reactive, defineAsyncComponent } from 'vue'
import { isEmptyObj } from '@/utils'

function useNumberChart() {
	const visualization = reactive({
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
		return defineAsyncComponent(() => import('@/components/Query/Visualization/NumberCard.vue'))
	}

	function buildComponentProps(query, data) {
		if (isEmptyObj(data.valueColumn)) {
			return null
		}
		const valueColumn = data.valueColumn?.value
		if (
			!query.doc.columns.some((c) =>
				c.is_expression ? c.label === valueColumn : c.column === valueColumn
			)
		) {
			return null
		}

		const value = query.results.getColumnValues(valueColumn)[0]
		visualization.componentProps = { value }
	}

	return visualization
}

export default useNumberChart
