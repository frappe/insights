import ComboChartIcon from '@/components/Icons/ComboChartIcon.vue'
import {
	AlignLeft,
	BarChart3,
	BatteryMedium,
	DollarSign,
	GitBranch,
	LineChart,
	ListFilter,
	PieChart,
	ScatterChart,
	Sparkles,
	Square,
	Table,
	TextCursorInput,
	TrendingUp,
} from 'lucide-vue-next'
import { defineAsyncComponent } from 'vue'

export const VALID_CHARTS = [
	'Number',
	'Line',
	'Bar',
	'Pie',
	'Table',
	'Progress',
	'Scatter',
	'Funnel',
	'Trend',
	'Mixed Axis',
	'Pivot Table',
]

const WIDGETS = {
	Number: {
		type: 'Number',
		icon: DollarSign,
		component: defineAsyncComponent(() => import('./Number/Number.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Number/NumberOptions.vue')),
		options: {},
		defaultWidth: 4,
		defaultHeight: 4,
	},
	Trend: {
		type: 'Trend',
		icon: TrendingUp,
		component: defineAsyncComponent(() => import('./Trend/Trend.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Trend/TrendOptions.vue')),
		options: {},
		defaultWidth: 5,
		defaultHeight: 5,
	},
	Line: {
		type: 'Line',
		icon: LineChart,
		component: defineAsyncComponent(() => import('./Line/Line.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Line/LineOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
	},
	Scatter: {
		type: 'Scatter',
		icon: ScatterChart,
		component: defineAsyncComponent(() => import('./Scatter/Scatter.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Scatter/ScatterOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
	},
	Bar: {
		type: 'Bar',
		icon: BarChart3,
		component: defineAsyncComponent(() => import('./Bar/Bar.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Bar/BarOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
	},
	Pie: {
		type: 'Pie',
		icon: PieChart,
		component: defineAsyncComponent(() => import('./Pie/Pie.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Pie/PieOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
	},
	Funnel: {
		type: 'Funnel',
		icon: ListFilter,
		component: defineAsyncComponent(() => import('./Funnel/Funnel.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Funnel/FunnelOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
	},
	Table: {
		type: 'Table',
		icon: Table,
		component: defineAsyncComponent(() => import('./Table/Table.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Table/TableOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
	},
	Progress: {
		type: 'Progress',
		icon: BatteryMedium,
		component: defineAsyncComponent(() => import('./Progress/Progress.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Progress/ProgressOptions.vue')),
		options: {},
		defaultWidth: 5,
		defaultHeight: 4,
	},
	'Mixed Axis': {
		type: 'Mixed Axis',
		icon: ComboChartIcon,
		component: defineAsyncComponent(() => import('./MixedAxis/MixedAxis.vue')),
		optionsComponent: defineAsyncComponent(() => import('./MixedAxis/MixedAxisOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
	},
	Filter: {
		type: 'Filter',
		icon: TextCursorInput,
		component: defineAsyncComponent(() => import('./Filter/Filter.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Filter/FilterOptions.vue')),
		options: {},
		defaultWidth: 5,
		defaultHeight: 2,
	},
	Text: {
		type: 'Text',
		icon: AlignLeft,
		component: defineAsyncComponent(() => import('./Text/Text.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Text/TextOptions.vue')),
		options: {},
		defaultWidth: 8,
		defaultHeight: 2,
	},
	'Pivot Table': {
		type: 'Pivot Table',
		icon: GitBranch,
		component: defineAsyncComponent(() => import('./PivotTable/PivotTable.vue')),
		optionsComponent: defineAsyncComponent(() => import('./PivotTable/PivotTableOptions.vue')),
		options: {},
		defaultWidth: 16,
		defaultHeight: 14,
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

export function getIcon(itemType) {
	if (!itemType) return
	if (itemType == 'Auto') return Sparkles
	if (!get(itemType)) return Square
	return get(itemType).icon
}

export default {
	...WIDGETS,
	list: Object.values(WIDGETS),
	get,
	getComponent,
	getOptionComponent,
	getChartOptions,
	getIcon,
}
