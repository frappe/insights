import { defineAsyncComponent } from 'vue'

const VALID_CHARTS = [
	'Number',
	'Line',
	'Bar',
	'Pie',
	'Table',
	'Progress',
	'Scatter',
	'Funnel',
	'Trend',
]

const WIDGETS = {
	Number: {
		type: 'Number',
		component: defineAsyncComponent(() => import('./Number/Number.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Number/NumberOptions.vue')),
		options: {},
		defaultWidth: 4,
		defaultHeight: 4,
	},
	Trend: {
		type: 'Trend',
		component: defineAsyncComponent(() => import('./Trend/Trend.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Trend/TrendOptions.vue')),
		options: {},
		defaultWidth: 5,
		defaultHeight: 5,
	},
	Line: {
		type: 'Line',
		component: defineAsyncComponent(() => import('./Line/Line.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Line/LineOptions.vue')),
		options: {},
		defaultWidth: 14,
		defaultHeight: 12,
	},
	Scatter: {
		type: 'Scatter',
		component: defineAsyncComponent(() => import('./Scatter/Scatter.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Scatter/ScatterOptions.vue')),
		options: {},
		defaultWidth: 14,
		defaultHeight: 19,
	},
	Bar: {
		type: 'Bar',
		component: defineAsyncComponent(() => import('./Bar/Bar.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Bar/BarOptions.vue')),
		options: {},
		defaultWidth: 14,
		defaultHeight: 12,
	},
	Pie: {
		type: 'Pie',
		component: defineAsyncComponent(() => import('./Pie/Pie.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Pie/PieOptions.vue')),
		options: {},
		defaultWidth: 14,
		defaultHeight: 12,
	},
	Funnel: {
		type: 'Funnel',
		component: defineAsyncComponent(() => import('./Funnel/Funnel.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Funnel/FunnelOptions.vue')),
		options: {},
		defaultWidth: 14,
		defaultHeight: 12,
	},
	Table: {
		type: 'Table',
		component: defineAsyncComponent(() => import('./Table/Table.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Table/TableOptions.vue')),
		options: {},
		defaultWidth: 14,
		defaultHeight: 12,
	},
	Progress: {
		type: 'Progress',
		component: defineAsyncComponent(() => import('./Progress/Progress.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Progress/ProgressOptions.vue')),
		options: {},
		defaultWidth: 5,
		defaultHeight: 4,
	},
	Filter: {
		type: 'Filter',
		component: defineAsyncComponent(() => import('./Filter/Filter.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Filter/FilterOptions.vue')),
		options: {},
		defaultWidth: 5,
		defaultHeight: 2,
	},
	Text: {
		type: 'Text',
		component: defineAsyncComponent(() => import('./Text/Text.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Text/TextOptions.vue')),
		options: {},
		defaultWidth: 8,
		defaultHeight: 2,
	},
}

const UnknownWidget = {
	type: 'Unknown',
	component: defineAsyncComponent(() => import('@/widgets/InvalidWidget.vue')),
	optionsComponent: null,
	options: {},
	defaultWidth: 5,
	defaultHeight: 4,
}

function get(itemType) {
	return WIDGETS[itemType] || UnknownWidget
}

function getComponent(itemType) {
	return get(itemType).component
}

function getOptionComponent(itemType) {
	return get(itemType).optionsComponent
}

function getChartOptions() {
	return VALID_CHARTS.map((chart) => ({
		value: chart,
		label: chart,
	}))
}

export default {
	...WIDGETS,
	list: Object.values(WIDGETS),
	get,
	getComponent,
	getOptionComponent,
	getChartOptions,
}
