<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Copy, CopyPlus, MoreHorizontal, PlayIcon, RefreshCw, Scroll, Wand2 } from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import { formatShortcut, useShortcut } from '../../composables/useShortcut'
import useDataSourceStore from '../../data_source/data_source'
import { wheneverChanges } from '../../helpers'
import { createToast } from '../../helpers/toasts'
import session from '../../session'
import { __ } from '../../translation'
import { Query } from '../query'
import QueryDataTable from './QueryDataTable.vue'
import QueryInfo from './QueryInfo.vue'
import SchemaExplorer from './SchemaExplorer.vue'
import DataSourceSelector from './source_selector/DataSourceSelector.vue'
import ViewSQLDialog from './ViewSQLDialog.vue'
import { Tooltip } from 'frappe-ui'

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

const showViewSQLDialog = ref(false)

const moreActions = computed(() => {
	const actions: any[] = []

	if (!query.doc.use_live_connection && session.user.is_admin) {
		actions.push({
			label: __('Refresh Stored Tables'),
			icon: h(RefreshCw, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: query.refreshStoredTables,
		})
	}

	actions.push(
		{
			label: __('Format SQL'),
			icon: h(Wand2, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: () => format(),
		},
		{
			label: __('View SQL'),
			icon: h(Scroll, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: () => (showViewSQLDialog.value = true),
		},
		{
			label: __('Duplicate Query'),
			icon: h(CopyPlus, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: () => query.duplicate(),
		},
		{
			label: __('Copy Query'),
			icon: h(Copy, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: () => query.copy(),
		},
	)

	return actions
})

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
			<div class="flex w-full flex-shrink-0 items-center justify-between bg-white">
				<DataSourceSelector v-model="data_source" placeholder="Select a data source" />
				<div class="flex items-center gap-2">
					<Tooltip :text="__('Execute ({0})', formatShortcut('Meta+E'))">
						<Button variant="outline" :label="__('Execute')" @click="execute(true)">
							<template #prefix>
								<PlayIcon class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
							</template>
						</Button>
					</Tooltip>
					<Dropdown placement="right" :options="moreActions">
						<Button variant="outline">
							<template #icon>
								<MoreHorizontal class="h-4 w-4 text-gray-700" stroke-width="1.5" />
							</template>
						</Button>
					</Dropdown>
				</div>
			</div>

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

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
