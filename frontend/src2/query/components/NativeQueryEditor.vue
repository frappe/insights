<script setup lang="ts">
import { toast } from 'frappe-ui'
import { Wand2 } from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import { useShortcut } from '../../composables/useShortcut'
import { useSourceSchema } from '../../data_source/data_source'
import { __ } from '../../translation'
import { Query } from '../query'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import QueryActions from './QueryActions.vue'
import QueryDataTable from './QueryDataTable.vue'
import QueryHeader from './QueryHeader.vue'
import QueryInfo from './QueryInfo.vue'
import SchemaExplorer from './SchemaExplorer.vue'
import DataSourceSelector from './source_selector/DataSourceSelector.vue'

const query = inject<Query>('query')!
const $find = ref<HTMLElement>()
query.autoExecute = false
query.ensureResult()

const operation = query.getSQLOperation()
const data_source = ref(operation ? operation.data_source : '')
const sql = ref(operation ? operation.raw_sql : '')

function execute(force: boolean = false) {
	if (!data_source.value) {
		toast.error(__('Please select a data source first'))
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
		toast.error(__('Failed to format SQL'))
	} finally {
		formatting.value = false
	}
}

const extraActions = () => [
	{
		label: __('Format SQL'),
		icon: h(Wand2, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => format(),
	},
]

const codeEditor = ref<InstanceType<typeof Code> | null>(null)
function insertTextIntoEditor(text: string) {
	if (codeEditor.value) {
		codeEditor.value.insertText(text)
	}
}

const sourceSchema = useSourceSchema(data_source)
const completions = computed(() => {
	if (!Object.keys(sourceSchema.schema).length)
		return {
			schema: {},
			tables: [],
		}

	const schema: Record<string, any> = {}
	Object.entries(sourceSchema.schema).forEach(([table, tableData]) => {
		schema[table] = tableData.columns.map((column: any) => ({
			label: column.label,
			detail: column.type,
		}))
	})

	const tables = Object.entries(sourceSchema.schema).map(([table, tableData]) => ({
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

// The SQL in the editor reaches the query only on a run, so the text is a
// staleness source of its own — the query's own check cannot see it.
const stale = computed(() => {
	const operation = query.getSQLOperation()
	return sql.value !== (operation ? operation.raw_sql : '') || query.isStale
})
</script>

<template>
	<div class="flex flex-1 overflow-hidden">
		<div class="relative flex h-full flex-1 flex-col gap-3 overflow-hidden px-4 pb-4 pt-3">
			<QueryHeader>
				<DataSourceSelector
					v-model="data_source"
					:placeholder="__('Select a data source')"
				/>
				<QueryActions
					:on-execute="() => execute(true)"
					:extra-actions="extraActions"
					:stale="stale"
				/>
			</QueryHeader>

			<!-- SQL Editor -->
			<div class="relative flex flex-1 flex-col overflow-hidden rounded-4 border">
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
			<div class="relative flex h-[45%] w-full flex-col gap-2">
				<div ref="$find" class="flex flex-shrink-0"></div>
				<ResultPane :query="query" :stale="stale" :find-target="$find">
					<template #grid="{ rows, currentPage, pageSize }">
						<QueryDataTable
							:query="query"
							:rows="rows"
							:current-page="currentPage"
							:page-size="pageSize"
						/>
					</template>
				</ResultPane>
			</div>
		</div>

		<!-- Right Sidebar -->
		<div
			class="relative flex h-full w-[19rem] flex-shrink-0 flex-col overflow-y-auto bg-surface-base"
		>
			<QueryInfo />

			<!-- Schema Explorer -->
			<SchemaExplorer
				:schema="sourceSchema.schema"
				:loading="sourceSchema.loading"
				:failed="sourceSchema.failed"
				@insert-text="insertTextIntoEditor"
			/>
		</div>
	</div>
</template>
