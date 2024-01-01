<script setup>
import { ellipsis, FIELDTYPES, formatNumber } from '@/utils'
import { Filter } from 'lucide-vue-next'
import { computed, inject } from 'vue'

const query = inject('query')
const resultColumns = computed(() => query.formattedResults?.[0] || [])
const rows = computed(() => query.formattedResults?.slice(1, query.MAX_ROWS) || [])
const numberColumnIndexes = computed(() =>
	query.resultColumns.map((c) => FIELDTYPES.NUMBER.includes(c.type))
)
const isNumberColumn = (index) => numberColumnIndexes.value[index]
const needsExecution = computed(() => query.doc.status == 'Pending Execution')
</script>

<template>
	<div class="relative flex h-full w-full flex-col overflow-hidden">
		<div
			v-if="!query.formattedResults.length"
			class="flex flex-1 items-center justify-center rounded border"
		>
			<div class="flex flex-1 flex-col items-center justify-center gap-2">
				<Filter class="h-10 w-10 text-gray-300" />
				<span class="text-gray-500"> No results found </span>
			</div>
		</div>
		<div
			v-if="needsExecution || query.executing"
			class="absolute top-8 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
		>
			<div class="flex flex-1 flex-col items-center justify-center gap-2">
				<Button
					class="shadow-2xl"
					variant="solid"
					@click="query.execute()"
					:loading="query.executing"
				>
					Execute Query
				</Button>
			</div>
		</div>
		<div
			v-if="query.formattedResults.length"
			class="flex-1 flex-shrink-0 rounded border"
			:class="needsExecution ? 'overflow-hidden' : 'overflow-scroll'"
		>
			<table class="border-separate border-spacing-0">
				<thead class="sticky top-0">
					<tr>
						<th class="border-b bg-gray-100 px-3 py-2 font-normal" scope="col">#</th>
						<th
							v-for="(column, index) in resultColumns"
							:key="index"
							scope="col"
							class="max-w-[15rem] border-b border-r bg-gray-100 px-3 py-2 text-left font-normal"
						>
							<div class="flex justify-between gap-5 overflow-hidden">
								<span class="flex-1 truncate">{{ column.label }}</span>
								<div v-if="$slots.columnActions" class="flex-shrink-0">
									<slot name="columnActions" v-bind="{ column }"></slot>
								</div>
							</div>
						</th>
						<th class="border-b bg-gray-100 px-3 py-2" scope="col" width="99%"></th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, i) in rows" :key="i">
						<td class="border-b border-r px-3 py-2 text-gray-700">{{ i + 1 }}</td>
						<td
							v-for="(cell, j) in row"
							:key="j"
							class="max-w-[15rem] border-b border-r px-3 py-2 text-gray-700"
						>
							<div class="flex w-full">
								<span
									class="w-full truncate"
									:class="isNumberColumn(j) ? 'tnum text-right' : ''"
								>
									{{
										typeof cell == 'number'
											? formatNumber(cell)
											: ellipsis(cell, 100)
									}}
								</span>
							</div>
						</td>
						<td class="border-b px-3 py-2" width="99%"></td>
					</tr>
				</tbody>
			</table>
		</div>
		<div v-if="query.formattedResults.length" class="mt-2">
			<slot name="footer"></slot>
		</div>
	</div>
</template>
