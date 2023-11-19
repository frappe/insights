<template>
	<div class="flex flex-1 flex-shrink-0 flex-col overflow-hidden">
		<div
			v-if="!pickingFilter"
			class="flex w-full flex-shrink-0 items-center justify-between bg-white pb-2"
		>
			<div class="text-sm tracking-wide text-gray-700">FILTERS</div>
			<Button icon="plus" @click="pickingFilter = true"></Button>
		</div>
		<div
			v-if="!pickingFilter && (!filters.conditions || filters.conditions.length == 0)"
			class="flex h-full w-full items-center justify-center rounded border-2 border-dashed border-gray-200 text-sm text-gray-600"
		>
			<p>No filters added</p>
		</div>
		<div
			v-else-if="!pickingFilter && filters.conditions?.length > 0"
			class="h-full w-full overflow-scroll"
		>
			<LogicalExpression
				:key="JSON.stringify(filters)"
				:expression="filters"
				@add-filter="showFilterPicker"
				@edit-filter="showFilterPicker"
				@remove-filter="removeFilter"
				@toggle-operator="toggleOperator"
			/>
		</div>
		<FilterPicker
			v-else-if="pickingFilter"
			@close="pickingFilter = false"
			@filter-select="onFilterSelect"
			:filter="editFilter"
		/>
	</div>
</template>

<script setup>
import LogicalExpression from './LogicalExpression.vue'
import FilterPicker from './FilterPicker.vue'

import { ref, inject, computed } from 'vue'

const pickingFilter = ref(false)
const query = inject('query')
const filters = computed(() => query.filters.data || {})

const editFilter = ref(null)
const showFilterPicker = ({ condition, level, position, idx }) => {
	pickingFilter.value = true
	if (condition) {
		editFilter.value = condition
		query.filters.editFilterAt.level = level
		query.filters.editFilterAt.position = position
		query.filters.editFilterAt.idx = idx
	} else {
		editFilter.value = null
		query.filters.addNextFilterAt.level = level
		query.filters.addNextFilterAt.position = position
	}
}

function onFilterSelect(filter) {
	if (editFilter.value) {
		query.filters.edit(filter)
	} else {
		query.filters.add(filter)
	}
	editFilter.value = null
	pickingFilter.value = false
}

function removeFilter({ level, position, idx }) {
	query.filters.remove(level, position, idx)
}

function toggleOperator({ level, position }) {
	query.filters.toggleOperator(level, position)
}
</script>
