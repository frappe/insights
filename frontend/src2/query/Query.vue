<script setup lang="ts">
import { computed, provide } from 'vue'
import { WorkbookQuery } from '../types/workbook.types'
import NativeQueryEditor from './components/NativeQueryEditor.vue'
import QueryBuilder from './components/QueryBuilder.vue'
import useQuery from './query'
import ScriptQueryEditor from './components/ScriptQueryEditor.vue'

const props = defineProps<{ query: WorkbookQuery }>()
const query = useQuery(props.query)
provide('query', query)
window.query = query
query.execute()

const is_builder_query = computed(
	() => query.doc.is_builder_query || query.doc.operations.find((op) => op.type === 'source')
)
</script>

<template>
	<QueryBuilder v-if="is_builder_query" />
	<NativeQueryEditor v-else-if="query.doc.is_native_query" />
	<ScriptQueryEditor v-else-if="query.doc.is_script_query" />
</template>
