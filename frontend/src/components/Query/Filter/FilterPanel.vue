<template>
	<div class="flex h-full w-1/3 flex-col overflow-scroll pl-4 pb-4">
		<div
			v-if="!pickingFilter"
			class="sticky top-0 flex items-center justify-between bg-white pb-3 pt-1"
		>
			<div class="text-sm tracking-wide text-gray-600">FILTERS</div>
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
			class="flex h-full items-start overflow-hidden"
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
