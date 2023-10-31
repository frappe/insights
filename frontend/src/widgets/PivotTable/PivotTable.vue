<script setup>
import { ellipsis, formatNumber } from '@/utils'
import { call } from 'frappe-ui'
import { computed, ref, watchEffect } from 'vue'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const resultColumns = computed(() => Object.keys(props.data[0]))
function createPivotTable(rows, columns, values) {
	const resultRows = props.data.map((row) => {
		return resultColumns.value.map((column) => row[column])
	})
	return call('insights.api.queries.apply_pivot_transform', {
		data: [resultColumns.value, ...resultRows],
		rows: rows.map((row) => row.label),
		columns: columns.map((column) => column.label),
		values: values.map((value) => value.label),
	})
}

const pivotedData = ref([])
watchEffect(async () => {
	if (
		!props.data?.length ||
		!props.options?.rows?.length ||
		!props.options?.columns?.length ||
		!props.options?.values?.length
	)
		return

	pivotedData.value = await createPivotTable(
		props.options.rows,
		props.options.columns,
		props.options.values
	)
})

const columns = computed(() => {
	if (!pivotedData.value?.length) return []
	return pivotedData.value[0]
})
const rows = computed(() => {
	if (!pivotedData.value?.length) return []
	return pivotedData.value.slice(1)
})
function isNumber(value) {
	if (!value) return false
	return !isNaN(value)
}
</script>

<template>
	<div
		v-if="pivotedData?.length"
		class="flex h-full w-full flex-col space-y-2 overflow-hidden rounded"
	>
		<div v-if="props.options.title" class="text-lg font-normal leading-6 text-gray-800">
			{{ props.options.title }}
		</div>
		<div class="relative flex flex-1 flex-col overflow-scroll text-base">
			<div
				v-if="rows.length == 0"
				class="absolute top-0 flex h-full w-full items-center justify-center text-lg text-gray-600"
			>
				<span>No Data</span>
			</div>
			<table v-if="rows.length" class="w-full">
				<thead class="sticky top-0">
					<tr>
						<td
							v-for="column in columns"
							class="cursor-pointer truncate border-b border-r bg-white px-3 py-1.5 pr-4 text-gray-600 hover:text-gray-800"
							scope="col"
						>
							{{ column.label }}
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in rows" :key="index">
						<td
							v-for="cell in row"
							class="truncate border-b border-r bg-white py-2 px-3"
							:class="isNumber(cell) ? 'text-right' : ''"
						>
							{{ isNumber(cell) ? formatNumber(cell) : ellipsis(cell, 100) }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>
