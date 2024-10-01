<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { onBeforeUnmount, provide } from 'vue'
import { WorkbookQuery } from '../types/workbook.types'
import QueryBuilderSourceSelector from './components/QueryBuilderSourceSelector.vue'
import QueryBuilderTable from './components/QueryBuilderTable.vue'
import QueryBuilderToolbar from './components/QueryBuilderToolbar.vue'
import QueryInfo from './components/QueryInfo.vue'
import QueryOperations from './components/QueryOperations.vue'
import useQuery from './query'

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
	<div class="flex flex-1 overflow-hidden">
		<QueryBuilderSourceSelector v-if="!query.doc.operations.length" />
		<div v-else class="relative flex h-full w-full flex-col overflow-hidden">
			<QueryBuilderToolbar></QueryBuilderToolbar>
			<div class="flex flex-1 overflow-hidden border">
				<QueryBuilderTable></QueryBuilderTable>
			</div>
		</div>
		<div
			class="relative z-[1] flex h-full w-[17rem] flex-shrink-0 flex-col gap-1 divide-y overflow-y-auto bg-white shadow"
		>
			<QueryInfo />
			<QueryOperations />
		</div>
	</div>
</template>
