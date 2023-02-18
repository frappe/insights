import { defineAsyncComponent, markRaw } from 'vue'

const WIDGETS = {
	Number: {
		type: 'Number',
		icon: 'hash',
		component: markRaw(defineAsyncComponent(() => import('./Number/Number.vue'))),
		optionsComponent: markRaw(defineAsyncComponent(() => import('./Number/NumberOptions.vue'))),
		options: {},
		defaultWidth: 5,
		defaultHeight: 4,
	},
	Line: {
		type: 'Line',
		icon: 'trending-up',
		component: markRaw(defineAsyncComponent(() => import('./Line/Line.vue'))),
		optionsComponent: markRaw(defineAsyncComponent(() => import('./Line/LineOptions.vue'))),
		options: {},
		defaultWidth: 10,
		defaultHeight: 8,
	},
	Bar: {
		type: 'Bar',
		icon: 'bar-chart',
		component: markRaw(defineAsyncComponent(() => import('./Bar/Bar.vue'))),
		optionsComponent: markRaw(defineAsyncComponent(() => import('./Bar/BarOptions.vue'))),
		options: {},
		defaultWidth: 10,
		defaultHeight: 8,
	},
	Pie: {
		type: 'Pie',
		icon: 'pie-chart',
		component: markRaw(defineAsyncComponent(() => import('./Pie/Pie.vue'))),
		optionsComponent: markRaw(defineAsyncComponent(() => import('./Pie/PieOptions.vue'))),
		options: {},
		defaultWidth: 10,
		defaultHeight: 8,
	},
	Table: {
		type: 'Table',
		icon: 'grid',
		component: markRaw(defineAsyncComponent(() => import('./Table/Table.vue'))),
		optionsComponent: markRaw(defineAsyncComponent(() => import('./Table/TableOptions.vue'))),
		options: {},
		defaultWidth: 12,
		defaultHeight: 8,
	},
	Progress: {
		type: 'Progress',
		icon: 'percent',
		component: markRaw(defineAsyncComponent(() => import('./Progress/Progress.vue'))),
		optionsComponent: markRaw(
			defineAsyncComponent(() => import('./Progress/ProgressOptions.vue'))
		),
		options: {},
		defaultWidth: 5,
		defaultHeight: 4,
	},
	Filter: {
		type: 'Filter',
		icon: 'filter',
		component: markRaw(defineAsyncComponent(() => import('./Filter/Filter.vue'))),
		optionsComponent: markRaw(defineAsyncComponent(() => import('./Filter/FilterOptions.vue'))),
		options: {},
		defaultWidth: 5,
		defaultHeight: 1,
	},
	Text: {
		type: 'Text',
		icon: 'align-left',
		component: markRaw(defineAsyncComponent(() => import('./Text/Text.vue'))),
		optionsComponent: markRaw(defineAsyncComponent(() => import('./Text/TextOptions.vue'))),
		options: {},
		defaultWidth: 10,
		defaultHeight: 1,
	},
}

const UnknownWidget = {
	type: 'Unknown',
	icon: 'question',
	component: markRaw(defineAsyncComponent(() => import('./UnknownWidget.vue'))),
	optionsComponent: markRaw(defineAsyncComponent(() => import('./UnknownWidget.vue'))),
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

export default {
	...WIDGETS,
	list: Object.values(WIDGETS),
	get,
	getComponent,
	getOptionComponent,
}
