<template>
	<div @dblclick="edit_filter_at = idx">
		<div
			v-if="edit_filter_at != idx"
			class="group menu-item relative -ml-1 flex w-fit cursor-pointer items-center rounded-md px-2 hover:bg-gray-50"
		>
			<FeatherIcon name="corner-down-right" class="mr-2 h-3 w-3 text-gray-500" />
			<div class="flex h-8 items-center whitespace-nowrap rounded-md font-normal">
				<div class="flex flex-col">
					<span class="flex items-center">
						<FeatherIcon name="columns" class="mr-1 h-3 w-3 text-gray-500/90" />
						{{ filter.left.label }}
					</span>
					<!-- <span class="text-xs font-light text-gray-500">{{ filter.left.table_label }}</span> -->
				</div>
				<!-- operator with border -->
				<!-- <div class="mx-3 rounded border-[0.5px] border-gray-500 bg-gray-50 px-1.5 py-0.5 text-xs text-gray-600">
							{{ filter.operator.label }}
						</div> -->
				<div class="mx-2 text-sm text-green-600">
					{{ filter.operator.label }}
				</div>
				<div v-if="filter.right_type == 'Column'" class="flex flex-col">
					<span class="flex items-center">
						<FeatherIcon name="columns" class="mr-1 h-3 w-3 text-gray-500/90" />
						{{ filter.right.label }}
					</span>
					<!-- <span class="text-xs font-light text-gray-500">{{ filter.right.table_label }}</span> -->
				</div>
				<div v-else class="flex items-center">
					<FeatherIcon name="type" class="mr-1 h-3 w-3 text-gray-500/90" />
					{{ filter.right.label }}
				</div>
			</div>
			<FeatherIcon
				name="x"
				class="invisible ml-2 h-3 w-3 text-gray-500 hover:text-gray-700 group-hover:visible"
				@click="$emit('remove_filter', { idx, level })"
			/>
			<div
				class="invisible absolute -right-20 flex w-fit cursor-pointer items-center py-1 text-sm font-light italic text-gray-400 hover:visible hover:text-gray-500 group-hover:visible"
				:class="{ 'px-3': group_operator == 'Any', 'px-3.5': group_operator == 'All' }"
				@click.prevent.stop="$emit('branch_filter_at', { idx, level })"
			>
				+ {{ group_operator == 'All' ? 'OR' : 'AND' }} filter
			</div>
		</div>
		<div v-else-if="edit_filter_at == idx" class="-ml-1 flex flex-1 items-center px-2 py-1">
			<FeatherIcon name="corner-down-right" class="mr-1 h-3 w-3 text-gray-500" />
			<FilterSearch
				ref="filter_picker_editor"
				:query="query"
				:tables="tables"
				:filter="filter"
				@keydown.esc="edit_filter_at = null"
				v-on-outside-click="() => (edit_filter_at = null)"
				@filter_selected="
					(filter) => {
						edit_filter_at = null
						$emit('filter_edited', { filter, level, idx })
					}
				"
			/>
		</div>
	</div>
</template>

<script>
import FilterSearch from './FilterSearch.vue'

export default {
	name: 'FilterNode',
	components: {
		FilterSearch,
	},
	props: ['query', 'tables', 'group_operator', 'filter', 'idx', 'level'],
	data() {
		return {
			edit_filter_at: null,
		}
	},
}
</script>
