<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { onBeforeUnmount, provide } from 'vue'
import { WorkbookQuery } from '../types/workbook.types'
import NativeQueryEditor from './components/NativeQueryEditor.vue'
import useQuery from './query'
import QueryBuilder from './components/QueryBuilder.vue'

const props = defineProps<{ query: WorkbookQuery }>()
const query = useQuery(props.query)
provide('query', query)
window.query = query
query.execute()

const keys = useMagicKeys()
const cmdZ = keys['Meta+Z']
const cmdShiftZ = keys['Meta+Shift+Z']
const stopUndoWatcher = whenever(cmdZ, () => query.canUndo() && query.history.undo())
const stopRedoWatcher = whenever(cmdShiftZ, () => query.canRedo() && query.history.redo())

onBeforeUnmount(() => {
	stopUndoWatcher()
	stopRedoWatcher()
})
</script>

<template>
	<QueryBuilder v-if="query.doc.is_builder_query" />
	<NativeQueryEditor v-else-if="query.doc.is_native_query" />
</template>
