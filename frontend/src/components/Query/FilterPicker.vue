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
				<Button
					class="mr-2 !flex !h-7 !w-7 !items-center !justify-center !p-0 !text-gray-700"
					@click="adding_filter = false"
				>
					<FeatherIcon name="chevron-left" class="h-4 w-4" />
				</Button>
				<div class="text-lg font-medium">{{ editing_filter ? 'Edit' : 'Add' }} a Filter</div>
			</div>
			<div class="-mt-2 flex flex-col space-y-3">
				<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md font-light"
						:class="{ 'border bg-white font-normal shadow-sm': filter_type == 'simple' }"
						@click.prevent.stop="filter_type = 'simple'"
					>
						Simple
					</div>
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md"
						:class="{ 'border bg-white font-normal shadow-sm': filter_type == 'expression' }"
						@click.prevent.stop="filter_type = 'expression'"
					>
						Expression
					</div>
				</div>
				<SimpleFilterPicker
					v-if="filter_type == 'simple'"
					:query="query"
					@filter-select="filter_selected"
					:filter="get_filter_at(edit_filter_at)"
				/>
				<ExpressionFilterPicker
					v-if="filter_type == 'expression'"
					:query="query"
					@filter-select="filter_selected"
					:filter="get_filter_at(edit_filter_at)"
				/>
			</div>
		</div>
		<div
			v-if="filters.conditions.length == 0 && !adding_filter"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No filters added</p>
		</div>
		<div
			v-else-if="filters.conditions.length > 0 && !adding_filter"
			class="-mt-2 flex h-full items-start overflow-scroll"
		>
			<FilterTree
				:filters="filters"
				@remove_filter="remove_filter"
				@branch_filter_at="branch_filter_at"
				@toggle_group_operator="toggle_group_operator"
				@edit_filter="
					({ level, position, idx, is_expression }) => {
						adding_filter = true
						editing_filter = true
						edit_filter_at = { level, position, idx, is_expression }
						filter_type = is_expression ? 'expression' : 'simple'
					}
				"
				@add_filter="
					({ level, position }) => {
						adding_filter = true
						add_next_filter_at = { level, position }
					}
				"
			/>
		</div>
	</div>
</template>

<script>
import FilterTree from '@/components/Query/FilterTree.vue'
import SimpleFilterPicker from '@/components/Query/SimpleFilterPicker.vue'
import ExpressionFilterPicker from '@/components/Query/ExpressionFilterPicker.vue'

export default {
	name: 'FilterPicker',
	props: ['query'],
	components: {
		FilterTree,
		SimpleFilterPicker,
		ExpressionFilterPicker,
	},
	data() {
		return {
			filter_type: 'simple',
			adding_filter: false,
			editing_filter: false,
			edit_filter_at: {},
			add_next_filter_at: { level: 1, position: 1 },
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
		get_filter_group_at({ filters, level, position, parent_index }) {
			if (level == 1 && position == 1) {
				return this.filters
			}

			// find the filter group at the given level and position
			let filter_groups = filters || this.filters
			let filter_group_at_level = null

			for (let i = 0; i < filter_groups.conditions.length; i++) {
				let filter_group = filter_groups.conditions[i]
				if (filter_group.level == level && (filter_group.position == position || i == parent_index)) {
					filter_group_at_level = filter_group
					break
				}

				if (filter_group.conditions?.length) {
					let filter_group_at_level_in_group = this.get_filter_group_at({
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
		},
		get_parent_filter_group_of({ level, position }) {
			const parent_level = level - 1
			const filter_group_index = position - 1

			return this.get_filter_group_at({
				filters: this.filters,
				level: parent_level,
				parent_index: filter_group_index,
			})
		},
		get_filter_at({ level, position, idx }) {
			if (!level || !position || typeof idx !== 'number') {
				return {}
			}

			let filter_group = this.get_filter_group_at({ level, position })
			if (filter_group.conditions.length > idx) {
				return filter_group.conditions[idx]
			}

			return {}
		},
		toggle_group_operator({ level, position }) {
			const filters = this.get_filter_group_at({ level, position })
			filters.group_operator = filters.group_operator == '&' ? 'or' : '&'
			this.query.update_filters.submit({ filters: this.filters })
		},
		filter_selected({ filter }) {
			if (this.edit_filter_at.level && this.edit_filter_at.position && typeof this.edit_filter_at.idx == 'number') {
				const { level, position, idx } = this.edit_filter_at
				this.edit_filter({ filter, level, position, idx })
			} else if (this.add_next_filter_at.level && this.add_next_filter_at.position) {
				const { level, position } = this.add_next_filter_at
				this.add_filter({ filter, level, position })
			}
			this.filter_type = 'simple'
		},
		add_filter({ filter, level, position }) {
			const filter_group = this.get_filter_group_at({ level, position })
			filter_group.conditions.push(filter)
			this.adding_filter = false
			this.add_next_filter_at = { level: 1, position: 1 }
			this.query.update_filters.submit({ filters: this.filters })
		},
		edit_filter({ filter, level, position, idx }) {
			const filter_group = this.get_filter_group_at({ level, position })
			const conditions = filter_group.conditions
			conditions[idx] = filter
			this.edit_filter_at = {}
			this.adding_filter = false
			this.editing_filter = false
			this.query.update_filters.submit({ filters: this.filters })
		},
		branch_filter_at({ level, position, idx }) {
			const filter_group = this.get_filter_group_at({ level, position })
			const conditions = filter_group.conditions

			const condition_to_replace = conditions[idx]
			filter_group.conditions[idx] = {
				level: level + 1,
				position: idx + 1,
				group_operator: filter_group.group_operator == '&' ? 'or' : '&',
				conditions: [condition_to_replace],
			}
			this.query.update_filters.submit({ filters: this.filters })
		},
		remove_filter({ level, position, idx }) {
			if (level == 1 && typeof idx == 'number') {
				// remove the filter from root level
				this.filters.conditions.splice(idx, 1)
			}

			if (level > 1 && position && typeof idx == 'number') {
				// remove the filter at `idx` from the filter group at `level` & `position`
				const filter_group = this.get_filter_group_at({ level, position })
				filter_group.conditions.splice(idx, 1)
			}

			this.query.update_filters.submit({ filters: this.filters })
		},
	},
}
</script>
