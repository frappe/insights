<script setup>
import { ellipsis, formatNumber } from '@/utils'
import { computed } from 'vue'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const MAX_ROWS = 500
const rows = computed(() => {
	if (!props.data?.length || !props.options.columns?.length) return []
	const resultRows = props.data.map((row) => {
		return props.options.columns.map((column) => row[column])
	})
	if (resultRows.length > MAX_ROWS) {
		return resultRows.slice(0, MAX_ROWS)
	}
	return resultRows
})

function guessColumnValueType(column) {
	const index = props.options.columns.indexOf(column)
	const values = rows.value.map((row) => row[index])
	const isNumber = values.every((value) => !isNaN(value))
	if (isNumber) {
		return 'number'
	}
	return 'string'
}

function total(column) {
	const index = props.options.columns.indexOf(column)
	const values = rows.value.map((row) => parseInt(row[index]))
	const total = values.reduce((a, b) => a + b, 0)
	return formatNumber(Number(total))
}
</script>

<template>
	<div
		v-if="options?.columns?.length || rows?.length"
		class="flex h-full w-full flex-col space-y-2 overflow-hidden rounded px-4 py-2"
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
			<table v-if="props.options.columns">
				<thead class="sticky top-0">
					<tr>
						<td
							v-if="props.options.index"
							class="w-10 whitespace-nowrap border-b bg-white py-1.5 font-medium text-gray-600"
							scope="col"
						>
							#
						</td>
						<td
							v-for="column in props.options.columns"
							class="cursor-pointer whitespace-nowrap border-b bg-white py-1.5 font-medium text-gray-600 hover:text-gray-800"
							scope="col"
						>
							{{ column }}
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in rows" class="border-b">
						<td v-if="props.options.index" class="w-10 whitespace-nowrap bg-white py-2">
							{{ index + 1 }}
						</td>
						<td v-for="cell in row" class="whitespace-nowrap bg-white py-2">
							{{ typeof cell == 'number' ? formatNumber(cell) : ellipsis(cell, 100) }}
						</td>
					</tr>
					<tr v-if="props.options.showTotal" class="border-b font-medium">
						<td
							v-if="props.options.index"
							class="w-10 whitespace-nowrap bg-white px-2.5 py-2 text-gray-600"
						>
							Total
						</td>
						<td v-for="column in props.options.columns">
							{{ guessColumnValueType(column) == 'number' ? total(column) : '' }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>

	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
