<script setup>
import Code from '@/components/Controls/Code.vue'
import { call } from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import SchemaExplorerDialog from './SchemaExplorerDialog.vue'

const props = defineProps({
	showToolbar: { type: Boolean, default: true },
})

const query = inject('query')
if (query.doc.data_source) {
	call('run_doc_method', {
		method: 'get_schema',
		dt: 'Insights Data Source',
		dn: query.doc.data_source,
	}).then((response) => {
		query.sourceSchema = response.message
	})
}
const completions = computed(() => {
	if (!query.sourceSchema) return { schema: {}, tables: [] }

	const schema = {}
	Object.entries(query.sourceSchema).forEach(([table, tableData]) => {
		schema[table] = tableData.columns.map((column) => ({
			label: column.column,
			detail: column.label,
		}))
	})

	const tables = Object.entries(query.sourceSchema).map(([table, tableData]) => ({
		label: table,
		detail: tableData.label,
	}))

	return {
		schema,
		tables,
	}
})

const showDataExplorer = ref(false)
const nativeQuery = ref(query.doc.sql)
watch(
	() => query.doc.sql,
	(value) => (nativeQuery.value = value)
)
</script>

<template>
	<div class="relative flex flex-1 flex-col overflow-y-auto">
		<Code
			:key="completions.tables.length"
			language="sql"
			v-model="nativeQuery"
			:schema="completions.schema"
			:tables="completions.tables"
			placeholder="Type your query here"
		></Code>
		<div v-if="props.showToolbar" class="sticky bottom-0 flex gap-1 border-t bg-white p-1">
			<div>
				<Button
					variant="outline"
					iconLeft="book-open"
					@click="showDataExplorer = !showDataExplorer"
					label="Tables"
				>
				</Button>
			</div>
			<div>
				<Button
					:variant="query.doc.status !== 'Execution Successful' ? 'solid' : 'outline'"
					iconLeft="play"
					@click="query.executeSQL(nativeQuery)"
					:loading="query.loading"
					label="Run"
				>
				</Button>
			</div>
		</div>
	</div>
	<SchemaExplorerDialog v-model:show="showDataExplorer" />
</template>
