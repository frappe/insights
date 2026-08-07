<script setup lang="ts">
import { inject, reactive, watchEffect, watch } from 'vue'
import { copy, wheneverChanges } from '../helpers'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardFilterEditor from './DashboardFilterEditor.vue'
import FilterControl from './FilterControl.vue'
import { defaultFilterState } from './viewer'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
watchEffect(() => Object.assign(filter, props.item))
if (!filter.links) {
	filter.links = {}
}

// The filter names itself. Which column it reads is the server's to look up —
// the link that says so is the one thing a reader is never handed, so there is
// one lookup rather than one per surface.
function stringValuesProvider(search: string) {
	const firstLinkedChart = Object.keys(filter.links)?.[0]
	if (!firstLinkedChart) return Promise.resolve([])
	return dashboard.getDistinctColumnValues(filter.filter_name, search, firstLinkedChart)
}

const filterState = reactive(copy(dashboard.filterStates[filter.filter_name] || {}))

// no `immediate` — on mount, filterState must keep the restored state from dashboard.filterStates
watch(
	() => [filter.default_operator, filter.default_value],
	() => {
		const state = defaultFilterState(filter)
		if (!state) return
		filterState.operator = state.operator
		filterState.value = state.value
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
