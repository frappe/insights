<template>
	<div class="flex flex-1 flex-col px-4">
		<div v-if="adding_column" class="mb-4 flex flex-shrink-0">
			<ColumnSearch :query="query" @column_search_blur="adding_column = false" />
		</div>
		<div v-else-if="!adding_column" class="mb-4 flex items-center justify-between">
			<div class="text-lg font-medium">Columns</div>
			<Button class="!flex !h-7 !w-7 !items-center !justify-center !p-0 !text-gray-700" @click="adding_column = true">
				+
			</Button>
		</div>
		<div
			v-if="columns.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No columns selected</p>
		</div>
		<div v-else class="-mt-2 flex flex-1 select-none flex-col overflow-scroll scrollbar-hide">
			<Draggable v-model="columns" group="columns" item-key="name" @sort="update_column_order">
				<template #item="{ element: column }">
					<div
						class="flex h-10 cursor-pointer items-center justify-between space-x-8 border-b text-sm text-gray-600 last:border-0 hover:bg-gray-50"
					>
						<div class="flex items-baseline">
							<DragHandleIcon class="mr-1 -ml-1 h-4 w-4 rotate-90 cursor-grab self-center text-gray-400" />
							<div
								v-if="column.aggregation"
								class="my-0 mr-2 flex-1 select-none whitespace-nowrap rounded border border-orange-200 px-1 py-0.5 text-xs text-orange-400/80"
							>
								{{ column.aggregation }}
							</div>
							<div class="text-base font-medium">{{ column.label }}</div>
						</div>
						<div class="flex items-center">
							<div class="font-light text-gray-500">{{ column.table_label }}</div>
							<div
								class="ml-1 flex items-center px-1 py-0.5 text-gray-500 hover:text-gray-600"
								@click="remove_column(column)"
							>
								<FeatherIcon name="x" class="h-3 w-3" />
							</div>
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

export default {
	name: 'ColumnPicker',
	props: ['query'],
	components: {
		Draggable,
		ColumnSearch,
		DragHandleIcon,
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
		remove_column(column) {
			this.query.remove_column.submit({ column })
		},
	},
}
</script>
