<script setup lang="tsx">
import { getFormattedResult } from '@/utils/query/results'
import { convertResultToObjects } from '@/widgets/useChartData'
import { LoadingIndicator } from 'frappe-ui'
import { ChevronLeft, ChevronRight, Table2Icon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import QueryBuilderTableColumn from './QueryBuilderTableColumn.vue'
import { QueryPipeline } from './useQueryPipeline'

const queryPipeline = inject('queryPipeline') as QueryPipeline

const columns = computed(() => queryPipeline.results.columns)
const rows = computed(() => {
	return convertResultToObjects(
		getFormattedResult([queryPipeline.results.columns, ...queryPipeline.results.rows])
	)
})

const pageLength = ref(100)
const currPage = ref(1)
const pageStart = computed(() => (currPage.value - 1) * pageLength.value + 1)
const pageEnd = computed(() => {
	const end = currPage.value * pageLength.value
	return end > rows.value.length ? rows.value.length : end
})
const totalRows = computed(() => rows.value.length)
const showPagination = computed(() => rows.value?.length && totalRows.value > pageLength.value)

const hasPrevPage = computed(() => currPage.value === 1)
const hasNextPage = computed(() => pageEnd.value < totalRows.value)

const prevPage = () => {
	if (hasPrevPage.value) return
	currPage.value--
}
const nextPage = () => {
	if (hasNextPage.value) return
	currPage.value++
}
</script>

<template>
	<div class="relative flex w-full flex-1 flex-col overflow-hidden">
		<div
			v-if="queryPipeline.executing"
			class="absolute top-10 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
		>
			<LoadingIndicator class="h-8 w-8 text-gray-700" />
		</div>

		<template v-if="columns?.length || rows?.length">
			<div class="flex w-full flex-1 overflow-y-auto font-mono text-base">
				<table class="border-separate border-spacing-0">
					<thead class="sticky top-0 bg-white">
						<tr>
							<td class="border-b border-r px-3"></td>
							<td
								v-for="(column, idx) in columns"
								:key="idx"
								class="border-b border-r"
							>
								<QueryBuilderTableColumn :column="column" />
							</td>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(row, idx) in rows" :key="idx">
							<td class="border-b border-r px-3">{{ idx + 1 }}</td>
							<td
								v-for="(value, idx2) in Object.values(row)"
								:key="idx2"
								class="truncate border-b border-r py-2 px-3 text-gray-800"
							>
								{{ value }}
							</td>
						</tr>
						<tr height="99%" class="border-b"></tr>
					</tbody>
				</table>
			</div>
			<div
				v-if="showPagination"
				class="flex flex-shrink-0 items-center justify-end gap-3 p-1"
			>
				<p class="tnum text-sm text-gray-600">
					{{ pageStart }} - {{ pageEnd }} of {{ totalRows }} rows
				</p>
				<div class="flex gap-2">
					<Button variant="ghost" @click="prevPage" :disabled="hasPrevPage">
						<ChevronLeft class="h-4 w-4 text-gray-600" />
					</Button>
					<Button variant="ghost" @click="nextPage" :disabled="hasNextPage">
						<ChevronRight class="h-4 w-4 text-gray-600" />
					</Button>
				</div>
			</div>
		</template>

		<div v-else class="flex h-full w-full items-center justify-center">
			<div class="flex flex-col items-center gap-2">
				<Table2Icon class="h-16 w-16 text-gray-300" stroke-width="1.5" />
				<p class="text-center text-gray-500">
					No data to display. <br />
					Start by selecting a data source and adding operations.
				</p>
			</div>
		</div>
	</div>
</template>
