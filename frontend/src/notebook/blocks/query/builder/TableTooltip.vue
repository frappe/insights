<script setup>
import useDataSourceTable from '@/datasource/useDataSourceTable'
import { computed } from 'vue'

const props = defineProps({ data_source: String, table: String })

if (!props.data_source || !props.table) {
	console.error('TableTooltip: data_source and table are required')
}

const table = await useDataSourceTable({
	data_source: props.data_source,
	table: props.table,
})
const tablePreview = computed(() => {
	if (!table.doc) return
	return {
		label: table.doc.label,
		row_count: table.doc.meta?.row_count || 0,
		columns: table.columns.map(({ label, type }) => ({ label, type })),
	}
})
</script>
<template>
	<div
		v-if="tablePreview"
		class="flex w-64 flex-col divide-y divide-gray-400 rounded border bg-gray-800 px-2.5 py-2 text-base shadow-lg"
	>
		<div class="flex items-center justify-between pb-2">
			<div class="font-medium text-gray-100">
				{{ tablePreview.label }}
				<span class="text-sm text-gray-500">
					{{ ' ' }} ({{ tablePreview.columns.length }} columns)
				</span>
			</div>

			<div class="text-sm text-gray-500">{{ tablePreview.row_count }} rows</div>
		</div>
		<div class="pt-2 text-sm text-gray-500">
			<div
				v-for="column in tablePreview.columns.slice(0, 10)"
				class="flex items-center justify-between py-1"
			>
				<div class="text-sm text-gray-100">{{ column.label }}</div>
				<div class="text-sm">{{ column.type }}</div>
			</div>
		</div>
	</div>
</template>
