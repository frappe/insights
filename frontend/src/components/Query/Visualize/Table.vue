<template>
	<div class="flex w-full flex-1 flex-col space-y-2 overflow-hidden rounded-md border p-3">
		<div v-if="props.title" class="h-5 flex-shrink-0 text-base font-medium text-gray-600">
			{{ props.title }}
		</div>
		<div class="relative flex flex-1 flex-col overflow-scroll text-base scrollbar-hide">
			<div
				v-if="props.rows.length == 0"
				class="absolute top-0 flex h-full w-full items-center justify-center text-lg font-light text-gray-500"
			>
				<span>No Data</span>
			</div>
			<table v-if="props.columns">
				<thead class="sticky top-0">
					<tr>
						<td
							v-if="props.options.index"
							class="w-10 whitespace-nowrap bg-gray-100 px-2.5 py-1.5 font-medium text-gray-600 first:rounded-l-md last:rounded-r-md"
							scope="col"
						>
							#
						</td>
						<td
							v-for="column in props.columns"
							class="whitespace-nowrap bg-gray-100 px-2.5 py-1.5 font-medium text-gray-600 first:rounded-l-md last:rounded-r-md"
							scope="col"
						>
							{{ column }}
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in props.rows" class="border-b">
						<td
							v-if="props.options.index"
							class="w-10 whitespace-nowrap bg-white px-2.5 py-2 font-light text-gray-600"
						>
							{{ index + 1 }}
						</td>
						<td
							v-for="cell in row"
							class="whitespace-nowrap bg-white px-2.5 py-2 font-light text-gray-600"
						>
							{{
								typeof cell == 'number'
									? cell.toLocaleString()
									: ellipsis(cell, 100)
							}}
						</td>
					</tr>
					<tr v-if="props.options.showTotal" class="border-b font-medium">
						<td
							v-if="props.options.index"
							class="w-10 whitespace-nowrap bg-white px-2.5 py-2 text-gray-600"
						>
							Total
						</td>
						<td v-for="column in props.columns">
							{{ guessColumnValueType(column) == 'number' ? total(column) : '' }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script setup>
import { ellipsis } from '@/utils'

const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	columns: {
		type: Array,
	},
	rows: {
		type: Array,
	},
	options: {
		type: Object,
		default: {},
	},
})

function guessColumnValueType(column) {
	const index = props.columns.indexOf(column)
	const values = props.rows.map((row) => row[index])
	const isNumber = values.every((value) => !isNaN(value))
	if (isNumber) {
		return 'number'
	}
	return 'string'
}

function total(column) {
	const index = props.columns.indexOf(column)
	const values = props.rows.map((row) => parseInt(row[index]))
	const total = values.reduce((a, b) => a + b, 0)
	return Number(total).toLocaleString()
}
</script>
