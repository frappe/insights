<script setup lang="ts">
import { fieldtypesToIcon } from '@/utils'
import { SearchIcon, SquareCheck, SquareIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import { QueryPipeline, QueryPipelineResultColumn } from './useQueryPipeline'

const emit = defineEmits({
	select: (columns: string[]) => true,
})
const showDialog = defineModel()

const queryPipeline = inject('queryPipeline') as QueryPipeline
const columns = computed(() => queryPipeline.results.columns)

const columnSearchQuery = ref('')
const filteredColumns = computed(() => {
	if (!columns.value.length) return []
	if (!columnSearchQuery.value) return columns.value
	return columns.value.filter((column) => {
		return column.name.toLowerCase().includes(columnSearchQuery.value.toLowerCase())
	})
})

const selectedColumns = ref<QueryPipelineResultColumn[]>([])
function isSelected(column: QueryPipelineResultColumn) {
	return selectedColumns.value.includes(column)
}
function toggleColumn(column: QueryPipelineResultColumn) {
	const index = selectedColumns.value.indexOf(column)
	if (index === -1) {
		selectedColumns.value.push(column)
	} else {
		selectedColumns.value.splice(index, 1)
	}
}
function toggleSelectAll() {
	if (areAllSelected.value) {
		selectedColumns.value = []
	} else {
		selectedColumns.value = [...columns.value]
	}
}
const areAllSelected = computed(() => selectedColumns.value.length === columns.value.length)
const areNoneSelected = computed(() => selectedColumns.value.length === 0)
function confirmSelection() {
	emit(
		'select',
		selectedColumns.value.map((c) => c.name)
	)
	showDialog.value = false
}
</script>

<template>
	<Dialog
		v-if="showDialog"
		v-model="showDialog"
		:options="{
			size: 'sm',
			title: 'Select Columns',
			actions: [
				{
					label: 'Confirm',
					variant: 'solid',
					disabled: areNoneSelected,
					onClick: confirmSelection,
				},
				{
					label: 'Cancel',
					onClick: () => (showDialog = false),
				},
			],
		}"
	>
		<template #body-content>
			<div class="-mb-5 flex max-h-[20rem] flex-col gap-2 overflow-auto p-0.5">
				<div class="flex gap-2">
					<FormControl
						class="flex-1"
						autocomplete="off"
						placeholder="Search by name"
						v-model="columnSearchQuery"
					>
						<template #prefix>
							<SearchIcon class="h-4 w-4 text-gray-500" />
						</template>
					</FormControl>
					<Button @click="toggleSelectAll">
						{{ areAllSelected ? 'Deselect All' : 'Select All' }}
					</Button>
				</div>
				<div class="flex flex-col rounded border p-1 text-base">
					<template v-for="column in filteredColumns">
						<div
							class="flex h-7 cursor-pointer items-center justify-between rounded px-2 hover:bg-gray-100"
							@click="toggleColumn(column)"
						>
							<div class="flex items-center gap-1.5">
								<component
									class="h-5 w-5"
									stroke-width="1.5"
									:is="isSelected(column) ? SquareCheck : SquareIcon"
									:class="isSelected(column) ? 'text-gray-800' : 'text-gray-600'"
									:color="isSelected(column) ? 'white' : 'currentColor'"
									:fill="isSelected(column) ? 'currentColor' : 'none'"
								/>
								<component
									:is="fieldtypesToIcon[column.type]"
									class="h-4 w-4 text-gray-700"
									stroke-width="1.5"
								/>
								<span>{{ column.name }}</span>
							</div>
						</div>
					</template>
				</div>
			</div>
		</template>
	</Dialog>
</template>
