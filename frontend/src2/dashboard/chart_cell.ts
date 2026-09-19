// One chart cell's state, whichever card draws it. The builder draws the card it
// can change and every view surface draws the read-only one, but what a cell
// reads and what its reader may narrow it by are the same, so both cards are
// drawn from this.
//
// It lives apart from both cards because of what they import: the builder's
// card carries the authoring drill, which an island may not.

import { computed, provide, ref, shallowRef, watch } from 'vue'
import { numberReadings } from '../charts/adapter/number'
import { tableFindKey } from '../charts/adapter/table'
import type { ChartView } from '../charts/chart_view'
import type { Filter } from '../components/filter_picker/filter_picker'
import type { NumberChartConfig } from '../types/chart.types'
import type { QueryResultColumn } from '../types/query.types'
import type { DashboardView, DashboardViewItem } from './view'

export type ChartCellProps = { item: DashboardViewItem; dashboard: DashboardView }

export function useChartCell(props: ChartCellProps) {
	// The read registers itself when it is made, so it cannot be resolved in a
	// computed, which Vue is free to evaluate, discard or run again. It is
	// resolved once per chart the cell names, and held.
	const read = shallowRef<ChartView | undefined>()
	watch(
		() => props.item.chart,
		(chart_name) => {
			read.value = chart_name ? props.dashboard.chartView(chart_name) : undefined
			if (chart_name) props.dashboard.loadChart(chart_name)
		},
		{ immediate: true },
	)

	// A cell always names the reading it draws. One written before a cell could
	// name one draws the first, and says so here rather than leaving the chart to
	// guess which surface it is on.
	const reading = computed(
		() => props.item.reading ?? numberReadings(read.value?.doc.config as NumberChartConfig)[0],
	)

	// A cell can be pointed at a chart after it was dropped, so the provide cannot
	// sit behind a one-shot check of the name.
	provide(
		'chartName',
		computed(() => props.item.chart),
	)

	// A table card carries its own filter: the reader picks a column of the rows
	// it drew and the page sends it with the card's request. Only a table,
	// because only a table shows the rows a rule is read against.
	const isTable = computed(() => read.value?.doc.chart_type === 'Table')

	// The rule is written against the columns the card drew, because that is
	// where it lands: after the chart's summarize, on the columns the card draws.
	// A dimension is offered under the label the chart prints, and a measure is a
	// column there too — "count over 5" reads the total on screen.
	const columns = computed<QueryResultColumn[]>(() => {
		if (!isTable.value) return []
		return read.value?.result.columns || []
	})

	// What "Reset filters" takes back: the grid's own filters that reach this
	// card, and the one the reader put on the card itself. Offered only when
	// there is something to take back, so an empty card that nobody filtered says
	// only that it is empty.
	const filtered = computed(() =>
		Boolean(props.item.chart && props.dashboard.filtered(props.item.chart)),
	)
	function resetFilters() {
		if (props.item.chart) props.dashboard.resetCardFilters(props.item.chart)
	}

	const cardFilters = computed<Filter[]>({
		get: () => (props.item.chart && props.dashboard.cardFilters[props.item.chart]) || [],
		set: (filters) => {
			if (props.item.chart) props.dashboard.setCardFilters(props.item.chart, filters)
		},
	})

	// The page answers for a card filter's values, the same page that answers for
	// a saved filter's. The chart's config says which drawn column is a dimension
	// and what column it reads; a measure names none, and the number operators
	// ask for no value.
	function valuesProvider(column: QueryResultColumn) {
		return (search: string) => {
			const chart_name = props.item.chart
			if (!chart_name) return Promise.resolve([])
			return props.dashboard.cardValues(chart_name, column.name, search)
		}
	}

	function rangeProvider(column: QueryResultColumn) {
		const chart_name = props.item.chart
		if (!chart_name) return Promise.resolve(undefined)
		return props.dashboard.cardRange(chart_name, column.name)
	}

	// Find is the other half of the table card's title row, and the half that
	// never leaves the browser: a case-insensitive match over the rows the card
	// already drew. It is not a filter, so it is held here and not on the page —
	// nothing outside this card reads it, and a reload should not bring it back.
	// `TableChart` takes it through the key and narrows the rows it hands the grid.
	const findText = ref('')
	const findOpen = ref(false)
	provide(tableFindKey, findText)

	return {
		read,
		reading,
		isTable,
		columns,
		filtered,
		resetFilters,
		cardFilters,
		valuesProvider,
		rangeProvider,
		findText,
		findOpen,
	}
}
