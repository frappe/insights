<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { AlertTriangle, Pencil } from 'lucide-vue-next'
import { computed, inject, provide, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import { numberReadings } from '../charts/adapter/number'
import { tableFindKey } from '../charts/adapter/table'
import useChart from '../charts/chart'
import type { ChartRead } from '../charts/chart_read'
import ChartChrome from '../charts/components/ChartChrome.vue'
import ChartRenderer from '../charts/components/ChartRenderer.vue'
import type { Filter } from '../components/filter_picker/filter_picker'
import { waitUntil, wheneverChanges } from '../helpers'
import { __ } from '../translation'
import { NumberChartConfig } from '../types/chart.types'
import type { QueryResultColumn } from '../types/query.types'
import { WorkbookDashboardChart } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import TableCardActions from './TableCardActions.vue'

const props = defineProps<{ item: WorkbookDashboardChart }>()
const dashboard = inject<Dashboard>('dashboard')!

// Both stores register themselves when they are made (a watcher, a history, an
// entry in the chart and read maps), so neither can be resolved in a computed,
// which Vue is free to evaluate, discard or run again. They are resolved once
// per chart the cell names, and held.
const chart = shallowRef<ReturnType<typeof useChart> | null>(null)
// the card, drawn from the config being edited rather than from the saved
// chart, so an unsaved edit shows here too. A public link reads the saved chart.
const read = shallowRef<ChartRead | null>(null)

// `watch` and not `watchEffect`: making a store reads reactive state of its own,
// and an effect tracking that would remake it whenever any of it moved
watch(
	() => props.item.chart,
	(chart_name) => {
		chart.value = chart_name ? useChart(chart_name) : null
		read.value = chart_name ? dashboard.chartRead(chart_name) : null
	},
	{ immediate: true },
)

// A cell always names the reading it draws. One written before a cell could
// name one draws the first, and says so here rather than leaving the chart to
// guess which surface it is on.
const reading = computed(
	() => props.item.reading ?? numberReadings(read.value?.doc.config as NumberChartConfig)[0],
)

// a cell can be pointed at a chart after it was dropped, so neither the provide
// nor the watcher below can sit behind a one-shot check of the name
provide(
	'chartName',
	computed(() => props.item.chart),
)

wheneverChanges(
	() => props.item.chart,
	(chart_name: string) => {
		if (!chart_name) return
		waitUntil(() => Boolean(chart.value?.isloaded)).then(() => {
			// A read this cell is the first to draw, or one the chart went stale
			// under while nothing was drawing it. `invalidateChart` marks rather
			// than runs, so the mark is collected here — by the card that has
			// somewhere to put the rows.
			if (!read.value?.ready || read.value.stale) {
				dashboard.refreshChart(chart_name)
			}
		})
	},
	{ immediate: true },
)

wheneverChanges(
	() => chart.value?.doc.config.order_by,
	() => props.item.chart && dashboard.refreshChart(props.item.chart),
	{ deep: true, debounce: 500 },
)

// A table card carries its own filter: the reader picks a column of the rows it
// drew and the store routes it as a filter item linked to this chart alone. Only
// a table, because only a table shows the rows a rule is read against.
const isTable = computed(() => read.value?.doc.chart_type === 'Table')

// The rule is written against the columns the card drew, because that is where
// the routed filter lands: the card filter links by the chart's name, so the
// group is appended to the chart's derived query, after its summarize. A
// dimension is offered under the label the chart prints, and a measure is a
// column there too — "count over 5" reads the total on screen.
const columns = computed<QueryResultColumn[]>(() => {
	if (!isTable.value) return []
	return read.value?.result.columns || []
})

// What "Reset filters" takes back: the grid's own filters that reach this card,
// and the one the reader put on the card itself. Offered only when there is
// something to take back, so an empty card that nobody filtered says only that
// it is empty.
const filtered = computed(() =>
	Boolean(props.item.chart && dashboard.cardIsFiltered(props.item.chart)),
)
function resetFilters() {
	if (props.item.chart) dashboard.resetCardFilters(props.item.chart)
}

function rangeProvider(column: QueryResultColumn) {
	const chart_name = props.item.chart
	if (!chart_name) return Promise.resolve(undefined)
	return dashboard.getCardColumnRange(chart_name, column.name)
}

const cardFilters = computed<Filter[]>({
	get: () => (props.item.chart && dashboard.cardFilters[props.item.chart]) || [],
	set: (filters) => {
		if (props.item.chart) dashboard.setCardFilters(props.item.chart, filters)
	},
})

// The dashboard answers for a card filter's values, the same surface that
// answers for a saved filter's. Reaching the query's own method would ask a
// document a public reader holds no permission on, and the failure is silent.
// The chart's config says which drawn column is a dimension and what column it
// reads; a measure names none, and the number operators ask for no value.
function valuesProvider(column: QueryResultColumn) {
	return (search: string) => {
		const chart_name = props.item.chart
		if (!chart_name) return Promise.resolve([])
		return dashboard.getCardColumnValues(chart_name, column.name, search)
	}
}

// Find is the other half of the table card's title row, and the half that never
// leaves the browser: a case-insensitive match over the rows the card already
// drew. It is not a filter, so it is held here and not in the dashboard store —
// nothing outside this card reads it, and a reload should not bring it back.
// `TableChart` takes it through the key and narrows the rows it hands the grid.
const findText = ref('')
const findOpen = ref(false)
const actionsActive = ref(false)
provide(tableFindKey, findText)

// Editing a chart is not editing the dashboard. The chart is a workbook object
// and the dashboard only names it, so the action sits on the card in view mode
// and never touches the layout state.
const router = useRouter()
const canEditChart = computed(() => Boolean(props.item.chart) && dashboard.doc.has_workbook_access)
function editChart() {
	router.push(`/workbook/${dashboard.doc.workbook}/chart/${props.item.chart}`)
}
</script>

<template>
	<!-- a public link draws the card read-only: sorting is a query, and a drill
	     needs an authoring seat, so neither is offered there -->
	<ChartChrome
		v-if="read && dashboard.shared"
		:chart="read"
		:reading="reading"
		readonly
		:filtered="filtered"
		@reset-filters="resetFilters"
	>
		<template v-if="isTable" #actions>
			<TableCardActions
				v-model:filters="cardFilters"
				v-model:find-text="findText"
				v-model:find-open="findOpen"
				:columns="columns"
				:values-provider="valuesProvider"
				:range-provider="rangeProvider"
			/>
		</template>
	</ChartChrome>
	<ChartRenderer
		v-else-if="read"
		:chart="read"
		:reading="reading"
		:actions-revealed="actionsActive"
		:filtered="filtered"
		@reset-filters="resetFilters"
	>
		<template v-if="isTable" #actions="{ expanded }">
			<TableCardActions
				v-model:filters="cardFilters"
				v-model:find-text="findText"
				v-model:find-open="findOpen"
				v-model:active="actionsActive"
				:columns="columns"
				:values-provider="valuesProvider"
				:range-provider="rangeProvider"
				:reveal="!dashboard.shared && !expanded"
			/>
		</template>
		<template v-if="canEditChart" #hoverActions>
			<Tooltip :text="__('Edit Chart')">
				<Button variant="ghost" @click="editChart()">
					<Pencil class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</Button>
			</Tooltip>
		</template>
	</ChartRenderer>

	<!-- not one of the card's states: a grid item that names no chart has no store
	     to be loading, failed or empty. It is the layout that is wrong, not a read. -->
	<div
		v-else
		class="flex h-full flex-1 flex-col items-center justify-center rounded-4 border border-outline-gray-2"
	>
		<div class="flex items-center gap-1.5 text-p-base text-ink-gray-4">
			<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
			<span>{{ __('Chart not found') }}</span>
		</div>
	</div>
</template>
