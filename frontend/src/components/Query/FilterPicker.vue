<template>
	<div class="flex flex-1 flex-col px-4 pb-4">
		<div v-if="!adding_filter" class="mb-4 flex items-center justify-between">
			<div class="text-lg font-medium">Conditions</div>
			<Button class="!flex !h-7 !w-7 !items-center !justify-center !p-0 !text-gray-700" @click="adding_filter = true">
				+
			</Button>
		</div>
		<div v-if="adding_filter">
			<div class="mb-4 flex h-7 items-center">
				<FeatherIcon name="chevron-left" class="mr-2 h-4 w-4 cursor-pointer" @click="adding_filter = false" />
				<div class="text-lg font-medium">{{ editing_filter ? 'Edit' : 'Add' }} a Filter</div>
			</div>
			<div class="-mt-2 flex flex-col space-y-2">
				<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
					<div class="flex h-full flex-1 items-center justify-center rounded-md border bg-white shadow-sm">Simple</div>
					<div class="flex h-full flex-1 items-center justify-center rounded-md font-light">Expression</div>
				</div>
				<SimpleFilterPicker :query="query" :filter="get_filter_at(edit_filter_at)" @select="filter_selected" />
			</div>
		</div>
		<div
			v-if="filters.conditions.length == 0 && !adding_filter"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No filters added</p>
		</div>
		<div v-else-if="filters.conditions.length > 0 && !adding_filter" class="-mt-2 flex">
			<FilterTree
				:filters="filters"
				@remove_filter="remove_filter"
				@branch_filter_at="branch_filter_at"
				@toggle_group_operator="toggle_group_operator"
				@edit_filter="
					({ level, idx }) => {
						adding_filter = true
						editing_filter = true
						edit_filter_at = { level, idx }
					}
				"
				@add_filter="
					({ level }) => {
						adding_filter = true
						add_next_filter_at = level
					}
				"
			/>
		</div>
	</div>
</template>

<script>
import FilterTree from '@/components/Query/FilterTree.vue'
import SimpleFilterPicker from '@/components/Query/SimpleFilterPicker.vue'

export default {
	name: 'FilterPicker',
	props: ['query'],
	components: {
		FilterTree,
		SimpleFilterPicker,
	},
	data() {
		return {
			adding_filter: false,
			editing_filter: false,
			add_next_filter_at: 1,
			edit_filter_at: {},
		}
	},
	computed: {
		tables() {
			return this.query.doc.tables.map((row) => {
				return {
					label: row.label,
					table: row.table,
				}
			})
		},
		filters() {
			return JSON.parse(this.query.doc.filters || '{}')
		},
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
		get_filter_at({ level, idx }) {
			if (!level || !idx) {
				return {}
			}

			let filter_group = this.get_filter_group_at(level)
			if (filter_group.conditions) {
				return filter_group.conditions[idx]
			}

			return {}
		},
		toggle_group_operator({ level }) {
			const filters = this.get_filter_group_at(level)
			filters.group_operator = filters.group_operator == '&' ? 'or' : '&'
			this.query.update_filters.submit({ filters: this.filters })
		},
		filter_selected({ filter }) {
			if (this.edit_filter_at.level && this.edit_filter_at.idx) {
				const { level, idx } = this.edit_filter_at
				this.edit_filter({ filter, level, idx })
			} else if (this.add_next_filter_at) {
				const level = this.add_next_filter_at
				this.add_filter({ filter, level })
			}
		},
		add_filter({ filter, level }) {
			const filter_group = this.get_filter_group_at(level)
			filter_group.conditions.push(filter)
			this.adding_filter = false
			this.add_next_filter_at = 1
			this.query.update_filters.submit({ filters: this.filters })
		},
		edit_filter({ filter, level, idx }) {
			const filter_group = this.get_filter_group_at(level)
			const conditions = filter_group.conditions
			conditions[idx] = filter
			this.edit_filter_at = {}
			this.adding_filter = false
			this.editing_filter = false
			this.query.update_filters.submit({ filters: this.filters })
		},
		branch_filter_at({ level, idx }) {
			const filter_group = this.get_filter_group_at(level)
			const conditions = filter_group.conditions

			const condition_to_replace = conditions[idx]
			filter_group.conditions[idx] = {
				level: level + 1,
				group_operator: filter_group.group_operator == '&' ? 'or' : '&',
				conditions: [condition_to_replace],
			}
			this.query.update_filters.submit({ filters: this.filters })
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

			this.query.update_filters.submit({ filters: this.filters })
		},
	},
}
</script>
