<template>
	<div class="w-fit text-base text-gray-800">
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
					<FilterNode
						:filters="condition"
						:query="query"
						:tables="tables"
						@toggle_group_operator="(params) => $emit('toggle_group_operator', params)"
						@filter_selected="(params) => $emit('filter_selected', params)"
						@branch_condition_at="(params) => $emit('branch_condition_at', params)"
						@remove_filter="(params) => $emit('remove_filter', params)"
					/>
				</div>
				<div
					v-else
					class="group menu-item relative -ml-1 flex w-fit cursor-pointer items-center rounded-md px-2 hover:bg-gray-50"
					@click="menu_open_for = idx"
				>
					<FeatherIcon name="corner-down-right" class="mr-2 h-3 w-3 text-gray-500" />
					<div class="flex h-8 items-center whitespace-nowrap rounded-md font-normal">
						<div class="flex flex-col">
							<span class="flex items-center">
								<FeatherIcon name="columns" class="mr-1 h-3 w-3 text-gray-500/90" />
								{{ condition.left.label }}
							</span>
							<!-- <span class="text-xs font-light text-gray-500">{{ condition.left.table_label }}</span> -->
						</div>
						<!-- operator with border -->
						<!-- <div class="mx-3 rounded border-[0.5px] border-gray-500 bg-gray-50 px-1.5 py-0.5 text-xs text-gray-600">
							{{ condition.operator.label }}
						</div> -->
						<div class="mx-2 text-sm text-green-600">
							{{ condition.operator.label }}
						</div>
						<div v-if="condition.right_type == 'Column'" class="flex flex-col">
							<span class="flex items-center">
								<FeatherIcon name="columns" class="mr-1 h-3 w-3 text-gray-500/90" />
								{{ condition.right.label }}
							</span>
							<!-- <span class="text-xs font-light text-gray-500">{{ condition.right.table_label }}</span> -->
						</div>
						<div v-else class="flex items-center">
							<FeatherIcon name="type" class="mr-1 h-3 w-3 text-gray-500/90" />
							{{ condition.right.label }}
						</div>
					</div>
					<FeatherIcon
						name="x"
						class="invisible ml-2 h-3 w-3 text-gray-500 hover:text-gray-700 group-hover:visible"
						@click="$emit('remove_filter', { idx, level })"
					/>
					<div
						class="invisible absolute -right-28 flex w-fit cursor-pointer items-center py-1 text-sm font-light italic text-gray-400 hover:visible hover:text-gray-500 group-hover:visible"
						:class="{ ' px-3': group_operator == 'Any', 'px-3.5': group_operator == 'All' }"
						@click.prevent.stop="$emit('branch_condition_at', { idx, level })"
					>
						+ {{ group_operator == 'All' ? 'OR' : 'AND' }} condition
					</div>
				</div>
			</div>
			<div v-if="add_new_filter" class="-ml-1 flex flex-1 items-center px-2 py-1">
				<FeatherIcon name="corner-down-right" class="mr-1 h-3 w-3 text-gray-500" />
				<FilterPickerSearch
					ref="filter_picker_search"
					:query="query"
					:tables="tables"
					@keydown.esc="add_new_filter = false"
					@filter_selected="
						(filter) => {
							add_new_filter = false
							$emit('filter_selected', { filter, level })
						}
					"
				/>
			</div>
			<div
				v-if="!add_new_filter"
				class="-ml-1 flex w-fit cursor-pointer items-center px-2 text-sm font-light text-gray-400 hover:text-gray-500"
			>
				<FeatherIcon name="corner-down-right" class="mr-2 h-3 w-3 text-gray-500" />
				<div class="flex items-center py-1 italic" @click.prevent.stop="add_new_filter = true">Add a condition</div>
			</div>
		</div>
	</div>
</template>

<script>
import FilterPickerSearch from './FilterPickerSearch.vue'

export default {
	name: 'FilterNode',
	props: ['filters', 'query', 'tables'],
	components: {
		FilterPickerSearch,
	},
	data() {
		return {
			add_new_filter: false,
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
