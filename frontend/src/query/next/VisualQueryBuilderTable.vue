<script setup lang="ts">
import { getFormattedResult } from '@/utils/query/results'
import { convertResultToObjects } from '@/widgets/useChartData'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, inject } from 'vue'
import { QueryPipeline } from './useQueryPipeline'
import { LoadingIndicator } from 'frappe-ui'

const queryPipeline = inject('queryPipeline') as QueryPipeline

const columns = computed(() => queryPipeline.results.value?.[0])
const data = computed(() => {
	return convertResultToObjects(getFormattedResult(queryPipeline.results.value))
})
</script>

<template>
	<div class="relative flex w-full flex-1 flex-col overflow-hidden">
		<div
			v-if="queryPipeline.executing.value"
			class="absolute top-10 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
		>
			<LoadingIndicator class="h-8 w-8 text-gray-700" />
		</div>
		<div class="flex items-center justify-between border-b py-1 px-3">
			<p class="text-sm uppercase">Preview</p>
			<div class="invisible -mr-2 flex gap-2">
				<Button></Button>
			</div>
		</div>
		<div class="w-full flex-1 overflow-y-auto text-base">
			<table v-if="data?.length" class="border-separate border-spacing-0">
				<thead class="sticky top-0 bg-white font-medium">
					<tr>
						<td class="border-b border-r px-2 text-gray-800">#</td>
						<td
							v-for="col in columns"
							:key="col.label"
							class="min-w-[6rem] border-b border-r text-gray-800"
						>
							<div class="cursor-pointer truncate py-1.5 px-3 font-mono">
								{{ col.label }}
							</div>
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in data" :key="index">
						<td class="border-b border-r px-2 text-gray-800">{{ index + 1 }}</td>
						<td
							v-for="(cell, index2) in Object.values(row)"
							:key="index2"
							class="min-w-[6rem] truncate border-b border-r py-2 px-3 text-gray-700"
						>
							{{ cell }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
		<div class="flex flex-shrink-0 items-center justify-end gap-3 border-t p-1">
			<p class="tnum text-sm text-gray-600">{{ 1 }} - {{ 10 }} of {{ 2124 }} rows</p>
			<div class="flex gap-2">
				<Button variant="ghost">
					<ChevronLeft class="h-4 w-4 text-gray-600" />
				</Button>
				<Button variant="ghost">
					<ChevronRight class="h-4 w-4 text-gray-600" />
				</Button>
			</div>
		</div>
	</div>
</template>
