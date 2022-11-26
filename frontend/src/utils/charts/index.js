import { computed, markRaw, reactive, watch, unref, nextTick } from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { safeJSONParse, isEmptyObj } from '@/utils'
import { watchDebounced } from '@vueuse/core'

import { Bar, Line } from './axisChart'
import Pie from './pieChart'
import Number from './number'
import Progress from './progress'
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
	{ type: 'Progress', icon: 'percent' },
]

const controllers = { Bar, Line, Pie, Number, Pivot, Table, Progress }

function useChart({ chartID, data }) {
	if (!chartID) return console.error('Chart ID is required')

	const resource = queryChartResource(chartID)
	const initialDoc = computed(() => resource.doc || {})

	const emptyChart = {
		title: '',
		type: '',
		data: [],
		config: {},
		options: {},
		component: null,
		componentProps: null,
	}

	const chart = reactive({
		...emptyChart,
		setType,
		updateDoc,
		addToDashboard,
	})

	chart.data = computed(() => safeJSONParse(unref(data), []))
	watch(initialDoc, loadChart, { deep: true, immediate: true })
	function loadChart(doc) {
		chart.type = doc.type
		chart.title = doc.title
		chart.config = safeJSONParse(doc.config, {})
		chart.options = chart.config.options || {}
	}

	watch(() => chart.type, makeChartComponent, { immediate: true })
	async function makeChartComponent(type, oldType) {
		if (type === oldType) return
		if (controllers[type]) {
			chart.controller = controllers[type]()
			chart.component = markRaw(chart.controller.getComponent())
			chart.componentProps = null
		} else {
			chart.controller = null
			chart.component = null
			chart.componentProps = null
			type && console.warn(`No chart controller found for type - ${type}`)
		}
	}

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
		// to force re-mount of chart component
		chart.componentProps = null
		await nextTick()

		if (!chart.controller) return
		if (isEmptyObj(chart.config)) return
		const newProps = chart.controller.buildComponentProps({ ...chart })
		chart.componentProps = newProps
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
		const initialOptions = initialConfig.options || {}
		const configChanged = JSON.stringify(initialConfig) !== JSON.stringify(chart.config)
		const optionsChanged = JSON.stringify(initialOptions) !== JSON.stringify(chart.options)

		return (
			doc.type !== chart.type || doc.title !== chart.title || configChanged || optionsChanged
		)
	})

	function addToDashboard(dashboard, layout, { onSuccess }) {
		const params = { dashboard }
		const options = { onSuccess }
		resource.addToDashboard.submit(params, options)
		if (!chart.addingToDashboard) {
			chart.addingToDashboard = computed(() => resource.addToDashboard.loading)
		}
	}

	return chart
}

const queryChartResource = (name) => {
	const resource = createDocumentResource({
		doctype: 'Insights Query Chart',
		name: name,
		whitelistedMethods: {
			updateDoc: 'update_doc',
			addToDashboard: 'add_to_dashboard',
		},
	})
	resource.get.fetch()
	return resource
}

export { types, useChart }
