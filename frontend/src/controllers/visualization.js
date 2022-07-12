import { defineAsyncComponent } from 'vue'
import { createResource } from 'frappe-ui'

class Visualization {
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

	getComponentProps(query, data) {
		if (this.type == 'Bar' || this.type == 'Line' || this.type == 'Pie') {
			return this.getSingleValueChartProps(query, data)
		}
		if (this.type == 'Pivot') {
			return this.getPivotTransformProps(query, data)
		}
	}

	getSingleValueChartProps(query, data) {
		if (!data.labelColumn || !data.valueColumn) {
			return null
		}

		const labelColumn = data.labelColumn.value
		const valueColumn = data.valueColumn.value
		const labels = query.getColumnValues(labelColumn)
		const values = query.getColumnValues(valueColumn)

		let labelValues = labels.map((label, idx) => ({ label, value: values[idx] }))

		if (this.type == 'Pie') {
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

	getPivotTransformProps(query) {}
}

const visualizations = [
	new Visualization('Bar', 'bar-chart-2'),
	new Visualization('Line', 'trending-up'),
	new Visualization('Pie', 'pie-chart'),
	new Visualization('Row', 'align-left'),
	new Visualization('Funnel', 'filter'),
	new Visualization('Pivot', 'layout'),
]

const getVisualizationResource = createResource({
	method: 'insights.api.get_query_visualization',
})
const getVisualizationDoc = ({ queryName, onSuccess }) => {
	const options = { onSuccess }
	const params = { query: queryName }
	getVisualizationResource.submit(params, options)
}

const getVisualization = (type) => visualizations.find((v) => v.type === type)

const createVisualizationResource = createResource({
	method: 'insights.api.create_query_visualization',
})
const createVisualizationDoc = ({ queryName: query, title, type, data, onSuccess }) => {
	const options = { onSuccess }
	const params = { query, title, type, data }
	createVisualizationResource.submit(params, options)
}

const updateVisualizationResource = createResource({
	method: 'insights.api.update_query_visualization',
})
const updateVisualizationDoc = ({ docname, title, type, data, onSuccess }) => {
	const options = { onSuccess }
	const params = { docname, title, type, data }
	updateVisualizationResource.submit(params, options)
}

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

export {
	visualizations,
	getRandomColor,
	getVisualization,
	getVisualizationDoc,
	createVisualizationDoc,
	updateVisualizationDoc,
}
