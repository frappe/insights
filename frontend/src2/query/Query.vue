<script setup lang="ts">
import { provide } from 'vue'
import { WorkbookQuery } from '../types/workbook.types'
import NativeQueryEditor from './components/NativeQueryEditor.vue'
import QueryBuilder from './components/QueryBuilder.vue'
import useQuery from './query'

const props = defineProps<{ query: WorkbookQuery }>()
const query = useQuery(props.query)
provide('query', query)
window.query = query
query.execute()
</script>

<template>
	<QueryBuilder v-if="query.doc.is_builder_query" />
	<NativeQueryEditor v-else-if="query.doc.is_native_query" />
</template>
