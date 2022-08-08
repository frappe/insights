import { reactive, defineAsyncComponent } from 'vue'

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
	return defineAsyncComponent(() => import('@/components/Query/Visualization/PivotTransform'))
}

function buildComponentProps(query, data) {
	// request backend to perform pivot transform
	applyPivot(query, data)

	// watch for changes to transform result
	const pivotResult = computed(() => query.doc?.transform_result)
	const unwatch = watch(pivotResult, (result) => {
		if (result !== '{}') {
			// once pivot transform is complete, set props as result
			visualization.componentProps = { tableHtml: result }
		}
		unwatch()
	})

	// if previous pivot transform result exists, display it
	visualization.componentProps =
		query.doc.transform_result !== '{}' ? { tableHtml: query.doc.transform_result } : null
}

function applyPivot(query, data) {
	const pivotColumn = data.pivotColumn
	return query.applyTransform.submit({
		type: 'Pivot',
		data: {
			index_columns: query.doc.columns
				.filter((c) => c.aggregation == 'Group By' && c.label !== pivotColumn.label)
				.map((c) => c.label),
			pivot_columns: [pivotColumn.label],
		},
	})
}

export default visualization
