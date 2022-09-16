import { reactive, defineAsyncComponent, watch } from 'vue'

function usePivotChart() {
	const visualization = reactive({
		type: 'Pivot',
		icon: 'layout',
		dataSchema: {
			pivotColumn: true,
		},
		getComponent,
		buildComponentProps,
	})

	function getComponent() {
		return defineAsyncComponent(() =>
			import('@/components/Query/Visualization/PivotTransform.vue')
		)
	}

	function buildComponentProps(query, options) {
		// request backend to perform pivot transform
		applyPivot(query, options.data)

		// watch for changes to transform result
		const unwatch = watch(
			() => query.doc?.transform_result,
			(result) => {
				if (result !== '{}') {
					// once pivot transform is complete, set props as result
					visualization.componentProps = {
						title: options.title,
						tableHtml: result,
					}
				}
				unwatch()
			}
		)

		// if previous pivot transform result exists, display it
		visualization.componentProps =
			query.doc.transform_result !== '{}'
				? {
						title: options.title,
						tableHtml: query.doc.transform_result,
				  }
				: null
	}

	function applyPivot(query, data) {
		const pivotColumn = data.pivotColumn
		const pivotData = {
			index_columns: query.doc.columns
				.filter((c) => c.aggregation == 'Group By' && c.label !== pivotColumn.label)
				.map((c) => c.label),
			pivot_columns: [pivotColumn.label],
		}
		return query.applyTransform.submit({
			type: 'Pivot',
			data: pivotData,
		})
	}
	return visualization
}

export default usePivotChart
