<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { MoreHorizontal, Play, Wand2 } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import ContentEditable from '../../components/ContentEditable.vue'
import useDataSourceStore from '../../data_source/data_source'
import { wheneverChanges } from '../../helpers'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { Query } from '../query'
import useSettings from '../../settings/settings'
import QueryDataTable from './QueryDataTable.vue'
import DataSourceSelector from './source_selector/DataSourceSelector.vue'
import { createToast } from '../../helpers/toasts'
import SchemaExplorer from './SchemaExplorer.vue'
import { Switch } from 'frappe-ui'

const query = inject<Query>('query')!
query.autoExecute = false
query.execute()

const settings = useSettings()
function toggleDataStore(enable: boolean) {
	const title = enable ? 'Enable Data Store' : 'Disable Data Store'
	const message = enable
		? 'Enabling data store use the cached table data for faster queries, but may not be up-to-date. It will also allow you to combine data from multiple sources. Cached data is updated every day.'
		: 'Disabling data store will use the live connection to the database for queries. This will ensure that you are always querying the most up-to-date data but may be slower.'

	confirmDialog({
		title,
		message,
		onSuccess() {
			query.doc.use_live_connection = !enable
		},
	})
}

const operation = query.getSQLOperation()
const data_source = ref(operation ? operation.data_source : '')
const sql = ref(operation ? operation.raw_sql : '')
function execute(force: boolean = false) {
	if (!data_source.value) {
		createToast({
			title: 'Please select a data source first',
			variant: 'error',
		})
		return
	}
	query.setSQL(
		{
			raw_sql: sql.value,
			data_source: data_source.value,
		},
		force
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
			title: 'Failed to format SQL',
			variant: 'error',
		})
	} finally {
		formatting.value = false
	}
}

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
</script>

<template>
	<div class="flex flex-1 gap-4 overflow-hidden p-4">
		<div class="flex flex-1 flex-col gap-4 overflow-hidden">
			<div class="relative flex h-[55%] w-full flex-col rounded border">
				<div class="flex flex-shrink-0 items-center border-b h-10 px-3 gap-4 bg-white">
					<div class="flex-shrink-0">
						<DataSourceSelector
							v-model="data_source"
							placeholder="Select a data source"
							class="!w-48"
						/>
					</div>

					<div class="flex-1 flex justify-center">
						<ContentEditable
							class="w-fit min-w-[12rem] h-8 cursor-text rounded-md bg-gray-50/50 px-4 text-sm font-medium text-gray-700 text-center flex items-center justify-center transition-colors hover:bg-gray-50 focus-visible:ring-1 focus-visible:ring-gray-300"
							v-model="query.doc.title"
							placeholder="new query"
						></ContentEditable>
					</div>

					<div
						v-if="settings.doc.enable_data_store"
						class="flex flex-shrink-0 items-center gap-3"
					>
						<span class="text-xs text-gray-600"> Enable Data Store </span>
						<Switch
							:modelValue="!query.doc.use_live_connection"
							@update:modelValue="toggleDataStore"
							size="sm"
						/>
					</div>
				</div>
				<div class="flex-1 overflow-hidden">
					<Code
						ref="codeEditor"
						:key="completions.tables.length"
						v-model="sql"
						language="sql"
						:schema="completions.schema"
						:tables="completions.tables"
					/>
				</div>
				<div class="flex flex-shrink-0 gap-1 border-t p-1">
					<Button @click="execute(true)" label="Execute">
						<template #prefix>
							<Play class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<!-- <Dropdown
					:button="{ icon: MoreHorizontal }"
					:options="[
						{
							label: 'Format SQL',
							icon: Wand2,
							onClick: () => format(),
						},
					]"
				/> -->
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
				<QueryDataTable :query="query" :enable-alerts="true" />
			</div>
		</div>
		<div class="w-64 flex-shrink-0">
			<SchemaExplorer :schema="dataSourceSchema" @insert-text="insertTextIntoEditor" />
		</div>
	</div>
</template>
