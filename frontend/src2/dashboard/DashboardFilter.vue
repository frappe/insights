<script setup lang="ts">
import { computed, inject, reactive, watchEffect, watch } from 'vue'
import { copy, wheneverChanges } from '../helpers'
import { FilterOperator } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardFilterEditor from './DashboardFilterEditor.vue'
import FilterControl from './FilterControl.vue'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
watchEffect(() => Object.assign(filter, props.item))
if (!filter.links) {
	filter.links = {}
}

const sourceColumn = computed(() => {
	const firstChart = Object.keys(filter.links)[0]
	if (!firstChart) return
	const linkedColumn = filter.links[firstChart]
	return dashboard.getColumnFromFilterLink(linkedColumn)
})

function stringValuesProvider(search: string) {
	if (!sourceColumn.value) return Promise.resolve([])

	const firstLinkedChart = Object.keys(filter.links)?.[0]
	const adhocFilters = firstLinkedChart
		? dashboard.getAdhocFilters(firstLinkedChart, filter.filter_name)
		: undefined

	return dashboard.getDistinctColumnValues(
		sourceColumn.value.query,
		sourceColumn.value.column,
		search,
		adhocFilters,
	)
}

const filterState = reactive(copy(dashboard.filterStates[filter.filter_name] || {}))

// no `immediate` — on mount, filterState must keep the restored state from dashboard.filterStates
watch(
	() => [filter.default_operator, filter.default_value],
	([op, val]) => {
		if (op != null && val != null) {
			filterState.operator = op as FilterOperator
			filterState.value = val
		}
	},
	{ deep: true },
)

wheneverChanges(
	() => filterState,
	() => {
		dashboard.updateFilterState(filter.filter_name, filterState.operator, filterState.value)
	},
	{ deep: true },
)
</script>

<template>
	<FilterControl
		class="w-full"
		:filter-name="filter.filter_name"
		:filter-type="filter.filter_type"
		:icon="filter.icon"
		:values-provider="stringValuesProvider"
		v-model:operator="filterState.operator"
		v-model:value="filterState.value"
	/>

	<DashboardFilterEditor v-if="dashboard.isEditingItem(props.item)" :item="props.item" />
</template>
