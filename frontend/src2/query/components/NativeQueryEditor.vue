<script setup lang="ts">
import { Wand2 } from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import { useShortcut } from '../../composables/useShortcut'
import useDataSourceStore from '../../data_source/data_source'
import { wheneverChanges } from '../../helpers'
import { createToast } from '../../helpers/toasts'
import { __ } from '../../translation'
import { Query } from '../query'
import QueryExecutionStatus from './QueryExecutionStatus.vue'
import QueryToolbar from './QueryToolbar.vue'
import QueryDataTable from './QueryDataTable.vue'
import QueryInfo from './QueryInfo.vue'
import SchemaExplorer from './SchemaExplorer.vue'
import DataSourceSelector from './source_selector/DataSourceSelector.vue'

const query = inject<Query>('query')!
query.autoExecute = false
query.execute()

const operation = query.getSQLOperation()
const data_source = ref(operation ? operation.data_source : '')
const sql = ref(operation ? operation.raw_sql : '')

function execute(force: boolean = false) {
	if (!data_source.value) {
		createToast({
			title: __('Please select a data source first'),
			variant: 'error',
		})
		return
	}
	query.setSQL(
		{
			raw_sql: sql.value,
			data_source: data_source.value,
		},
		force,
	)
}

const formatting = ref(false)
async function format() {
	if (!sql.value.trim() || formatting.value) return

	formatting.value = true
	try {
		sql.value = await query.formatSQL({
			raw_sql: sql.value,
			data_source: data_source.value,
		})
	} catch (error) {
		createToast({
			title: __('Failed to format SQL'),
			variant: 'error',
		})
	} finally {
		formatting.value = false
	}
}

const extraActions = () => [
	{
		label: __('Format SQL'),
		icon: h(Wand2, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => format(),
	},
]

const codeEditor = ref<InstanceType<typeof Code> | null>(null)
function insertTextIntoEditor(text: string) {
	if (codeEditor.value) {
		codeEditor.value.insertText(text)
	}
}

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
	{ immediate: true },
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
			detail: column.type,
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

useShortcut('Meta+e', () => {
	execute(true)
})
</script>

<template>
	<div class="flex flex-1 overflow-hidden">
		<div class="relative flex h-full flex-1 flex-col gap-3 overflow-hidden p-4">
			<!-- Toolbar -->
			<QueryToolbar :on-execute="() => execute(true)" :extra-actions="extraActions">
				<DataSourceSelector v-model="data_source" placeholder="Select a data source" />
			</QueryToolbar>

			<!-- SQL Editor -->
			<div class="relative flex flex-1 flex-col overflow-hidden rounded border">
				<Code
					ref="codeEditor"
					:key="completions.tables.length"
					v-model="sql"
					language="sql"
					:schema="completions.schema"
					:tables="completions.tables"
				/>
			</div>

			<!-- Results Table -->
			<QueryExecutionStatus />
			<div class="relative flex h-[45%] w-full flex-col overflow-hidden rounded border">
				<QueryDataTable :query="query" :enable-alerts="true" />
			</div>
		</div>

		<!-- Right Sidebar -->
		<div class="relative flex h-full w-[19rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
			<QueryInfo />

			<!-- Schema Explorer -->
			<SchemaExplorer :schema="dataSourceSchema" @insert-text="insertTextIntoEditor" />
		</div>
	</div>
</template>
