<template>
	<div class="h-full w-full rounded-md border px-2 py-3">
		<div class="mx-auto h-full max-w-full">
			<div v-if="props.title" class="h-5 text-base font-semibold text-gray-600">
				{{ props.title }}
			</div>
			<div
				class="relative mt-2 flex w-full flex-col overflow-scroll text-base scrollbar-hide"
				:class="[props.title ? 'h-[calc(100%-1.75rem)]' : 'h-[calc(100%-1rem)]']"
			>
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
				<div
					v-if="props.rows.length == 0"
					class="mt-2 flex h-[calc(100%-1.5rem)] w-full items-center justify-center text-lg font-light text-gray-500"
				>
					No Data
				</div>
			</div>
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
