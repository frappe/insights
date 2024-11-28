<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { Play, RefreshCw, Wand2 } from 'lucide-vue-next'
import { computed, inject, ref, watchEffect } from 'vue'
import Code from '../../components/Code.vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../query'
import ContentEditable from '../../components/ContentEditable.vue'
import DataSourceSelector from './source_selector/DataSourceSelector.vue'
import { wheneverChanges } from '../../helpers'
import useDataSourceStore from '../../data_source/data_source'

const query = inject<Query>('query')!
query.autoExecute = false

const operation = query.getSQLOperation()
const data_source = ref(operation ? operation.data_source : '')
const sql = ref(operation ? operation.raw_sql : '')
function execute() {
	query.setSQL({
		raw_sql: sql.value,
		data_source: data_source.value,
	})
}

const columns = computed(() => query.result.columns)
const rows = computed(() => query.result.formattedRows)
const previewRowCount = computed(() => query.result.rows.length.toLocaleString())
const totalRowCount = computed(() =>
	query.result.totalRowCount ? query.result.totalRowCount.toLocaleString() : ''
)

const dataSourceSchema = ref<Record<string, any>>({})
const dataSourceStore = useDataSourceStore()
wheneverChanges(
	data_source,
	() => {
		if (!data_source.value) {
			dataSourceSchema.value = {}
			return
		}
		dataSourceStore.getSchema(data_source.value).then((schema: any) => {
			dataSourceSchema.value = schema
		})
	},
	{ immediate: true }
)
const completions = computed(() => {
	if (!Object.keys(dataSourceSchema.value).length)
		return {
			schema: {},
			tables: [],
		}

	const schema: Record<string, any> = {}
	Object.entries(dataSourceSchema.value).forEach(([table, tableData]) => {
		schema[table] = tableData.columns.map((column: any) => ({
			label: column.label,
			detail: column.label,
		}))
	})

	const tables = Object.entries(dataSourceSchema.value).map(([table, tableData]) => ({
		label: table,
		detail: tableData.label,
	}))

	return {
		schema,
		tables,
	}
})
</script>

<template>
	<div class="flex flex-1 flex-col gap-4 overflow-hidden p-4">
		<div class="relative flex h-[55%] w-full flex-col rounded border">
			<div class="flex flex-shrink-0 items-center gap-1 border-b p-1">
				<DataSourceSelector v-model="data_source" placeholder="Select a data source" />
				<ContentEditable
					class="flex h-7 cursor-text items-center justify-center rounded bg-white px-2 text-base text-gray-800 focus-visible:ring-1 focus-visible:ring-gray-600"
					v-model="query.doc.title"
					placeholder="Untitled Dashboard"
				></ContentEditable>
			</div>
			<div class="flex-1 overflow-hidden">
				<Code
					:key="completions.tables.length"
					v-model="sql"
					language="sql"
					:schema="completions.schema"
					:tables="completions.tables"
				/>
			</div>
			<div class="flex flex-shrink-0 gap-1 border-t p-1">
				<Button @click="execute" label="Execute">
					<template #prefix>
						<Play class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
				<Button @click="" label="Format">
					<template #prefix>
						<Wand2 class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</div>
		<div
			v-show="query.result.executedSQL"
			class="tnum flex flex-shrink-0 items-center gap-2 text-sm text-gray-600"
		>
			<div class="h-2 w-2 rounded-full bg-green-500"></div>
			<div>
				<span v-if="query.result.timeTaken == -1"> Fetched from cache </span>
				<span v-else> Fetched in {{ query.result.timeTaken }}s </span>
				<span> {{ useTimeAgo(query.result.lastExecutedAt).value }} </span>
			</div>
		</div>
		<div class="relative flex w-full flex-1 flex-col overflow-hidden rounded border">
			<div
				v-if="query.executing"
				class="absolute top-10 z-10 flex w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>

			<DataTable :columns="columns" :rows="rows" :on-export="query.downloadResults">
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
	</div>
</template>
