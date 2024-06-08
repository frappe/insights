<script setup lang="ts">
import { computed, ref } from 'vue'
import { getCachedQuery } from '../query/query'
import { DashboardFilterColumn, WorkbookChart, WorkbookQuery } from '../workbook/workbook'

const showDialog = defineModel()
const props = defineProps<{ charts: WorkbookChart[]; queries: WorkbookQuery[] }>()
const emit = defineEmits({
	select: (filter: DashboardFilterColumn) => true,
})

const columnOptions = computed(() => {
	return props.queries.map((q) => {
		const query = getCachedQuery(q.name)
		const resultColumns = query?.result.columns || []
		return {
			group: q.title || q.name,
			items: resultColumns.map((c) => ({
				label: c.name,
				value: c.name,
				description: c.type,
				query: q.name,
				name: c.name,
				type: c.type,
			})),
		}
	})
})

const selectedColumn = ref<DashboardFilterColumn>({
	query: '',
	name: '',
	type: 'String',
})

const linkedChartsCount = computed(() => {
	if (!selectedColumn.value.query) return 0
	return props.charts.filter((c) => c.query === selectedColumn.value.query).length
})

function confirmSelection() {
	emit('select', {
		query: selectedColumn.value.query,
		name: selectedColumn.value.name,
		type: selectedColumn.value.type,
	})
	showDialog.value = false
}
</script>

<template>
	<Dialog
		v-model="showDialog"
		:options="{
			size: 'sm',
			title: 'Add Filter',
			actions: [
				{
					label: 'Add',
					variant: 'solid',
					disabled: selectedColumn.name === '',
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
			<div class="-mb-5 flex flex-col gap-2 p-0.5">
				<Autocomplete
					label="Select Column"
					v-model="selectedColumn"
					:options="columnOptions"
				/>
				<span v-if="linkedChartsCount > 0" class="text-sm text-gray-500">
					{{ linkedChartsCount }} chart(s) will be filtered by this column
				</span>
			</div>
		</template>
	</Dialog>
</template>
