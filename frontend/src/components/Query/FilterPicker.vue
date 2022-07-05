<template>
	<div class="m-4 flex flex-1 flex-col">
		<div v-if="!addingFilter" class="mb-4 flex items-center justify-between">
			<div class="text-lg font-medium">Filters</div>
			<Button icon="plus" @click="addingFilter = true"></Button>
		</div>
		<div v-if="addingFilter">
			<div class="mb-4 flex h-7 items-center">
				<Button icon="chevron-left" class="mr-2" @click="resetNewFilter"> </Button>
				<div class="text-lg font-medium">{{ editingFilter ? 'Edit' : 'Add' }} a Filter</div>
			</div>
			<div class="flex flex-col space-y-3">
				<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md font-light"
						:class="{ 'border bg-white font-normal shadow-sm': newFilterType == 'simple' }"
						@click.prevent.stop="newFilterType = 'simple'"
					>
						Simple
					</div>
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md"
						:class="{ 'border bg-white font-normal shadow-sm': newFilterType == 'expression' }"
						@click.prevent.stop="newFilterType = 'expression'"
					>
						Expression
					</div>
				</div>
				<SimpleFilterPicker
					v-if="newFilterType == 'simple'"
					@filter-select="filterSelected"
					:filter="getFilterAt(editFilterAt)"
				/>
				<ExpressionFilterPicker
					v-if="newFilterType == 'expression'"
					@filter-select="filterSelected"
					:filter="getFilterAt(editFilterAt)"
				/>
			</div>
		</div>
		<div v-if="!addingFilter" class="flex flex-1 flex-col">
			<div
				v-if="query_filters.conditions.length == 0"
				class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
			>
				<p>No filters added</p>
			</div>
			<div
				v-else-if="query_filters.conditions.length > 0"
				class="flex h-full items-start overflow-scroll"
			>
				<FilterTree
					:filters="query_filters"
					@remove-filter="removeFilter"
					@branch-filter-at="branchFilterAt"
					@toggle-group-operator="toggleGroupOperator"
					@edit-filter="
						({ level, position, idx, is_expression }) => {
							addingFilter = true
							editingFilter = true
							newFilterType = is_expression ? 'expression' : 'simple'
							Object.assign(editFilterAt, { level, position, idx, is_expression })
						}
					"
					@add-filter="
						({ level, position }) => {
							addingFilter = true
							Object.assign(addNextFilterAt, { level, position })
						}
					"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import FilterTree from '@/components/Query/FilterTree.vue'
import SimpleFilterPicker from '@/components/Query/SimpleFilterPicker.vue'
import ExpressionFilterPicker from '@/components/Query/ExpressionFilterPicker.vue'

import { computed, inject, reactive, ref } from 'vue'

const query = inject('query')
const query_filters = reactive(query.filters)

const newFilterType = ref('simple')
const addingFilter = ref(false)
const editingFilter = ref(false)
const editFilterAt = reactive({})
const addNextFilterAt = reactive({ level: 1, position: 1 })

const tables = computed(() =>
	query.tables.map((t) => ({
		label: row.label,
		table: row.table,
	}))
)

function toggleGroupOperator({ level, position }) {
	const filters = get_filter_group_at({ level, position })
	filters.group_operator = filters.group_operator == '&' ? 'or' : '&'
	query.updateFilters({ filters: query_filters })
}
function filterSelected({ filter }) {
	if (editFilterAt.level && editFilterAt.position && typeof editFilterAt.idx == 'number') {
		const { level, position, idx } = editFilterAt
		edit_filter({ filter, level, position, idx })
	} else if (addNextFilterAt.level && addNextFilterAt.position) {
		const { level, position } = addNextFilterAt
		add_filter({ filter, level, position })
	}
}
function add_filter({ filter, level, position }) {
	const filter_group = get_filter_group_at({ level, position })
	filter_group.conditions.push(filter)
	resetNewFilter()
	query.updateFilters({ filters: query_filters })
}
function edit_filter({ filter, level, position, idx }) {
	const filter_group = get_filter_group_at({ level, position })
	const conditions = filter_group.conditions
	conditions[idx] = filter
	resetNewFilter()
	query.updateFilters({ filters: query_filters })
}
function branchFilterAt({ level, position, idx }) {
	const filter_group = get_filter_group_at({ level, position })
	const conditions = filter_group.conditions

	const condition_to_replace = conditions[idx]
	filter_group.conditions[idx] = {
		level: level + 1,
		position: idx + 1,
		group_operator: filter_group.group_operator == '&' ? 'or' : '&',
		conditions: [condition_to_replace],
	}
	query.updateFilters({ filters: query_filters })
}
function removeFilter({ level, position, idx }) {
	if (level == 1 && typeof idx == 'number') {
		// remove the filter from root level
		query_filters.conditions.splice(idx, 1)
	}

	if (level > 1 && position && typeof idx == 'number') {
		// remove the filter at `idx` from the filter group at `level` & `position`
		const filter_group = get_filter_group_at({ level, position })
		filter_group.conditions.splice(idx, 1)
	}

	query.updateFilters({ filters: query_filters })
}
function resetNewFilter() {
	newFilterType.value = 'simple'
	addingFilter.value = false
	editingFilter.value = false
	addNextFilterAt.level = 1
	addNextFilterAt.position = 1
	Object.keys(editFilterAt).forEach((key) => delete editFilterAt[key])
}

function get_filter_group_at({ filters, level, position, parent_index }) {
	if (level == 1 && position == 1) {
		return query_filters
	}

	// find the filter group at the given level and position
	let filter_groups = filters || query_filters
	let filter_group_at_level = null

	for (let i = 0; i < filter_groups.conditions.length; i++) {
		let filter_group = filter_groups.conditions[i]
		if (filter_group.level == level && (filter_group.position == position || i == parent_index)) {
			filter_group_at_level = filter_group
			break
		}

		if (filter_group.conditions?.length) {
			let filter_group_at_level_in_group = get_filter_group_at({
				filters: filter_group,
				level,
				position,
			})
			if (filter_group_at_level_in_group) {
				filter_group_at_level = filter_group_at_level_in_group
				break
			}
		}
	}

	return filter_group_at_level
}
function get_parent_filter_group_of({ level, position }) {
	const parent_level = level - 1
	const filter_group_index = position - 1

	return get_filter_group_at({
		filters: query_filters,
		level: parent_level,
		parent_index: filter_group_index,
	})
}
function getFilterAt({ level, position, idx }) {
	if (!level || !position || typeof idx !== 'number') {
		return { left: {}, operator: {}, right: {} }
	}

	let filter_group = get_filter_group_at({ level, position })
	if (filter_group.conditions.length > idx) {
		return filter_group.conditions[idx]
	}

	return {}
}
</script>
