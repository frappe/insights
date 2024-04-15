<script setup lang="tsx">
import { LoadingIndicator } from 'frappe-ui'
import { Table2Icon } from 'lucide-vue-next'
import { computed, inject } from 'vue'
import QueryBuilderTableColumn from './QueryBuilderTableColumn.vue'
import { Query } from './useQuery'

const query = inject('query') as Query

const columns = computed(() => query.result.columns)
const rows = computed(() => query.result.rows)
const previewRowCount = computed(() => query.result.rows.length.toLocaleString())
const totalRowCount = computed(() => query.result.totalRowCount.toLocaleString())
</script>

<template>
	<div class="relative flex w-full flex-1 flex-col overflow-hidden">
		<div
			v-if="query.executing"
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
								:class="isNaN(value) ? '' : 'text-right'"
							>
								{{ value }}
							</td>
						</tr>
						<tr height="99%" class="border-b"></tr>
					</tbody>
				</table>
			</div>
			<div class="flex flex-shrink-0 items-center gap-3 border-t p-2">
				<p class="tnum text-sm text-gray-600">
					Showing {{ previewRowCount }} of {{ totalRowCount }} rows
				</p>
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
