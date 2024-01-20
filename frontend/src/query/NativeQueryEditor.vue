<script setup>
import Code from '@/components/Controls/Code.vue'
import TextToSQLDialog from '@/components/TextToSQLDialog.vue'
import { call } from 'frappe-ui'
import { computed, inject, ref, watch } from 'vue'
import SchemaExplorerDialog from './SchemaExplorerDialog.vue'

const props = defineProps({
	showToolbar: { type: Boolean, default: true },
})

const query = inject('query')
if (query.doc.data_source) {
	call('insights.api.data_sources.get_source_schema', {
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

const openAIDialog = ref(false)
const showDataExplorer = ref(false)
const nativeQuery = ref(query.doc.sql)
watch(
	() => query.doc.sql,
	(value) => (nativeQuery.value = value)
)
</script>

<template>
	<div class="relative flex flex-1 flex-col overflow-y-scroll">
		<Code
			:key="completions.tables.length"
			language="sql"
			v-model="nativeQuery"
			:schema="completions.schema"
			:tables="completions.tables"
			placeholder="Type your query here"
		></Code>
		<div v-if="props.showToolbar" class="sticky bottom-0 flex gap-2 border-t bg-white p-2">
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
					@click="query.executeSQL(nativeQuery)"
					:loading="query.loading"
				>
				</Button>
			</div>
			<div>
				<Button variant="outline" @click="openAIDialog = true"> OpenAI </Button>
			</div>
		</div>
	</div>
	<SchemaExplorerDialog v-model:show="showDataExplorer" />
	<TextToSQLDialog v-model:show="openAIDialog" :dataSource="query.doc.data_source" />
</template>
