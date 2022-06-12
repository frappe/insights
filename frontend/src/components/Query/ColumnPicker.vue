<template>
	<div class="flex flex-1 flex-col px-4 pb-4">
		<div v-if="!addingColumn && !editingColumn" class="flex flex-1 flex-col">
			<div class="mb-4 flex items-center justify-between">
				<div class="text-lg font-medium">Dimension & Metrics</div>
				<Button icon="plus" @click="addingColumn = true"></Button>
			</div>
			<div
				v-if="query.columns.length == 0"
				class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
			>
				<p>No columns selected</p>
			</div>
			<div v-else-if="query.columns.length > 0" class="flex flex-1 select-none flex-col overflow-scroll scrollbar-hide">
				<Draggable v-model="query.columns" group="columns" item-key="name" @sort="updateColumnOrder">
					<template #item="{ element: column }">
						<div
							class="flex h-10 cursor-pointer items-center justify-between space-x-8 border-b text-sm text-gray-600 last:border-0 hover:bg-gray-50"
							@click.prevent.stop="
								() => {
									editColumn = column
									editingColumn = true
									newColumnType = column.aggregation == 'Group By' ? 'Dimension' : 'Metric'
								}
							"
						>
							<div class="flex items-center">
								<DragHandleIcon class="mr-1 -ml-1 h-4 w-4 rotate-90 cursor-grab self-center text-gray-400" />
								<span
									v-if="column.aggregation"
									class="my-0 mr-2 flex-1 select-none whitespace-nowrap rounded border border-orange-200 px-1 py-0.5 text-xs text-orange-400/80"
								>
									{{ column.aggregation }}
								</span>
								<span class="text-base font-medium">{{ column.label }}</span>
							</div>
							<div class="flex items-center">
								<div class="mr-1 font-light text-gray-500">{{ column.table_label }}</div>
								<div
									class="flex items-center px-1 py-0.5 text-gray-500 hover:text-gray-600"
									@click.prevent.stop="query.removeColumn({ column })"
								>
									<FeatherIcon name="x" class="h-3 w-3" />
								</div>
							</div>
						</div>
					</template>
				</Draggable>
			</div>
		</div>
		<div v-if="addingColumn || editingColumn">
			<div class="mb-4 flex h-7 items-center">
				<Button icon="chevron-left" class="mr-2" @click="resetNewColumn"> </Button>
				<div class="text-lg font-medium">{{ editingColumn ? 'Edit' : 'Add' }} {{ newColumnType }}</div>
			</div>
			<div class="flex flex-col space-y-3">
				<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md font-light"
						:class="{ 'border bg-white font-normal shadow-sm': newColumnType == 'Metric' }"
						@click.prevent.stop="newColumnType = 'Metric'"
					>
						Metric
					</div>
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md"
						:class="{ 'border bg-white font-normal shadow-sm': newColumnType == 'Dimension' }"
						@click.prevent.stop="newColumnType = 'Dimension'"
					>
						Dimension
					</div>
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md"
						:class="{ 'border bg-white font-normal shadow-sm': newColumnType == 'Expression' }"
						@click.prevent.stop="newColumnType = 'Expression'"
					>
						Expression
					</div>
				</div>
				<MetricPicker
					v-if="newColumnType == 'Metric'"
					:column="editColumn"
					@column-select="addUpdateColumn"
					@close="resetNewColumn"
				/>
				<DimensionPicker
					v-if="newColumnType == 'Dimension'"
					:column="editColumn"
					@column-select="addUpdateColumn"
					@close="resetNewColumn"
				/>
				<div v-if="newColumnType == 'Expression'" class="text-center text-gray-500">Coming Soon...</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import Draggable from 'vuedraggable'
import DragHandleIcon from '@/components/DragHandleIcon.vue'
import MetricPicker from '@/components/Query/MetricPicker.vue'
import DimensionPicker from '@/components/Query/DimensionPicker.vue'

import { inject, ref } from 'vue'

const query = inject('query')

const newColumnType = ref('Metric')
const addingColumn = ref(false)

const editColumn = ref({})
const editingColumn = ref(false)

function addUpdateColumn(column) {
	if (addingColumn.value) {
		query.addColumn({ column })
	} else if (editingColumn.value) {
		query.updateColumn({ column })
	}
	resetNewColumn()
}
function resetNewColumn() {
	newColumnType.value = 'Metric'
	addingColumn.value = false
	editingColumn.value = false
	editColumn.value = {}
}
function updateColumnOrder(e) {
	if (e.oldIndex != e.newIndex) {
		query.moveColumn({
			from_index: e.oldIndex,
			to_index: e.newIndex,
		})
	}
}
</script>
