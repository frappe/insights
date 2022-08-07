import {
	defineAsyncComponent,
	computed,
	markRaw,
	reactive,
	watch,
	watchEffect,
	nextTick,
} from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { safeJSONParse, isEmptyObj } from '@/utils'
import { useQuery } from '@/utils/query'

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

		if (this.type == 'Number') {
			return {
				labelColumn: false,
				valueColumn: true,
				multipleValues: false,
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
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualization/BarChart.vue')
			)
		}
		if (this.type == 'Pie') {
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualization/PieChart.vue')
			)
		}
		if (this.type == 'Line') {
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualization/LineChart.vue')
			)
		}
		if (this.type == 'Number') {
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualization/NumberCard.vue')
			)
		}
		if (this.type == 'Pivot') {
			return defineAsyncComponent(() =>
				import('@/components/Query/Visualization/PivotTransform')
			)
		}
	}
}

const visualizationTypes = [
	new VisualizationType('Bar', 'bar-chart-2'),
	new VisualizationType('Line', 'trending-up'),
	new VisualizationType('Pie', 'pie-chart'),
	new VisualizationType('Number', 'hash'),
	new VisualizationType('Row', 'align-left'),
	new VisualizationType('Funnel', 'filter'),
	new VisualizationType('Pivot', 'layout'),
]

const getRandomColor = (num = 1) => {
	const colors = []
	let hue = Math.floor(Math.random() * 360)
	let lightness = num == 1 ? '60%' : '40%'
	let alpha = 1
	for (let i = 0; i < num; i++) {
		const color = `hsla(${hue}, 50%, ${lightness}, ${alpha})`
		colors.push(color)
		alpha -= 0.085
		alpha = Math.max(alpha, 0.05)
	}
	return colors
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
		query = useQuery(queryID)
	}

	watch(
		() => ({
			doc: query.doc,
			data: visualization.data,
		}),
		buildComponentProps,
		{ deep: true, immediate: true }
	)

	async function buildComponentProps({ doc, data }) {
		// reset the componentProps so that on each update the component is re-rendered
		visualization.componentProps = null
		await nextTick()

		if (!doc || isEmptyObj(data)) {
			return
		}
		if (isEmptyObj(data.labelColumn, data.valueColumn)) {
			return
		}

		const type = visualization.type
		if (type == 'Bar' || type == 'Line' || type == 'Pie') {
			// check if data.valueColumn is an array
			if (Array.isArray(data.valueColumn)) {
				visualization.componentProps = buildMultipleValueChartProps(data)
			} else {
				visualization.componentProps = buildSingleValueChartProps(type, data)
			}
			return
		}

		if (type == 'Number') {
			visualization.componentProps = buildNumberCardProps(data)
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
		const labelColumn = data.labelColumn?.value
		const valueColumn = data.valueColumn?.value

		const columnNames = query.doc.columns.map((c) => c.column)
		if (columnNames.indexOf(labelColumn) === -1 || columnNames.indexOf(valueColumn) === -1) {
			return null
		}

		const labels = query.results.getColumnValues(labelColumn)
		const values = query.results.getColumnValues(valueColumn)

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

	function buildMultipleValueChartProps(data) {
		const labelColumn = data.labelColumn?.value
		const valueColumns = data.valueColumn.map((col) => col.value)

		const columnNames = query.doc.columns.map((c) => c.column)
		if (
			columnNames.indexOf(labelColumn) === -1 ||
			valueColumns.some((col) => columnNames.indexOf(col) === -1)
		) {
			return null
		}

		const labels = query.results.getColumnValues(labelColumn)
		const values = valueColumns.map((col) => query.results.getColumnValues(col))

		let labelValues = labels.map((label, idx) => ({
			label,
			values: values.map((col) => col[idx]),
		}))

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
			data: {
				labels: labelValues.map((item) => item.label),
				datasets: valueColumns.map((col, idx) => ({
					label: data.valueColumn[idx].label,
					data: labelValues.map((item) => item.values[idx]),
				})),
			},
		}
	}

	function buildNumberCardProps(data) {
		if (isEmptyObj(data.valueColumn)) {
			return null
		}

		const valueColumn = data.valueColumn?.value

		const columnNames = query.doc.columns.map((c) => c.column)
		if (columnNames.indexOf(valueColumn) === -1) {
			return null
		}

		const value = query.results.getColumnValues(valueColumn)[0]
		return { value }
	}

	function applyPivot(data) {
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
