<template>
	<div class="m-4 flex flex-1 flex-shrink-0 flex-col">
		<div v-if="!pickingFilter" class="mb-4 flex items-center justify-between">
			<div class="text-lg font-medium">Filters</div>
			<Button icon="plus" @click="pickingFilter = true"></Button>
		</div>
		<div
			v-if="!pickingFilter && (!filters.conditions || filters.conditions.length == 0)"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No filters added</p>
		</div>
		<div
			v-if="!pickingFilter && filters.conditions?.length > 0"
			class="flex h-full items-start overflow-scroll"
		>
			<LogicalExpression
				:expression="filters"
				@add-filter="showFilterPicker"
				@edit-filter="showFilterPicker"
				@remove-filter="removeFilter"
				@toggle-operator="toggleOperator"
			/>
		</div>
		<FilterPicker
			v-if="pickingFilter"
			@close="pickingFilter = false"
			@filter-select="onFilterSelect"
			:filter="editFilter"
		/>
	</div>
</template>

<script setup>
import LogicalExpression from '@/components/Query/Filter/LogicalExpression.vue'
import FilterPicker from '@/components/Query/Filter/FilterPicker.vue'

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
	pickingFilter.value = false
}

function removeFilter({ level, position, idx }) {
	query.filters.remove(level, position, idx)
}

function toggleOperator({ level, position }) {
	query.filters.toggleOperator(level, position)
}
</script>
