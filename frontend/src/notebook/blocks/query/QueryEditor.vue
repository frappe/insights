<script setup>
import Code from '@/components/Controls/Code.vue'
import { inject, computed } from 'vue'

const query = inject('query')
query.autosave = true
query.reload()
query.fetchSourceSchema()
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
</script>

<template>
	<div class="h-full w-full px-2">
		<Code
			:key="completions.tables.length"
			language="sql"
			v-model="query.doc.sql"
			:schema="completions.schema"
			:tables="completions.tables"
		></Code>
	</div>
</template>

<style lang="scss">
.cm-editor {
	user-select: text;
	padding: 0px !important;
	background-color: white !important;
}
</style>
