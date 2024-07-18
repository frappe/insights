<script setup lang="ts">
import { CheckSquare, SearchIcon, SquareIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import { QueryResultColumn, SelectArgs } from '../../types/query.types'
import { Query } from '../query'
import DataTypeIcon from './DataTypeIcon.vue'

const props = defineProps<{ columns?: SelectArgs }>()
const emit = defineEmits({
	select: (args: SelectArgs) => true,
})
const showDialog = defineModel()

const query = inject('query') as Query
const columns = ref<QueryResultColumn[]>([])
query.getColumnsForSelection().then((cols: QueryResultColumn[]) => {
	columns.value = cols
	selectedColumns.value = props.columns
		? columns.value.filter((c) => props.columns?.column_names.includes(c.name))
		: []
})

const columnSearchQuery = ref('')
const filteredColumns = computed(() => {
	if (!columns.value.length) return []
	if (!columnSearchQuery.value) return columns.value
	return columns.value.filter((column) => {
		return column.name.toLowerCase().includes(columnSearchQuery.value.toLowerCase())
	})
})

const selectedColumns = ref<QueryResultColumn[]>([])
function isSelected(column: QueryResultColumn) {
	return selectedColumns.value.includes(column)
}
function toggleColumn(column: QueryResultColumn) {
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
	emit('select', {
		column_names: selectedColumns.value.map((c) => c.name),
	})
	showDialog.value = false
}
</script>

<template>
	<Dialog
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
			<div class="-mb-5 flex max-h-[20rem] flex-col gap-2 p-0.5">
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
						{{
							areAllSelected
								? `Deselect All (${selectedColumns.length})`
								: `Select All (${selectedColumns.length})`
						}}
					</Button>
				</div>
				<div class="flex flex-col overflow-y-scroll rounded border p-0.5 text-base">
					<template v-for="column in filteredColumns">
						<div
							class="flex h-7 flex-shrink-0 cursor-pointer items-center justify-between rounded px-2 hover:bg-gray-100"
							@click="toggleColumn(column)"
						>
							<div class="flex items-center gap-1.5">
								<DataTypeIcon :columnType="column.type" />
								<span>{{ column.name }}</span>
							</div>
							<component
								class="h-4 w-4"
								stroke-width="1.5"
								:is="isSelected(column) ? CheckSquare : SquareIcon"
								:class="isSelected(column) ? 'text-gray-900' : 'text-gray-600'"
							/>
						</div>
					</template>
				</div>
			</div>
		</template>
	</Dialog>
</template>
