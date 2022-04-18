<template>
	<div class="w-full text-base text-gray-800">
		<div class="group flex items-baseline py-1 text-sm font-medium" :class="{ 'ml-1': level != 1 }">
			<FeatherIcon v-if="level != 1" name="corner-down-right" class="mr-1 h-3 w-3 text-gray-500" />
			<div class="flex items-center" :class="{ 'ml-1': level != 1 }">
				<span
					class="mr-1 flex cursor-pointer items-center border-gray-200 group-hover:underline"
					@click="$emit('toggle_group_operator', { level })"
				>
					{{ group_operator }}
				</span>
				<span class="text-xs font-light text-gray-500"> of the following are true </span>
				<FeatherIcon
					name="x"
					class="invisible ml-2 h-3 w-3 text-gray-500 hover:text-gray-700 group-hover:visible"
					@click="$emit('remove_filter', { level })"
				/>
			</div>
		</div>
		<div v-if="conditions" class="flex flex-col" :class="{ 'pl-4': level != 1 }">
			<div v-for="(condition, idx) in conditions" :key="idx" class="flex items-center">
				<div v-if="condition.group_operator" class="flex items-center">
					<FilterTree
						:filters="condition"
						:query="query"
						:tables="tables"
						@toggle_group_operator="$emit('toggle_group_operator', $event)"
						@filter_selected="$emit('filter_selected', $event)"
						@filter_edited="$emit('filter_edited', $event)"
						@branch_filter_at="$emit('branch_filter_at', $event)"
						@remove_filter="$emit('remove_filter', $event)"
					/>
				</div>
				<div v-else>
					<FilterNode
						:query="query"
						:tables="tables"
						:filter="condition"
						:idx="idx"
						:level="level"
						:group_operator="group_operator"
						@remove_filter="$emit('remove_filter', $event)"
						@branch_filter_at="$emit('branch_filter_at', $event)"
						@filter_edited="$emit('filter_edited', $event)"
					/>
				</div>
			</div>
			<!-- Add a new filter -->
			<div
				v-if="!add_new_filter"
				class="-ml-1 flex cursor-pointer items-center px-2 py-1 text-gray-400 hover:text-gray-500"
			>
				<FeatherIcon name="corner-down-right" class="mr-2 h-3 w-3" />
				<div class="text-sm font-light italic" @click.prevent.stop="add_new_filter = true">Add a condition</div>
			</div>
			<div v-else class="-ml-1 flex flex-1 items-center px-2 py-1">
				<FeatherIcon name="corner-down-right" class="mr-1 h-3 w-3 text-gray-500" />
				<FilterSearch
					ref="filter_picker_search"
					:query="query"
					:tables="tables"
					@keydown.esc="add_new_filter = false"
					v-on-outside-click="() => (add_new_filter = false)"
					@filter_selected="
						(filter) => {
							add_new_filter = false
							$emit('filter_selected', { filter, level })
						}
					"
				/>
			</div>
		</div>
	</div>
</template>

<script>
import FilterSearch from './FilterSearch.vue'
import FilterNode from './FilterNode.vue'

export default {
	name: 'FilterTree',
	props: ['filters', 'query', 'tables'],
	components: {
		FilterSearch,
		FilterNode,
	},
	data() {
		return {
			add_new_filter: false,
			edit_filter_at: null,
		}
	},
	computed: {
		level() {
			return this.filters.level || 1
		},
		group_operator() {
			return this.filters.group_operator || 'All'
		},
		conditions() {
			return this.filters.conditions || []
		},
	},
}
</script>
