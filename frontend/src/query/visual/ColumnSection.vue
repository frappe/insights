<script setup>
import { Combine, GripVertical } from 'lucide-vue-next'
import { computed, inject, nextTick, ref } from 'vue'
import Draggable from 'vuedraggable'
import ColumnEditor from './ColumnEditor.vue'
import ColumnListItem from './ColumnListItem.vue'
import { NEW_COLUMN } from './constants'

const query = inject('query')
const assistedQuery = inject('assistedQuery')
!assistedQuery.columnOptions.length && assistedQuery.fetchColumnOptions()

const columns = computed(() => assistedQuery.columns)
const columnRefs = ref(null)
const activeColumnIdx = ref(null)

function onColumnSelect(column) {
	if (!column) return
	const columnAlreadyExists = columns.value.find(
		(c) => c.table === column.table && c.column === column.column && c.label === column.label
	)
	if (columnAlreadyExists) {
		return
	}
	assistedQuery.addColumns([column])
}

function onRemoveColumn() {
	assistedQuery.removeColumnAt(activeColumnIdx.value)
	activeColumnIdx.value = null
}
function onSaveColumn(column) {
	assistedQuery.updateColumnAt(activeColumnIdx.value, column)
	activeColumnIdx.value = null
}
function onAddColumnExpression() {
	assistedQuery.addColumns([
		{
			...NEW_COLUMN,
			expression: {
				raw: '',
				ast: {},
			},
		},
	])
	nextTick(() => {
		activeColumnIdx.value = columns.value.length - 1
	})
}

function onColumnSort(e) {
	if (e.oldIndex != e.newIndex) {
		assistedQuery.moveColumn(e.oldIndex, e.newIndex)
	}
}
</script>

<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<div class="flex items-center space-x-1.5">
				<Combine class="h-4 w-4 text-gray-600" />
				<p class="font-medium">Summarize</p>
			</div>
			<Autocomplete
				:modelValue="columns"
				bodyClasses="w-[18rem]"
				@update:modelValue="onColumnSelect"
				:options="assistedQuery.groupedColumnOptions"
				@update:query="assistedQuery.fetchColumnOptions"
			>
				<template #target="{ togglePopover }">
					<Button variant="outline" icon="plus" @click="togglePopover"></Button>
				</template>
				<template #footer="{ togglePopover }">
					<Button
						class="w-full"
						variant="ghost"
						iconLeft="plus"
						@click="onAddColumnExpression() || togglePopover()"
					>
						Custom Expression
					</Button>
				</template>
			</Autocomplete>
		</div>
		<Draggable
			class="w-full"
			:model-value="columns"
			group="columns"
			item-key="label"
			handle=".handle"
			@sort="onColumnSort"
		>
			<template #item="{ element: column, index: idx }">
				<div class="mb-2 flex items-center gap-1">
					<GripVertical class="handle h-4 w-4 flex-shrink-0 cursor-grab text-gray-500" />
					<div class="flex-1">
						<Popover
							:show="activeColumnIdx === idx"
							@close="activeColumnIdx = null"
							placement="right-start"
						>
							<template #target="{ togglePopover }">
								<ColumnListItem
									:column="column"
									:isActive="activeColumnIdx === idx"
									@edit-column="activeColumnIdx = idx"
									@remove-column="assistedQuery.removeColumnAt(idx)"
								/>
							</template>
							<template #body>
								<div
									v-if="activeColumnIdx === idx"
									class="ml-2 w-[20rem] rounded-lg border border-gray-100 bg-white text-base shadow-xl"
								>
									<ColumnEditor
										:column="column"
										@discard="activeColumnIdx = null"
										@remove="onRemoveColumn"
										@save="onSaveColumn"
									/>
								</div>
							</template>
						</Popover>
					</div>
				</div>
			</template>
		</Draggable>
	</div>
</template>
