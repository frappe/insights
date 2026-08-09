<script setup lang="ts">
import { reactive, watch } from 'vue'
import ViewerChart from '../charts/ViewerChart.vue'
import { isFilterApplied } from '../query/components/filter_utils'
import type { FilterOperator, FilterValue } from '../types/query.types'
import FilterControl from './FilterControl.vue'
import { fetchFilterValues, type DashboardCellProps, type ViewerFilterState } from './viewer'

// One cell of a dashboard grid, as a reader gets it. A chart card owns its own
// request and its own states, so a cell that cannot load leaves the page alone.
//
// A filter is a cell like any other, in the position its author gave it. The one
// thing it cannot do here is name its own column — the link that says so never
// reaches a reader — so it asks for its values by filter name and lets the
// server route what it lands on.
const props = defineProps<DashboardCellProps>()

const emit = defineEmits<{
	loaded: [executedAt: Date]
	resetFilters: []
	filter: [state?: ViewerFilterState]
}>()

const filterName = props.item.filter_name as string

// what the control edits. It reports an operator and a value as two changes, so
// collecting them here means one settled state per move, and one refetch of the
// cards this filter reaches.
const draft = reactive<{ operator?: FilterOperator; value?: FilterValue }>({
	...props.filters?.[filterName],
})

// the page owns the state, so a reset anywhere on it lands back in this control
watch(
	() => props.filters?.[filterName],
	(state) => {
		draft.operator = state?.operator
		draft.value = state?.value
	},
)

watch(draft, () => {
	const applied = isFilterApplied(props.item.filter_type!, draft.operator, draft.value)
	emit('filter', applied ? { operator: draft.operator!, value: draft.value! } : undefined)
})
</script>

<template>
	<div class="flex h-full w-full items-center justify-start p-2">
		<ViewerChart
			v-if="props.item.type === 'chart'"
			:chart="props.item.chart!"
			:dashboard="props.dashboard"
			:filters="props.filters"
			:priority="props.priority"
			:refresh-token="props.refreshToken"
			@loaded="$emit('loaded', $event)"
			@reset-filters="$emit('resetFilters')"
		/>
		<div
			v-else-if="props.item.type === 'text'"
			class="prose prose-v3 h-full w-full max-w-none overflow-auto text-ink-gray-7"
			v-html="props.item.text"
		/>
		<FilterControl
			v-else-if="props.item.type === 'filter'"
			class="w-full"
			:filter-name="filterName"
			:filter-type="props.item.filter_type!"
			:icon="props.item.icon"
			:values-provider="
				(search: string) => fetchFilterValues(props.dashboard, filterName, search)
			"
			v-model:operator="draft.operator"
			v-model:value="draft.value"
		/>
	</div>
</template>
