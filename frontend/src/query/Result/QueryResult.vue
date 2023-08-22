<template>
	<div
		ref="resultContainer"
		class="flex h-full w-full flex-shrink-0 flex-col overflow-hidden bg-white p-2"
	>
		<!-- Result Header -->
		<div class="relative flex h-9 flex-shrink-0 items-center justify-between">
			<div class="flex space-x-1">
				<div class="text-sm tracking-wide text-gray-600">RESULT</div>
				<div
					v-if="executionTime"
					class="flex items-center space-x-1 text-sm font-light text-gray-600"
				>
					<span class="text-sm text-gray-600">
						({{ formatNumber(totalRows) }} rows in {{ executionTime }}s)
					</span>
					<Tooltip
						v-if="totalRows > query.results.MAX_ROWS"
						:text="`Results are limited to ${query_result_limit} rows. You can change this in the settings.`"
						:hoverDelay="0.1"
						class="flex"
					>
						<FeatherIcon name="info" class="h-3 w-3 cursor-pointer" />
					</Tooltip>
				</div>
			</div>
			<LimitsAndOrder v-if="!query.doc.is_assisted_query" class="-mt-1" />
		</div>
		<!-- Result  -->
		<div class="relative flex flex-1 overflow-hidden">
			<!-- Empty State -->
			<div
				v-if="!needsExecution && formattedResult?.length === 0"
				class="flex h-full w-full items-center justify-center rounded border-2 border-dashed border-gray-200 font-light text-gray-500"
			>
				<p>No results found</p>
			</div>
			<div v-else class="relative flex flex-1 select-text flex-col-reverse overflow-hidden">
				<div class="flex-1 overflow-scroll rounded bg-gray-50 pt-0">
					<table class="border-separate border-spacing-0 text-sm">
						<thead class="sticky top-0 text-gray-600">
							<tr>
								<th
									v-for="(column, index) in columns"
									:key="index"
									class="whitespace-nowrap border-b border-r bg-gray-100 px-3 py-1.5 font-medium text-gray-700"
									scope="col"
								>
									<ColumnHeader :column="column" :query="query" />
								</th>
								<th
									class="border-b bg-gray-100 px-3 py-1.5 font-medium text-gray-700"
									scope="col"
									width="99%"
								></th>
							</tr>
						</thead>
						<tbody
							class="pointer-events-none"
							:class="{ 'blur-[2px]': needsExecution }"
						>
							<tr v-for="(row, i) in formattedResult" :key="i">
								<td
									v-for="(cell, j) in row"
									:key="j"
									class="whitespace-nowrap border-b border-r bg-gray-50 px-3 py-2 text-gray-600"
									:class="{ 'text-right': isNumberColumn[j] }"
								>
									{{
										typeof cell == 'number'
											? formatNumber(cell)
											: ellipsis(cell, 100)
									}}
								</td>
								<td
									class="border-b bg-gray-50 px-3 py-2 text-gray-600"
									width="99%"
								></td>
							</tr>
						</tbody>
					</table>

					<!-- If Pending Execution -->
					<div
						v-if="query.run.loading || needsExecution"
						class="absolute left-0 top-0 flex h-full w-full items-center justify-center"
					>
						<Button
							variant="solid"
							class="!rounded bg-gray-900 text-gray-50 !shadow-md hover:bg-gray-800"
							@click="query.execute()"
							:loading="query.run.loading"
							loadingText="Executing..."
						>
							{{ query.run.loading ? '' : 'Execute' }}
						</Button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import LimitsAndOrder from '@/query/LimitsAndOrder.vue'
import ColumnHeader from '@/query/Result/ColumnHeader.vue'
import settingsStore from '@/stores/settingsStore'
import { ellipsis, FIELDTYPES, formatNumber } from '@/utils'

const settings = settingsStore().settings

import { computed, inject, watch } from 'vue'

const query = inject('query')

const query_result_limit = computed(() => formatNumber(parseInt(settings.query_result_limit)))
const formattedResult = computed(() => query.results.formattedResult.slice(1))
const needsExecution = computed(() => query.doc?.status === 'Pending Execution')
const columns = computed(() => {
	return query.results.formattedResult[0]
})
const isNumberColumn = computed(() => {
	return query.resultColumns.map((c) => FIELDTYPES.NUMBER.includes(c.type))
})

if (settings.auto_execute_query) {
	watch(needsExecution, (newVal, oldVal) => newVal && !oldVal && query.execute())
}

const executionTime = computed(() => {
	const rounded = Math.round(query.doc.execution_time * 100) / 100
	return query.doc.execution_time && rounded < 0.01 ? '< 0.01' : rounded
})

const totalRows = computed(() => {
	return query.doc.results_row_count - 1
})
</script>
