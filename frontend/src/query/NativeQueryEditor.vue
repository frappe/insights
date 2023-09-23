<script setup>
import Code from '@/components/Controls/Code.vue'
import { call } from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import SchemaExplorerDialog from './SchemaExplorerDialog.vue'

const query = inject('query')
if (query.doc.data_source) {
	call('insights.api.get_source_schema', {
		data_source: query.doc.data_source,
	}).then((response) => {
		query.sourceSchema = response
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

const nativeQuery = ref(query.doc.sql)
watch(
	() => query.doc.sql,
	(value) => {
		nativeQuery.value = value
	}
)
function runQuery() {
	query.setValue.submit({ sql: nativeQuery.value }).then(() => {
		query.run.submit()
	})
}

const showDataExplorer = ref(false)
</script>

<template>
	<div class="flex w-full flex-1 flex-shrink-0 flex-col">
		<div class="flex-shrink-0 uppercase leading-7 tracking-wide text-gray-600">
			Native Query
		</div>
		<div class="relative flex flex-1 flex-col overflow-y-scroll rounded border">
			<Code
				:key="completions.tables.length"
				language="sql"
				v-model="nativeQuery"
				:schema="completions.schema"
				:tables="completions.tables"
				placeholder="Type your query here"
			></Code>
			<div class="sticky bottom-0 flex gap-2 bg-white p-2">
				<div>
					<Button
						variant="subtle"
						icon="book-open"
						@click="showDataExplorer = !showDataExplorer"
					></Button>
				</div>
				<div>
					<Button
						variant="solid"
						icon="play"
						@click="runQuery"
						:loading="query.run.loading"
					>
					</Button>
				</div>
			</div>
		</div>
	</div>
	<SchemaExplorerDialog v-model:show="showDataExplorer" />
</template>
