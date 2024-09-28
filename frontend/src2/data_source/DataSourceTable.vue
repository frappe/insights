<script setup lang="ts">
import { Breadcrumbs, LoadingIndicator } from 'frappe-ui'
import { ref, watchEffect } from 'vue'
import DataTable from '../components/DataTable.vue'
import useTableStore, { DataSourceTablePreview } from './tables'

const props = defineProps<{ data_source: string; table_name: string }>()

const tableStore = useTableStore()
const table = ref<DataSourceTablePreview>()
tableStore.fetchTable(props.data_source, props.table_name).then((t) => {
	table.value = t
})

watchEffect(() => {
	document.title = `Tables | ${props.table_name}`
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs
			:items="[
				{ label: 'Data Sources', route: '/data-source' },
				{ label: props.data_source, route: `/data-source/${props.data_source}` },
				{
					label: props.table_name,
					route: `/data-source/${props.data_source}/${props.table_name}`,
				},
			]"
		/>
		<div class="flex items-center gap-2"></div>
	</header>

	<div class="flex flex-1 flex-col overflow-hidden bg-white">
		<div v-if="table" class="flex flex-1 flex-col overflow-hidden">
			<div class="flex flex-1 overflow-auto">
				<DataTable
					:loading="tableStore.fetchingTable"
					:columns="table.columns"
					:rows="table.rows"
				>
					<template #footer>
						<div class="flex flex-shrink-0 items-center gap-3 border-t p-2">
							<p class="tnum text-sm text-gray-600">
								Showing 100 rows from {{ table.table_name }} table
							</p>
						</div>
					</template>
				</DataTable>
			</div>
		</div>
		<div
			v-else
			class="flex h-full w-full flex-col items-center justify-center rounded bg-gray-50"
		>
			<LoadingIndicator class="mb-2 w-8 text-gray-500" />
			<div class="text-lg text-gray-600">Loading table data...</div>
		</div>
	</div>
</template>
