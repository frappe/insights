<template>
	<div class="flex flex-1 flex-col p-4">
		<FilterPickerSearch
			class="mb-4"
			ref="filter_search"
			@filter_selected="add_filter"
			:query="query"
			:tables="tables"
		/>
		<div
			v-if="filters.conditions && filters.conditions.length"
			class="mx-2 flex flex-1 select-none flex-col"
		>
			<FilterNode
				:filters="filters"
				@toggle_group_operator="toggle_group_operator"
				@add_filter="trigger_add_filter"
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
import FilterPickerSearch from './FilterPickerSearch.vue'
import FilterNode from './FilterNode.vue'

export default {
	name: 'FilterPicker',
	props: ['tables', 'filters', 'query'],
	components: {
		FilterPickerSearch,
		FilterNode,
	},
	methods: {
		get_filter_group_at(level) {
			// find the filter group at the given level
			let filter_group = this.filters
			let _level = 1

			while (_level < level) {
				const _filter_group = filter_group.conditions.find(
					(f) => f.level == _level + 1
				)
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
			if (level == 1) {
				this.filters.group_operator =
					this.filters.group_operator == 'All' ? 'Any' : 'All'
				this.$emit('update:filters', this.filters)
				return
			}

			const filters = this.get_filter_group_at(level)
			filters.group_operator = filters.group_operator == 'All' ? 'Any' : 'All'
			this.$emit('update:filters', this.filters)
		},
		add_filter(filter) {
			if (!this.add_filter_meta) {
				// no meta to add at given position, so just add the filter to root level
				this.filters.conditions.push(filter)
				this.$emit('update:filters', this.filters)
				return
			}

			// replace existing condition at given level & index with a filter group
			const { idx, level, chain_operator } = this.add_filter_meta
			const filter_group = this.get_filter_group_at(level)
			const conditions = filter_group.conditions
			const condition_to_replace = conditions[idx]
			if (
				(chain_operator == 'and' && filter_group.group_operator == 'Any') ||
				(chain_operator == 'or' && filter_group.group_operator == 'All')
			) {
				// replace the element at idx with the new group filter
				conditions[idx] = {
					level: level + 1,
					group_operator: chain_operator == 'or' ? 'Any' : 'All',
					conditions: [condition_to_replace, filter],
				}
			} else {
				// add a filter
				conditions[idx + 1] = filter
			}
			this.$emit('update:filters', this.filters)
			this.add_filter_meta = null
		},
		trigger_add_filter({ level, idx, chain_operator }) {
			this.add_filter_meta = { level, idx, chain_operator }
			this.focus_filter_search()
		},
		focus_filter_search() {
			this.$refs.filter_search.focused = true
		},
		remove_filter({ level, idx }) {
			if (level == 1) {
				// remove the filter from root level
				this.filters.conditions.splice(idx, 1)
			} else {
				// remove the filter at `idx` from the filter group at `level`
				const filter_group = this.get_filter_group_at(level)
				filter_group.conditions.splice(idx, 1)
				if (filter_group.conditions.length == 0) {
					// remove the filter group
					this.filters.conditions.splice(level - 1, 1)
				}
			}

			this.$emit('update:filters', this.filters)
		},
	},
}
</script>
