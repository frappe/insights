import { computed, markRaw, reactive, watchEffect, nextTick } from 'vue'
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
	// { type: 'Row', icon: 'align-left' },
	// { type: 'Funnel', icon: 'filter' },
	// { type: 'Pivot', icon: 'layout' },
	{ type: 'Table', icon: 'grid' },
]

const controllers = { Bar, Line, Pie, Number, Pivot, Table }

function useVisualization({ visualizationID, queryID, query }) {
	if (!query) {
		query = useQuery(queryID)
	}

	const resource = visualizationDocResource(visualizationID)
	const initialDoc = computed(() => resource.doc || {})

	const visualization = reactive({
		type: '',
		title: '',
		data: {},
		controller: null,
		dataSchema: {},
		component: null,
		componentProps: null,
		setType,
		updateDoc,
		addToDashboard,
	})

	watchEffect(() => {
		// load visualization data from doc
		const doc = initialDoc.value
		if (doc.type || doc.title) {
			visualization.type = doc.type
			visualization.title = doc.title
			visualization.data = safeJSONParse(doc.data, {})
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
		// if query.doc or chart options changes then re-render visualization
		() => ({
			queryDoc: query.doc,
			options: {
				type: visualization.type,
				title: visualization.title,
				data: visualization.data,
			},
		}),
		buildComponentProps,
		{ deep: true, immediate: true, debounce: 300 }
	)

	async function buildComponentProps({ queryDoc, options }) {
		visualization.componentProps = null
		await nextTick()
		if (!query.doc || isEmptyObj(options.data)) {
			return
		}
		visualization.controller.buildComponentProps(query, options)
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

	visualization.isDirty = computed(() => {
		if (!initialDoc.value) return false

		const doc = initialDoc.value
		const initialData = safeJSONParse(doc.data, {})
		const dataChanged = JSON.stringify(initialData) !== JSON.stringify(visualization.data)
		return doc.type !== visualization.type || doc.title !== visualization.title || dataChanged
	})

	function addToDashboard(dashboard, layout, { onSuccess }) {
		const params = { dashboard, layout }
		const options = { onSuccess }
		resource.addToDashboard.submit(params, options)
		if (!visualization.addingToDashboard) {
			visualization.addingToDashboard = computed(() => resource.addToDashboard.loading)
		}
	}

	return visualization
}

const visualizationDocResource = (name) => {
	const doctype = 'Insights Query Chart'
	const whitelistedMethods = { updateDoc: 'update_doc', addToDashboard: 'add_to_dashboard' }
	return createDocumentResource({ doctype, name, whitelistedMethods })
}

export { types, useVisualization }
