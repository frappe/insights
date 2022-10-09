<template>
	<div ref="resultContainer" class="h-1/2">
		<!-- Result Header -->
		<div class="relative flex h-8 items-center">
			<div class="text-sm tracking-wide text-gray-600">RESULT</div>
			<div class="flex flex-1 items-center justify-center">
				<div
					ref="resizerHandle"
					class="transition-al h-1.5 w-16 cursor-s-resize rounded-full bg-gray-100"
					:class="[isResizing ? 'bg-gray-200' : '']"
				></div>
			</div>
			<div v-if="executionTime" class="text-sm font-light text-gray-500">
				Executed in {{ executionTime }} seconds
			</div>
		</div>
		<!-- Result  -->
		<div class="relative h-[calc(100%-2rem)] w-full">
			<!-- Empty State -->
			<div
				v-if="!needsExecution && formattedResult?.length === 0"
				class="flex h-full w-full items-center justify-center rounded-md border-2 border-dashed border-gray-200 font-light text-gray-400"
			>
				<p>No results found</p>
			</div>
			<!-- Table & Limits -->
			<div
				v-else
				class="flex h-full w-full select-text flex-col-reverse"
				:class="{ 'blur-[2px]': needsExecution }"
			>
				<!-- Limits -->
				<div class="mt-3 flex h-6 w-full flex-shrink-0">
					<LimitsAndOrder />
				</div>
				<!-- Table -->
				<div
					class="relative h-[calc(100%-2.25rem)] w-full overflow-scroll rounded-md bg-gray-50 pt-0 scrollbar-hide"
				>
					<table class="border-separate border-spacing-0 text-sm">
						<thead class="sticky top-0 text-gray-600">
							<tr>
								<th
									v-for="column in columns"
									:key="column.name"
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
						<tbody class="pointer-events-none">
							<tr v-for="(row, i) in formattedResult" :key="i">
								<td
									v-for="(cell, j) in row"
									:key="j"
									class="whitespace-nowrap border-b border-r bg-gray-50 px-3 py-2 text-gray-600"
									:class="{ 'text-right': isNumberColumn[j] }"
								>
									{{ ellipsis(cell, 100) }}
								</td>
								<td
									class="border-b bg-gray-50 px-3 py-2 text-gray-600"
									width="99%"
								></td>
							</tr>
						</tbody>
					</table>
				</div>
			</div>
			<!-- If Pending Execution -->
			<div
				v-if="needsExecution"
				class="absolute top-0 left-0 flex h-full w-full items-center justify-center"
			>
				<Button
					appearance="primary"
					class="!shadow-md"
					@click="query.debouncedRun()"
					:loading="query.run.loading"
					loadingText="Executing..."
				>
					{{ query.run.loading ? '' : 'Execute' }}
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup>
import ColumnHeader from '@/components/Query/Result/ColumnHeader.vue'
import LimitsAndOrder from '@/components/Query/LimitsAndOrder.vue'
import { FIELDTYPES, isEmptyObj, ellipsis } from '@/utils'

import { computed, inject, watch, onMounted, ref } from 'vue'

import useResizer from '@/utils/resizer'

const query = inject('query')

const formattedResult = computed(() => query.results.formattedData)
const needsExecution = computed(() => query.doc?.status === 'Pending Execution')
const columns = computed(() => {
	return isEmptyObj(query.doc.columns) ? query.columns.options : query.doc.columns
})
const isNumberColumn = computed(() => {
	return query.doc.columns.map((c) => FIELDTYPES.NUMBER.includes(c.type))
})

const $notify = inject('$notify')
const executeQuery = async () => {
	query.debouncedRun(null, {
		onError() {
			query.run.loading = false
			$notify({
				appearance: 'error',
				title: 'Error while executing query',
				message: 'Please review the query and try again.',
			})
		},
	})
}
watch(needsExecution, (newVal, oldVal) => newVal && !oldVal && executeQuery(), {
	immediate: true,
})

const executionTime = computed(() => {
	const rounded = Math.round(query.doc.execution_time * 100) / 100
	return query.doc.execution_time && rounded < 0.01 ? '< 0.01' : rounded
})

const isResizing = ref(false)
const resizerHandle = ref(null)
const resultContainer = ref(null)

onMounted(() => {
	useResizer({
		handle: resizerHandle,
		target: resultContainer,
		direction: 'y',
		inverse: true,
		limits: {
			minHeight: 200,
			maxHeight: resultContainer.value.clientHeight,
		},
		start: () => (isResizing.value = true),
		stop: () => (isResizing.value = false),
	})
})
</script>
