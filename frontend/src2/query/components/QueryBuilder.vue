<script setup lang="ts">
import { inject, onBeforeUnmount } from 'vue'
import { Query } from '../query'
import QueryBuilderSourceSelector from './QueryBuilderSourceSelector.vue'
import QueryBuilderTable from './QueryBuilderTable.vue'
import QueryBuilderToolbar from './QueryBuilderToolbar.vue'
import QueryInfo from './QueryInfo.vue'
import QueryOperations from './QueryOperations.vue'
import { useMagicKeys } from '@vueuse/core'
import { whenever } from '@vueuse/core'

const query = inject<Query>('query')!
query.autoExecute = true

const keys = useMagicKeys()
const cmdZ = keys['Meta+Z']
const cmdShiftZ = keys['Meta+Shift+Z']
const stopUndoWatcher = whenever(cmdZ, () => query.canUndo() && query.history.undo())
const stopRedoWatcher = whenever(cmdShiftZ, () => query.canRedo() && query.history.redo())

onBeforeUnmount(() => {
	query.activeOperationIdx = query.doc.operations.length - 1
	stopUndoWatcher()
	stopRedoWatcher()
})
</script>

<template>
	<div class="flex flex-1 overflow-hidden">
		<div class="relative flex h-full flex-1 flex-col gap-3 overflow-hidden p-4">
			<QueryBuilderSourceSelector v-if="!query.doc.operations.length" />
			<template v-else>
				<QueryBuilderToolbar></QueryBuilderToolbar>
				<QueryBuilderTable></QueryBuilderTable>
			</template>
		</div>
		<div
			class="relative z-[1] flex h-full w-[19rem] flex-shrink-0 flex-col overflow-y-auto bg-white"
		>
			<QueryInfo />
			<QueryOperations />
		</div>
	</div>
</template>
