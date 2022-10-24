import { computed, markRaw, reactive, nextTick, watch } from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { safeJSONParse, isEmptyObj } from '@/utils'
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

function useChart({ chartID, data }) {
	if (!chartID) {
		console.error('Chart ID is required')
		return
	}

	const resource = queryChartResource(chartID)
	const initialDoc = computed(() => resource.doc || {})

	const emptyChart = {
		type: '',
		data: [],
		config: {},
		options: {},
		dataSchema: {},
		controller: null,
		component: null,
		componentProps: null,
	}

	const chart = reactive({
		title: '',
		...emptyChart,
		setType,
		updateDoc,
		addToDashboard,
	})

	watch(
		initialDoc,
		(doc) => {
			// load chart data from doc
			if (doc.type || doc.title) {
				chart.type = doc.type
				chart.title = doc.title
				chart.config = safeJSONParse(doc.config, {})
				chart.options = chart.config.options || {}
				if (data) {
					chart.data = safeJSONParse(data.value || data, [])
				}
			}
		},
		{ deep: true, immediate: true }
	)

	watch(
		() => data.value || data,
		(newData) => {
			chart.data = safeJSONParse(newData, [])
		},
		{ immediate: true, deep: true }
	)

	watch(
		() => chart.type,
		(type) => {
			if (!type) {
				Object.assign(chart, emptyChart)
				return
			}
			if (type && controllers[type]) {
				chart.controller = controllers[type]()
				chart.dataSchema = chart.controller.dataSchema
				chart.component = markRaw(chart.controller.getComponent())
				return
			}
			console.warn(`No chart controller found for type - ${type}`)
		},
		{ immediate: true }
	)

	watchDebounced(
		() => chart.controller?.componentProps,
		(props) => {
			chart.componentProps = props
		},
		{ deep: true, immediate: true }
	)

	watchDebounced(
		// re-render chart if one of these props change
		() => ({
			type: chart.type,
			title: chart.title,
			data: chart.data,
			config: chart.config,
			options: chart.options,
		}),
		buildComponentProps,
		{ deep: true, immediate: true, debounce: 300 }
	)

	async function buildComponentProps() {
		chart.componentProps = null
		await nextTick()
		if (isEmptyObj(chart.config)) {
			return
		}
		chart.controller.buildComponentProps({ ...chart })
	}

	function setType(type) {
		chart.type = type
	}

	function updateDoc({ onSuccess }) {
		const params = {
			doc: {
				type: chart.type,
				title: chart.title,
				config: Object.assign({}, chart.config, {
					options: chart.options,
				}),
			},
		}
		const options = { onSuccess }
		resource.updateDoc.submit(params, options)
		if (!chart.savingDoc) {
			chart.savingDoc = computed(() => resource.updateDoc.loading)
		}
	}

	chart.isDirty = computed(() => {
		if (!initialDoc.value) return false

		const doc = initialDoc.value
		const initialConfig = safeJSONParse(doc.config, {})
		const configChanged = JSON.stringify(initialConfig) !== JSON.stringify(chart.config)

		return doc.type !== chart.type || doc.title !== chart.title || configChanged
	})

	function addToDashboard(dashboard, layout, { onSuccess }) {
		const params = { dashboard, layout }
		const options = { onSuccess }
		resource.addToDashboard.submit(params, options)
		if (!chart.addingToDashboard) {
			chart.addingToDashboard = computed(() => resource.addToDashboard.loading)
		}
	}

	return chart
}

const queryChartResource = (name) => {
	const doctype = 'Insights Query Chart'
	const whitelistedMethods = {
		updateDoc: 'update_doc',
		addToDashboard: 'add_to_dashboard',
	}
	return createDocumentResource({ doctype, name, whitelistedMethods })
}

export { types, useChart }
