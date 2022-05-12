<template>
	<div class="flex min-h-[16rem] min-w-[26rem] flex-1 flex-col p-4">
		<ColumnSearch v-if="tables.length > 0" class="mb-4" :query="query" />
		<div
			v-if="tables.length > 0 && columns.length == 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No columns selected</p>
		</div>
		<div v-else class="flex flex-1 select-none flex-col divide-y divide-gray-200 overflow-scroll scrollbar-hide">
			<Draggable v-model="columns" group="columns" item-key="name" @sort="update_column_order">
				<template #item="{ element: column }">
					<div
						class="flex cursor-pointer items-center justify-between space-x-8 rounded py-2 text-sm text-gray-600 hover:bg-gray-50"
					>
						<div class="flex items-baseline">
							<DragHandleIcon class="mr-1 h-4 w-4 rotate-90 cursor-grab self-center text-gray-400" />
							<div class="text-base font-medium">{{ column.label }}</div>
						</div>
						<div class="flex items-center">
							<div class="font-light text-gray-500">{{ column.table_label }} &#8226; {{ column.type }}</div>
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
import ColumnSearch from './ColumnSearch.vue'
import Draggable from 'vuedraggable'
import DragHandleIcon from '@/components/DragHandleIcon.vue'

export default {
	name: 'ColumnPicker',
	props: ['query'],
	components: {
		ColumnSearch,
		Draggable,
		DragHandleIcon,
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
