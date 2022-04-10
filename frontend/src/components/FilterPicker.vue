<template>
	<div class="flex flex-1 flex-col p-4">
		<div
			v-if="filters.conditions && filters.conditions.length"
			class="mx-2 flex flex-1 select-none flex-col overflow-scroll scrollbar-hide"
		>
			<FilterNode
				:filters="filters"
				:query="query"
				:tables="tables"
				@toggle_group_operator="toggle_group_operator"
				@filter_selected="add_filter"
				@branch_condition_at="branch_condition_at"
				@remove_filter="remove_filter"
			/>
		</div>
		<div
			v-else
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			No filters added
		</div>
	</div>
</template>

<script>
import FilterNode from './FilterNode.vue'

export default {
	name: 'FilterPicker',
	props: ['tables', 'filters', 'query'],
	components: {
		FilterNode,
	},
	methods: {
		get_filter_group_at(level) {
			// find the filter group at the given level
			let filter_group = this.filters
			let _level = 1

			while (_level < level) {
				const _filter_group = filter_group.conditions.find((f) => f.level == _level + 1)
				if (_filter_group) {
					filter_group = _filter_group
					_level += 1
				} else {
					// no filter at this level, so no point in continuing
					return {}
				}
			}

			return filter_group
		},
		toggle_group_operator({ level }) {
			const filters = this.get_filter_group_at(level)
			filters.group_operator = filters.group_operator == 'All' ? 'Any' : 'All'
			this.$emit('update:filters', this.filters)
		},
		add_filter({ filter, level }) {
			const filter_group = this.get_filter_group_at(level)
			const conditions = filter_group.conditions
			conditions.push(filter)
			this.$emit('update:filters', this.filters)
		},
		branch_condition_at({ level, idx }) {
			const filter_group = this.get_filter_group_at(level)
			const conditions = filter_group.conditions

			const condition_to_replace = conditions[idx]
			filter_group.conditions[idx] = {
				level: level + 1,
				group_operator: filter_group.group_operator == 'All' ? 'Any' : 'All',
				conditions: [condition_to_replace],
			}
			this.$emit('update:filters', this.filters)
		},
		remove_filter({ level, idx }) {
			if (level == 1) {
				if (idx) {
					// remove the filter from root level
					this.filters.conditions.splice(idx, 1)
				} else {
					this.filters.conditions = []
				}
			} else {
				if (idx) {
					// remove the filter at `idx` from the filter group at `level`
					const filter_group = this.get_filter_group_at(level)
					filter_group.conditions.splice(idx, 1)
					if (filter_group.conditions.length == 0) {
						// remove the filter group if no conditions remain
						const parent_filter_group = this.get_filter_group_at(level - 1)
						parent_filter_group.conditions = parent_filter_group.conditions.filter((f) => f.level != level)
					}
				} else {
					// remove the whole filter group at `level`
					const parent_filter_group = this.get_filter_group_at(level - 1)
					parent_filter_group.conditions = parent_filter_group.conditions.filter((f) => f.level != level)
				}
			}

			this.$emit('update:filters', this.filters)
		},
	},
}
</script>
