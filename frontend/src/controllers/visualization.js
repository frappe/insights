import { defineAsyncComponent, computed, markRaw, reactive, watch, watchEffect } from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { safeJSONParse, isEmptyObj } from '@/utils'
import Query from './query'

class VisualizationType {
	constructor(type, icon) {
		this.type = type
		this.icon = icon
	}

	getDataSchema() {
		if (this.type == 'Bar' || this.type == 'Line') {
			return {
				labelColumn: true,
				valueColumn: true,
				multipleValues: true,
			}
		}

		if (this.type == 'Pie') {
			return {
				labelColumn: true,
				valueColumn: true,
				multipleValues: false,
			}
		}

		if (this.type == 'Pivot') {
			return {
				pivotColumn: true,
				multiple: true,
			}
		}

		return {}
	}

	getComponent() {
		if (this.type == 'Bar') {
			return defineAsyncComponent(() => import('@/components/Query/Visualizations/BarChart'))
		}
		if (this.type == 'Pie') {
			return defineAsyncComponent(() => import('@/components/Query/Visualizations/PieChart'))
		}
		if (this.type == 'Line') {
			return defineAsyncComponent(() => import('@/components/Query/Visualizations/LineChart'))
		}
		if (this.type == 'Pivot') {
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualizations/PivotTransform')
			)
		}
	}
}

const visualizationTypes = [
	new VisualizationType('Bar', 'bar-chart-2'),
	new VisualizationType('Line', 'trending-up'),
	new VisualizationType('Pie', 'pie-chart'),
	new VisualizationType('Row', 'align-left'),
	new VisualizationType('Funnel', 'filter'),
	new VisualizationType('Pivot', 'layout'),
]

const getRandomColor = () => {
	const colors = [
		'#B6D7F0',
		'#B9F0E0',
		'#EC94B7',
		'#B3CCE8',
		'#749AD6',
		'#536CB0',
		'#9E79AB',
		'#898FAD',
		'#25787E',
	]
	return colors[Math.floor(Math.random() * colors.length)]
}

function useVisualization({ visualizationID, queryID, query }) {
	const resource = visualizationDocResource(visualizationID)
	const doc = computed(() => resource.doc || {})

	const visualization = reactive({
		doc: null,
		type: '',
		title: '',
		data: {},
		dataSchema: {},
		component: null,
		componentProps: null,
		updateDoc: updateDoc,
	})

	watchEffect(() => {
		// load visualization data from doc
		const _doc = doc.value
		if (_doc.type || _doc.data || _doc.title) {
			visualization.doc = _doc
			visualization.type = _doc.type
			visualization.title = _doc.title
			visualization.data = safeJSONParse(_doc.data, {})
		}
	})

	watchEffect(() => {
		const type = visualization.type
		if (type) {
			const typeController = visualizationTypes.find((v) => v.type === type)
			visualization.dataSchema = typeController.getDataSchema()
			visualization.component = markRaw(typeController.getComponent())
			visualization.componentProps = null
		}
	})

	if (!query) {
		query = new Query(queryID)
	}

	watch(
		() => ({
			doc: query.doc,
			data: visualization.data,
		}),
		buildComponentProps,
		{ deep: true, immediate: true }
	)

	function buildComponentProps({ doc, data }) {
		if (!doc || isEmptyObj(data)) {
			visualization.componentProps = null
			return
		}

		const type = visualization.type
		if (type == 'Bar' || type == 'Line' || type == 'Pie') {
			visualization.componentProps = buildSingleValueChartProps(type, data)
			return
		}

		if (type == 'Pivot') {
			// request backend to perform pivot transform
			applyPivot(data)
			// if previous pivot transformed result exists, display it
			visualization.componentProps =
				query.doc.transform_result !== '{}'
					? { tableHtml: query.doc.transform_result }
					: null
			return
		}
	}

	function buildSingleValueChartProps(type, data) {
		if (!data.labelColumn || !data.valueColumn) {
			return null
		}

		const labelColumn = data.labelColumn.value
		const valueColumn = data.valueColumn.value

		const labels = query.getColumnValues(labelColumn)
		const values = query.getColumnValues(valueColumn)

		let labelValues = labels.map((label, idx) => ({ label, value: values[idx] }))

		if (type == 'Pie') {
			labelValues = labelValues.sort((a, b) => b.value - a.value)
		}

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

	function applyPivot(data) {
		const pivotColumn = data.pivotColumn
		return query.applyTransform({
			type: 'Pivot',
			data: {
				index_columns: query.columns
					.filter((c) => c.aggregation == 'Group By' && c.label !== pivotColumn.label)
					.map((c) => c.label),
				pivot_columns: [pivotColumn.label],
			},
		})
	}

	const pivotResult = computed(() => query.doc?.transform_result)
	watch(pivotResult, (result) => {
		if (result !== '{}') {
			visualization.componentProps = { tableHtml: result }
		}
	})

	function updateDoc({ onSuccess }) {
		const params = {
			doc: {
				type: visualization.type,
				title: visualization.title,
				data: visualization.data,
			},
		}
		const options = { onSuccess }
		resource.updateDoc.submit(params, options)
		visualization.savingDoc = computed(() => resource.updateDoc.loading)
	}

	return visualization
}

const visualizationDocResource = (name) => {
	const doctype = 'Query Visualization'
	const whitelistedMethods = { updateDoc: 'update_doc' }
	return createDocumentResource({ doctype, name, whitelistedMethods })
}

export { visualizationTypes, getRandomColor, useVisualization }
