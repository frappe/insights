<script setup lang="tsx">
import { LoadingIndicator } from 'frappe-ui'
import { computed, inject } from 'vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../query'
import QueryBuilderTableColumn from './QueryBuilderTableColumn.vue'

const query = inject('query') as Query

const columns = computed(() => query.result.columns)
const rows = computed(() => query.result.formattedRows)
const previewRowCount = computed(() => query.result.rows.length.toLocaleString())
const totalRowCount = computed(() => query.result.totalRowCount.toLocaleString())
</script>

<template>
	<div class="relative flex w-full flex-1 flex-col overflow-hidden bg-white">
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
				<p class="tnum p-1 text-sm text-gray-600">
					Showing {{ previewRowCount }} of {{ totalRowCount }} rows
				</p>
			</template>
		</DataTable>
	</div>
</template>
