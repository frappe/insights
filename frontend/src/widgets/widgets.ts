import ComboChartIcon from '@/components/Icons/ComboChartIcon.vue'
import {
	AlignLeft,
	BarChart3,
	BarChartHorizontal,
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
import defaultWidgetDimensions from './widgetDimensions.json'

export const VALID_CHARTS = [
	'Number',
	'Line',
	'Bar',
	'Row',
	'Pie',
	'Table',
	'Progress',
	'Scatter',
	'Funnel',
	'Trend',
	'Mixed Axis',
	'Pivot Table',
] as const

const WIDGETS = {
	Auto: {
		type: 'Auto',
		icon: Sparkles,
		component: undefined,
		optionsComponent: undefined,
		options: {},
	},
	Number: {
		type: 'Number',
		icon: DollarSign,
		component: defineAsyncComponent(() => import('./Number/Number.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Number/NumberOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Number,
	},
	Trend: {
		type: 'Trend',
		icon: TrendingUp,
		component: defineAsyncComponent(() => import('./Trend/Trend.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Trend/TrendOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Trend,
	},
	Line: {
		type: 'Line',
		icon: LineChart,
		component: defineAsyncComponent(() => import('./Line/Line.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Line/LineOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Line,
	},
	Scatter: {
		type: 'Scatter',
		icon: ScatterChart,
		component: defineAsyncComponent(() => import('./Scatter/Scatter.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Scatter/ScatterOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Scatter,
	},
	Bar: {
		type: 'Bar',
		icon: BarChart3,
		component: defineAsyncComponent(() => import('./Bar/Bar.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Bar/BarOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Bar,
	},
	Row: {
		type: 'Row',
		icon: BarChartHorizontal,
		component: defineAsyncComponent(() => import('./Row/Row.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Row/RowOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Row,
	},
	Pie: {
		type: 'Pie',
		icon: PieChart,
		component: defineAsyncComponent(() => import('./Pie/Pie.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Pie/PieOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Pie,
	},
	Funnel: {
		type: 'Funnel',
		icon: ListFilter,
		component: defineAsyncComponent(() => import('./Funnel/Funnel.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Funnel/FunnelOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Funnel,
	},
	Table: {
		type: 'Table',
		icon: Table,
		component: defineAsyncComponent(() => import('./Table/Table.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Table/TableOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Table,
	},
	Progress: {
		type: 'Progress',
		icon: BatteryMedium,
		component: defineAsyncComponent(() => import('./Progress/Progress.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Progress/ProgressOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Progress,
	},
	'Mixed Axis': {
		type: 'Mixed Axis',
		icon: ComboChartIcon,
		component: defineAsyncComponent(() => import('./MixedAxis/MixedAxis.vue')),
		optionsComponent: defineAsyncComponent(() => import('./MixedAxis/MixedAxisOptions.vue')),
		options: {},
		...defaultWidgetDimensions['Mixed Axis'],
	},
	Filter: {
		type: 'Filter',
		icon: TextCursorInput,
		component: defineAsyncComponent(() => import('./Filter/Filter.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Filter/FilterOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Filter,
	},
	Text: {
		type: 'Text',
		icon: AlignLeft,
		component: defineAsyncComponent(() => import('./Text/Text.vue')),
		optionsComponent: defineAsyncComponent(() => import('./Text/TextOptions.vue')),
		options: {},
		...defaultWidgetDimensions.Text,
	},
	'Pivot Table': {
		type: 'Pivot Table',
		icon: GitBranch,
		component: defineAsyncComponent(() => import('./PivotTable/PivotTable.vue')),
		optionsComponent: defineAsyncComponent(() => import('./PivotTable/PivotTableOptions.vue')),
		options: {},
		...defaultWidgetDimensions['Pivot Table'],
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

export type WidgetType = keyof typeof WIDGETS
export type ChartType = typeof VALID_CHARTS[number]

function get(itemType: WidgetType) {
	return WIDGETS[itemType] || UnknownWidget
}

function getComponent(itemType: WidgetType) {
	return get(itemType).component
}

function getOptionComponent(itemType: WidgetType) {
	return get(itemType).optionsComponent
}

function getChartOptions() {
	return VALID_CHARTS.map((chart) => ({
		value: chart,
		label: chart,
	}))
}

export function getIcon(itemType: WidgetType) {
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
