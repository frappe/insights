<template>
	<div
		v-if="query.columns.length == 0"
		class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
	>
		<p>No columns selected</p>
	</div>
	<div
		v-else-if="query.doc.columns.length > 0"
		class="flex flex-1 select-none flex-col overflow-scroll scrollbar-hide"
	>
		<Draggable
			v-model="query.doc.columns"
			group="columns"
			item-key="name"
			@sort="updateColumnOrder"
		>
			<template #item="{ element: column }">
				<div
					class="flex h-10 cursor-pointer items-center justify-between space-x-8 border-b text-sm text-gray-600 last:border-0 hover:bg-gray-50"
					@click.prevent.stop="
						() => {
							$emit('edit-column', column)
							newColumnType =
								column.aggregation == 'Group By' ? 'Dimension' : 'Metric'
						}
					"
				>
					<div class="flex items-center">
						<DragHandleIcon
							class="mr-1 -ml-1 h-4 w-4 rotate-90 cursor-grab self-center text-gray-400"
						/>
						<span
							v-if="column.aggregation"
							class="my-0 mr-2 flex-1 select-none whitespace-nowrap rounded border border-orange-200 px-1 py-0.5 text-xs text-orange-400/80"
						>
							{{ column.aggregation }}
						</span>
						<span class="text-base font-medium">{{ column.label }}</span>
					</div>
					<div class="flex items-center">
						<div class="mr-1 font-light text-gray-500">
							{{ column.is_expression ? 'Expression' : column.table_label }}
						</div>
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
</template>

<script setup>
import Draggable from 'vuedraggable'
import DragHandleIcon from '@/components/Icons/DragHandleIcon.vue'

import { inject } from 'vue'

const query = inject('query')
defineEmits(['edit-column'])

function updateColumnOrder(e) {
	if (e.oldIndex != e.newIndex) {
		query.moveColumn({
			from_index: e.oldIndex,
			to_index: e.newIndex,
		})
	}
}
</script>
