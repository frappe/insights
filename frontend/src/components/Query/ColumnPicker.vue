<template>
	<div class="flex flex-1 flex-col px-4 pb-4">
		<div v-if="adding_column" class="mb-4 flex flex-shrink-0">
			<ColumnSearch :query="query" @column_search_blur="adding_column = false" />
		</div>
		<div v-else-if="!adding_column" class="mb-4 flex items-center justify-between">
			<div class="text-lg font-medium">Columns</div>
			<Button icon="plus" @click="adding_column = true"></Button>
		</div>
		<div
			v-if="columns.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No columns selected</p>
		</div>
		<div v-else class="flex flex-1 select-none flex-col overflow-scroll scrollbar-hide">
			<Draggable v-model="columns" group="columns" item-key="name" @sort="update_column_order">
				<template #item="{ element: column }">
					<div
						class="flex h-10 cursor-pointer items-center justify-between space-x-8 border-b text-sm text-gray-600 last:border-0 hover:bg-gray-50"
					>
						<div class="flex items-center">
							<DragHandleIcon class="mr-1 -ml-1 h-4 w-4 rotate-90 cursor-grab self-center text-gray-400" />
							<span
								v-if="column.aggregation"
								class="my-0 mr-2 flex-1 select-none whitespace-nowrap rounded border border-orange-200 px-1 py-0.5 text-xs text-orange-400/80"
							>
								{{ column.aggregation }}
							</span>
							<input
								type="text"
								spellcheck="false"
								ref="column_label_input"
								v-model="column.label"
								:size="Math.max(parseInt(column.label?.length * 1.2), 6)"
								class="mr-2 -ml-1.5 cursor-text rounded border-none bg-transparent p-0 px-1.5 pr-2 text-base focus:bg-gray-100/75 focus:text-gray-600 focus:outline-none focus:ring-transparent"
								@blur="update_column_label(column)"
								@keydown.enter="update_column_label(column)"
							/>
						</div>
						<div class="flex items-center">
							<div class="mr-1 font-light text-gray-500">{{ column.table_label }}</div>
							<ColumnMenu :query="query" :column="column" />
						</div>
					</div>
				</template>
			</Draggable>
		</div>
	</div>
</template>

<script>
import Draggable from 'vuedraggable'
import ColumnSearch from '@/components/Query/ColumnSearch.vue'
import DragHandleIcon from '@/components/DragHandleIcon.vue'
import ColumnMenu from '@/components/Query/ColumnMenu.vue'

export default {
	name: 'ColumnPicker',
	props: ['query'],
	components: {
		Draggable,
		ColumnSearch,
		DragHandleIcon,
		ColumnMenu,
	},
	data() {
		return {
			adding_column: false,
		}
	},
	computed: {
		tables() {
			return this.query.doc.tables
		},
		columns() {
			return this.query.doc.columns
		},
	},
	methods: {
		update_column_order(e) {
			if (e.oldIndex != e.newIndex) {
				this.query.move_column.submit({
					from_index: e.oldIndex,
					to_index: e.newIndex,
				})
			}
		},
		update_column_label(column) {
			if (!column.label?.length) {
				this.query.get.fetch()
				return
			}
			this.query.update_column.submit({ column: column })
		},
	},
}
</script>
