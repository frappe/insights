<script setup>
import Code from '@/components/Controls/Code.vue'
import { computed, inject, ref, watch } from 'vue'

const query = inject('query')
query.getSourceSchema.submit()
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
</script>

<template>
	<div class="flex w-full flex-1 flex-shrink-0 flex-col">
		<div class="h-8 flex-shrink-0 text-sm uppercase tracking-wide text-gray-600">
			Native Query
		</div>
		<div class="flex flex-1 overflow-scroll">
			<Code
				:key="completions.tables.length"
				language="sql"
				v-model="nativeQuery"
				:schema="completions.schema"
				:tables="completions.tables"
			></Code>
		</div>
		<div class="mt-4 h-10 flex-shrink-0 space-x-2">
			<Button iconLeft="play" appearance="white" class="shadow-sm" @click="runQuery">
				Run
			</Button>
		</div>
	</div>
</template>
