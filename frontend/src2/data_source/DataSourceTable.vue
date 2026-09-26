<script setup lang="ts">
import { Breadcrumbs, Button, LoadingIndicator } from 'frappe-ui'
import { Lock } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import ScopeMark from '../charts/components/ScopeMark.vue'
import DataTable from '../components/DataTable.vue'
import ResultPane from '../components/result_pane/ResultPane.vue'
import { refusalDetail, refusalHeadline } from '../not_permitted'
import { emptyResult } from '../query/helpers'
import type { ResultTable } from '../query/result_table'
import useTableStore, { DataSourceTablePreview } from './tables'
import { __ } from '../translation'

const props = defineProps<{ data_source: string; table_name: string }>()

const tableStore = useTableStore()
const table = ref<DataSourceTablePreview>()
// The preview did not load. This is separate from Not Permitted. A connection
// that is down, a table dropped at the source, or a table that is not a doctype
// lands here, and each one is worth a retry.
const failed = ref(false)

function load() {
	failed.value = false
	tableStore.fetchTable(props.data_source, props.table_name).then((t) => {
		table.value = t
		failed.value = !t
	})
}
load()

// A preview arrives whole in one response and has no query behind it,
// so it is a `ResultTable` with only the rows filled in.
const result = computed<ResultTable>(() => {
	const rows = table.value?.rows || []
	return {
		ready: Boolean(table.value),
		executing: tableStore.fetchingTable,
		result: {
			...emptyResult(),
			columns: table.value?.columns || [],
			rows,
			formattedRows: rows,
			totalRowCount: rows.length,
		},
	}
})

// Not Permitted: the caller may not read this table, so nothing ran. It is not
// a failure, so there is no retry. An empty grid would look like an empty table.
const refused = computed(() => table.value?.not_permitted?.doctypes)

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
		<div
			v-if="refused"
			class="flex h-full w-full flex-col items-center justify-center gap-2 rounded-4 bg-surface-gray-1"
		>
			<div class="flex items-center gap-1.5 text-p-base text-ink-gray-7">
				<Lock class="h-3.5 w-3.5 shrink-0 text-ink-gray-5" stroke-width="1.5" />
				<span>{{ refusalHeadline() }}</span>
			</div>
			<p class="text-p-sm text-ink-gray-5">
				{{ refusalDetail(refused, __('You do not have access to this table')) }}
			</p>
		</div>

		<div
			v-else-if="failed"
			class="flex h-full w-full flex-col items-center justify-center gap-2 rounded-4 bg-surface-gray-1"
		>
			<p class="text-p-base text-ink-gray-7">{{ __('Could not load this table') }}</p>
			<Button variant="outline" :label="__('Retry')" @click="load" />
		</div>

		<div v-else-if="table" class="flex flex-1 flex-col overflow-hidden p-4">
			<ResultPane :query="result">
				<!-- A preview has no total and no timing, so the header says what it is. -->
				<template #header-left>
					<span class="flex items-center gap-1 text-sm text-ink-gray-5">
						{{ __('First 100 rows') }}
						<ScopeMark
							:applied="table.user_permissions"
							:narrowed="table.narrowed_by_permissions"
						/>
					</span>
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
			<div class="text-lg text-ink-gray-5">{{ __('Loading table data...') }}</div>
		</div>
	</div>
</template>
