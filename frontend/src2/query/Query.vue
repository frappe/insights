<script setup lang="ts">
import { computed, provide } from 'vue'
import WorkbookQueryEmptyState from '../workbook/WorkbookQueryEmptyState.vue'
import NativeQueryEditor from './components/NativeQueryEditor.vue'
import QueryBuilder from './components/QueryBuilder.vue'
import ScriptQueryEditor from './components/ScriptQueryEditor.vue'
import useQuery from './query'
import { waitUntil } from '../helpers'

const props = defineProps<{ query_name: string }>()
const query = useQuery(props.query_name)
provide('query', query)
window.query = query

await waitUntil(() => query.isloaded)

const hasSourceOp = computed(() => query.doc.operations.find((op) => op.type === 'source'))

function setQueryType(interfaceType: 'query-builder' | 'sql-editor' | 'script-editor') {
	if (!query) return
	query.doc.is_native_query = interfaceType === 'sql-editor'
	query.doc.is_script_query = interfaceType === 'script-editor'
	query.doc.is_builder_query = interfaceType === 'query-builder'
}
</script>

<template>
	<QueryBuilder v-if="query.doc.is_builder_query || hasSourceOp" />
	<NativeQueryEditor v-else-if="query.doc.is_native_query" />
	<ScriptQueryEditor v-else-if="query.doc.is_script_query" />
	<WorkbookQueryEmptyState v-else @select="setQueryType" />
</template>
