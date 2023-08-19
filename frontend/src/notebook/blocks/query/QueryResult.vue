<script setup>
import { formatNumber } from '@/utils'
import settingsStore from '@/stores/settingsStore'
import { LoadingIndicator } from 'frappe-ui'
import { computed, inject } from 'vue'

const settings = settingsStore().settings
const query = inject('query')
const columns = computed(() => query.formattedResults?.[0] || [])
const data = computed(() => query.formattedResults?.slice(1) || [])

const executionTime = computed(() => {
	const rounded = Math.round(query.doc.execution_time * 100) / 100
	return query.doc.execution_time && rounded < 0.01 ? '< 0.01' : rounded
})
const totalRows = computed(() => query.doc.results_row_count - 1)

const query_result_limit = computed(() => formatNumber(parseInt(settings.query_result_limit)))
</script>

<template>
	<div
		v-show="query.formattedResults.length"
		class="flex h-9 w-full flex-shrink-0 items-center space-x-2 px-3 text-base"
	>
		<span class="font-code uppercase text-gray-600"> Results </span>
		<div
			v-if="data.length && executionTime"
			class="flex items-center space-x-1 text-sm font-light text-gray-600"
		>
			<span class="text-sm text-gray-600">
				({{ formatNumber(totalRows) }} rows in {{ executionTime }}s)
			</span>
			<Tooltip
				v-if="totalRows > query.MAX_ROWS"
				:text="`Results are limited to ${query_result_limit} rows. You can change this in the settings.`"
				:hoverDelay="0.1"
				class="flex"
			>
				<FeatherIcon name="info" class="h-3 w-3 cursor-pointer" />
			</Tooltip>
		</div>
	</div>

	<!-- Table -->
	<div
		v-if="query.formattedResults.length"
		class="relative flex flex-1 overflow-scroll py-0 scrollbar-hide"
	>
		<table class="h-full w-full border-separate border-spacing-0 text-sm">
			<thead class="sticky top-0 py-1 text-gray-600">
				<tr class="text-left text-gray-600">
					<th
						v-for="(column, index) in columns"
						:key="index"
						class="whitespace-nowrap border-b border-r bg-gray-100 py-1.5 pl-3 pr-20 font-medium text-gray-700"
					>
						{{ column.label }}
					</th>
					<th
						class="border-b bg-gray-100 py-1.5 pl-3 pr-20 font-medium text-gray-700"
						scope="col"
						width="99%"
					></th>
				</tr>
			</thead>
			<tbody class="pointer-events-none">
				<tr v-for="(row, i) in data" :key="i">
					<td
						v-for="(cell, j) in row"
						:key="j"
						class="overflow-hidden text-ellipsis whitespace-nowrap border-b border-r py-1.5 pl-3 pr-20 text-gray-600"
					>
						{{ typeof cell == 'number' ? formatNumber(cell) : cell }}
					</td>
					<td class="border-b py-2 pl-3 pr-20 text-gray-600" width="99%"></td>
				</tr>
				<tr height="99%">
					<td></td>
				</tr>
			</tbody>
		</table>

		<div
			v-if="query.executing"
			class="absolute inset-0 flex items-center justify-center bg-gray-50/60"
		>
			<LoadingIndicator class="h-4 w-4" />
		</div>
	</div>
</template>
