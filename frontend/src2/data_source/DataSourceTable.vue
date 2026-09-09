<script setup lang="ts">
import { Breadcrumbs, LoadingIndicator } from 'frappe-ui'
import { computed, ref, watchEffect } from 'vue'
import DataTable from '../components/DataTable.vue'
import ResultPane from '../components/result_pane/ResultPane.vue'
import { EMPTY_RESULT } from '../query/helpers'
import type { ResultTable } from '../query/result_table'
import useTableStore, { DataSourceTablePreview } from './tables'
import { __ } from '../translation'

const props = defineProps<{ data_source: string; table_name: string }>()

const tableStore = useTableStore()
const table = ref<DataSourceTablePreview>()
tableStore.fetchTable(props.data_source, props.table_name).then((t) => {
	table.value = t
})

// A preview arrives whole, in one response, and carries none of the authoring
// half — so it is a `ResultTable` with only the rows filled in, and the pane
// draws only what it was handed.
const result = computed<ResultTable>(() => {
	const rows = table.value?.rows || []
	return {
		ready: Boolean(table.value),
		executing: tableStore.fetchingTable,
		result: {
			...EMPTY_RESULT,
			columns: table.value?.columns || [],
			rows,
			formattedRows: rows,
			totalRowCount: rows.length,
		},
	}
})

watchEffect(() => {
	document.title = `Tables | ${props.table_name}`
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs
			:items="[
				{ label: __('Data Sources'), route: '/data-source' },
				{ label: props.data_source, route: `/data-source/${props.data_source}` },
				{
					label: props.table_name,
					route: `/data-source/${props.data_source}/${props.table_name}`,
				},
			]"
		/>
		<div class="flex items-center gap-2"></div>
	</header>

	<div class="flex flex-1 flex-col overflow-hidden bg-surface-base">
		<div v-if="table" class="flex flex-1 flex-col overflow-hidden p-4">
			<ResultPane :query="result">
				<!-- A preview has no total and no timing, so it says what it is
				     instead of what the status line could not report. -->
				<template #header-left>
					<span class="text-sm text-ink-gray-5">{{ __('First 100 rows') }}</span>
				</template>

				<template #grid="{ rows }">
					<DataTable :columns="table.columns" :rows="rows" />
				</template>
			</ResultPane>
		</div>
		<div
			v-else
			class="flex h-full w-full flex-col items-center justify-center rounded-4 bg-surface-gray-1"
		>
			<LoadingIndicator class="mb-2 w-8 text-ink-gray-4" />
			<div class="text-lg text-ink-gray-5">Loading table data...</div>
		</div>
	</div>
</template>
