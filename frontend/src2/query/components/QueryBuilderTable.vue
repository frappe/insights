<script setup lang="tsx">
import { LoadingIndicator } from 'frappe-ui'
import { computed, inject } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../query'
import QueryBuilderTableColumn from './QueryBuilderTableColumn.vue'
import { RefreshCw } from 'lucide-vue-next'

const query = inject('query') as Query

const columns = computed(() => query.result.columns)
const rows = computed(() => query.result.formattedRows)
const previewRowCount = computed(() => query.result.rows.length.toLocaleString())
const totalRowCount = computed(() =>
	query.result.totalRowCount ? query.result.totalRowCount.toLocaleString() : ''
)
</script>

<template>
	<div class="relative flex w-full flex-1 flex-col overflow-hidden rounded shadow">
		<div
			v-if="query.executing"
			class="absolute top-10 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
		>
			<LoadingIndicator class="h-8 w-8 text-gray-700" />
		</div>

		<DataTable :columns="columns" :rows="rows" :on-export="query.downloadResults">
			<template #column-header="{ column }">
				<QueryBuilderTableColumn :column="column" />
			</template>
			<template #footer-left>
				<div class="tnum flex items-center gap-2 text-sm text-gray-600">
					<span> Showing {{ previewRowCount }} of </span>
					<span v-if="!totalRowCount" class="inline-block">
						<Tooltip text="Load Count">
							<RefreshCw
								v-if="!query.fetchingCount"
								class="h-3.5 w-3.5 cursor-pointer transition-all hover:text-gray-800"
								stroke-width="1.5"
								@click="query.fetchResultCount"
							/>
							<LoadingIndicator v-else class="h-3.5 w-3.5 text-gray-600" />
						</Tooltip>
					</span>
					<span v-else> {{ totalRowCount }} </span>
					rows
				</div>
			</template>
		</DataTable>
	</div>
</template>
