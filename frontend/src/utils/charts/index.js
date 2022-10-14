import { computed, markRaw, reactive, nextTick, watch } from 'vue'
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

function useQueryChart({ chartID, queryID, query }) {
	if (!query) {
		query = useQuery(queryID)
	}

	const resource = queryChartResource(chartID)
	const initialDoc = computed(() => resource.doc || {})

	const emptyChart = {
		type: '',
		data: {},
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
				chart.data = safeJSONParse(doc.data, {})
				chart.options = chart.data.options || {}
			}
		},
		{ deep: true, immediate: true }
	)

	watch(
		() => chart.type,
		(type, old) => {
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
		// if query.doc or chart options changes then re-render chart
		() => ({
			queryDoc: query.doc,
			options: {
				type: chart.type,
				title: chart.title,
				data: chart.data,
				options: chart.options,
			},
		}),
		buildComponentProps,
		{ deep: true, immediate: true, debounce: 300 }
	)

	async function buildComponentProps({ queryDoc, options }) {
		chart.componentProps = null
		await nextTick()
		if (!query.doc || isEmptyObj(options.data)) {
			return
		}
		chart.controller.buildComponentProps(query, options)
	}

	function setType(type) {
		chart.type = type
	}

	function updateDoc({ onSuccess }) {
		const params = {
			doc: {
				type: chart.type,
				title: chart.title,
				data: Object.assign({}, chart.data, {
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
		const initialData = safeJSONParse(doc.data, {})
		const initalOptions = initialData.options || {}
		const dataChanged = JSON.stringify(initialData) !== JSON.stringify(chart.data)
		const optionsChanged = JSON.stringify(initalOptions) !== JSON.stringify(chart.options)

		return doc.type !== chart.type || doc.title !== chart.title || dataChanged || optionsChanged
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

export { types, useQueryChart }
