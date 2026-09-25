// The state of one chart cell, for both chart cards. The builder renders a card
// the owner can change, and every view page renders a read-only one. Both read
// the same rows and show the same filters, so both use this.
//
// It is separate from both cards because of their imports. The builder's card
// imports the builder's drill, which an island must not load.

import { computed, provide, ref, shallowRef, watch } from 'vue'
import { numberReadings } from '../charts/adapter/number'
import { tableFindKey } from '../charts/adapter/table'
import type { ChartRead } from '../charts/chart_view'
import type { Filter } from '../components/filter_picker/filter_picker'
import type { NumberChartConfig } from '../types/chart.types'
import type { QueryResultColumn } from '../types/query.types'
import type { DashboardView, DashboardViewItem } from './view'

export type ChartCellProps = { item: DashboardViewItem; dashboard: DashboardView }

export function useChartCell(props: ChartCellProps) {
	// Getting a read registers it, so a computed cannot get it. Vue may evaluate,
	// discard or rerun a computed. So the read is got once per chart name and
	// kept.
	const read = shallowRef<ChartRead | undefined>()
	watch(
		() => props.item.chart,
		(chart_name) => {
			read.value = chart_name ? props.dashboard.chartView(chart_name) : undefined
			if (chart_name) props.dashboard.loadChart(chart_name)
		},
		{ immediate: true },
	)

	// A cell stores the reading it shows. A cell saved before cells stored one
	// shows the first reading. That is decided here, so the chart does not have
	// to guess which page it is on.
	const reading = computed(
		() => props.item.reading ?? numberReadings(read.value?.doc.config as NumberChartConfig)[0],
	)

	// Only a table card has a card filter, because only a table shows the rows
	// the filter applies to. The reader picks a column of those rows, and the page
	// sends the filter with the card's request.
	const isTable = computed(() => read.value?.doc.chart_type === 'Table')

	// The filter uses the card's result columns, because the server applies it
	// after the chart's summarize. A dimension shows under the chart's label for
	// it. A measure is a column too, so "count over 5" filters on the total on
	// screen.
	const columns = computed<QueryResultColumn[]>(() => {
		if (!isTable.value) return []
		return read.value?.result.columns || []
	})

	// "Reset filters" clears the dashboard filters that apply to this card and the
	// reader's card filter. It shows only when there is something to clear, so an
	// empty card with no filters says only that it is empty.
	const filtered = computed(() =>
		Boolean(props.item.chart && props.dashboard.filtered(props.item.chart)),
	)
	function resetFilters() {
		if (props.item.chart) props.dashboard.resetCardFilters(props.item.chart)
	}

	const filterable = computed(() => read.value?.canFilter !== false)
	const cardFilters = computed<Filter[]>({
		get: () => (props.item.chart && props.dashboard.cardFilters[props.item.chart]) || [],
		set: (filters) => {
			if (props.item.chart) props.dashboard.setCardFilters(props.item.chart, filters)
		},
	})

	// The page returns a card filter's values, as it does for a dashboard filter.
	// The chart's config maps a dimension to its source column. A measure has no
	// source column, but its number operators need no value list.
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

	// Find runs only in the browser: a case-insensitive match over the rows the
	// card already shows. It is not a filter, so it lives here and not on the page.
	// Nothing outside this card reads it, and a reload should not restore it.
	// `TableChart` reads it through the key and narrows the rows it renders.
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
		filterable,
		cardFilters,
		valuesProvider,
		rangeProvider,
		findText,
		findOpen,
	}
}
