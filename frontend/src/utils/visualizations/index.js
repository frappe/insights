import { computed, markRaw, reactive, watch, watchEffect, nextTick } from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { safeJSONParse, isEmptyObj } from '@/utils'
import { useQuery } from '@/utils/query'
import { watchDebounced } from '@vueuse/core'

import { Bar, Line } from './axisChart'
import Pie from './pieChart'
import Number from './number'
import Pivot from './pivot'
import Table from './table'

const types = [
	{ type: 'Bar', icon: 'bar-chart-2' },
	{ type: 'Line', icon: 'trending-up' },
	{ type: 'Pie', icon: 'pie-chart' },
	{ type: 'Number', icon: 'hash' },
	{ type: 'Row', icon: 'align-left' },
	{ type: 'Funnel', icon: 'filter' },
	{ type: 'Pivot', icon: 'layout' },
	{ type: 'Table', icon: 'grid' },
]

const controllers = { Bar, Line, Pie, Number, Pivot, Table }

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

	if (!query) {
		query = useQuery(queryID)
	}

	const visualization = reactive({
		doc: null,
		type: '',
		title: '',
		data: {},
		controller: null,
		dataSchema: {},
		component: null,
		componentProps: null,
		setType,
		updateDoc,
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
		if (!type) return
		if (type && controllers[type]) {
			visualization.controller = controllers[type]()
			visualization.dataSchema = visualization.controller.dataSchema
			visualization.component = markRaw(visualization.controller.getComponent())
			visualization.componentProps = computed({
				get() {
					return visualization.controller.componentProps
				},
				set(value) {
					visualization.controller.componentProps = value
				},
			})
			return
		}
		console.warn(`No visualization controller found for type - ${type}`)
	})

	watchDebounced(
		// if query.doc or data changes then re-render visualization
		() => ({
			queryDoc: query.doc,
			data: visualization.data,
		}),
		({ data }) => buildComponentProps(query, data),
		{ deep: true, immediate: true, debounce: 300 }
	)

	async function buildComponentProps(query, data) {
		visualization.componentProps = null
		await nextTick()
		if (!query.doc || isEmptyObj(data)) {
			return
		}
		visualization.controller.buildComponentProps(query, data)
	}

	function setType(type) {
		visualization.type = type
		visualization.data = {}
	}

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
		if (!visualization.savingDoc) {
			visualization.savingDoc = computed(() => resource.updateDoc.loading)
		}
	}

	return visualization
}

const visualizationDocResource = (name) => {
	const doctype = 'Query Visualization'
	const whitelistedMethods = { updateDoc: 'update_doc' }
	return createDocumentResource({ doctype, name, whitelistedMethods })
}

export { types, getRandomColor, useVisualization }
