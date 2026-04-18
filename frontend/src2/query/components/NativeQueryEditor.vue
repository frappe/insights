<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { MoreHorizontal, Play, Wand2, DatabaseZap } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import ContentEditable from '../../components/ContentEditable.vue'
import useDataSourceStore from '../../data_source/data_source'
import { wheneverChanges } from '../../helpers'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { createToast } from '../../helpers/toasts'
import useSettings from '../../settings/settings'
import { __ } from '../../translation'
import { Query } from '../query'
import QueryDataTable from './QueryDataTable.vue'
import SchemaExplorer from './SchemaExplorer.vue'
import DataSourceSelector from './source_selector/DataSourceSelector.vue'

const query = inject<Query>('query')!
const settings = useSettings()
query.autoExecute = false
query.execute()

function toggleLiveConnection(enable: boolean) {
	const title = enable ? __('Enable Data Store') : __('Disable Data Store')
	const message = enable
		? __(
				'Enabling data store use the cached table data for faster queries, but may not be up-to-date. It will also allow you to combine data from multiple sources. Cached data is updated every day.',
		  )
		: __(
				'Disabling data store will use the live connection to the database for queries. This will ensure that you are always querying the most up-to-date data but may be slower.',
		  )

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
</script>

<template>
	<div class="flex flex-1 gap-4 overflow-hidden p-4">
		<div class="flex flex-1 flex-col gap-4 overflow-hidden">
			<div class="relative flex h-[55%] w-full flex-col rounded border">
				<div class="flex flex-shrink-0 items-center gap-1 border-b p-1">
					<div class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden">
						<DataSourceSelector
							v-model="data_source"
							placeholder="Select a data source"
						/>
						<ContentEditable
							class="flex h-7 cursor-text items-center justify-center rounded bg-white px-2 text-base leading-7 text-gray-800 focus-visible:ring-1 focus-visible:ring-gray-600"
							placeholder="Untitled Dashboard"
							:modelValue="query.doc.title"
							@returned="query.doc.title = $event"
							@blur="query.doc.title = $event"
						></ContentEditable>
					</div>
					<!-- <div
						v-if="settings.doc.enable_data_store"
						class="ml-auto flex flex-shrink-0 items-center gap-2 px-1 text-sm text-gray-600"
					>
						<span>{{ __('Enable Data Store') }}</span>
						<Toggle
							:modelValue="!query.doc.use_live_connection"
							@update:modelValue="toggleLiveConnection"
						/>
					</div> -->
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
					<Button @click="execute(true)" :label="__('Execute')">
						<template #prefix>
							<Play class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<Dropdown
						:button="{ icon: MoreHorizontal }"
						:options="[
							{
								label: query.doc.use_live_connection
									? __('Enable Data Store')
									: __('Disable Data Store'),
								icon: DatabaseZap,
								onClick: () =>
									toggleLiveConnection(query.doc.use_live_connection || false),
							},
							{
								label: __('Format SQL'),
								icon: Wand2,
								onClick: () => format(),
							},
						]"
					/>
				</div>
			</div>
			<div
				v-show="query.result.executedSQL"
				class="tnum flex flex-shrink-0 items-center gap-2 text-sm text-gray-600"
			>
				<div class="h-2 w-2 rounded-full bg-green-500"></div>
				<div class="flex items-center gap-1">
					<span v-if="query.result.timeTaken == -1">
						{{ __('Fetched from cache') }}
					</span>
					<span v-else>
						{{ __('Fetched in {0}s', String(query.result.timeTaken)) }}
					</span>
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
