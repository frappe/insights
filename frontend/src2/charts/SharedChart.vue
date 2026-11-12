<script setup lang="ts">
import { call } from 'frappe-ui'
import { provide, ref } from 'vue'
import type { Filter, ValuesProvider } from '../components/filter_picker/filter_picker'
import TableCardActions from '../dashboard/TableCardActions.vue'
import type { QueryResultColumn } from '../types/query.types'
import { tableFindKey } from './adapter/table'
import { useChartView } from './chart_view'
import ChartView from './ChartView.vue'

const props = defineProps<{ chart_name: string }>()

// a link opens the chart without a dashboard, so the reader's card filter is kept here
const cardFilters = ref<Filter[]>([])
const chart = useChartView(props.chart_name, {
	id: 'shared',
	filterContext: (chart_name) => ({
		chart: chart_name,
		cardFilters: cardFilters.value.map(({ column, operator, value }) => ({
			column: column.name,
			operator,
			value,
		})),
	}),
})
chart.load()

function setCardFilters(filters: Filter[]) {
	cardFilters.value = filters
	chart.load()
}

const cardColumn = (column: QueryResultColumn) => ({ chart: props.chart_name, column: column.name })
const valuesProvider: ValuesProvider = (column) => (search_term, granularity) =>
	call('insights.api.view.get_card_values', { ...cardColumn(column), search_term, granularity })
const rangeProvider = (column: QueryResultColumn) =>
	call<[number, number] | undefined>('insights.api.view.get_card_range', cardColumn(column))

const findText = ref('')
provide(tableFindKey, findText)
// Expand mounts a second TableCardActions, so the page holds what the reader opened
const findOpen = ref(false)
const actionsActive = ref(false)
</script>

<template>
	<div class="h-full w-full">
		<ChartView
			:chart="chart"
			:filtered="cardFilters.length > 0"
			:actions-revealed="actionsActive"
			@reset-filters="setCardFilters([])"
		>
			<template v-if="chart.doc.chart_type === 'Table'" #actions>
				<TableCardActions
					:filters="cardFilters"
					v-model:find-text="findText"
					v-model:find-open="findOpen"
					v-model:active="actionsActive"
					:filterable="chart.canFilter !== false"
					:columns="chart.result.columns || []"
					:values-provider="valuesProvider"
					:range-provider="rangeProvider"
					@update:filters="setCardFilters"
				/>
			</template>
		</ChartView>
	</div>
</template>
