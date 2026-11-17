<script setup lang="ts">
import { inject, onBeforeUnmount, ref } from 'vue'
import { Query } from '../query'
import QueryActions from './QueryActions.vue'
import QueryBuilderSourceSelector from './QueryBuilderSourceSelector.vue'
import QueryBuilderTable from './QueryBuilderTable.vue'
import QueryHeader from './QueryHeader.vue'
import QueryInfo from './QueryInfo.vue'
import QueryOperations from './QueryOperations.vue'
import { useUndoKeys } from '../../helpers/undo_keys'

const query = inject<Query>('query')!
const $find = ref<HTMLElement>()
query.autoExecute = true

useUndoKeys({
	undo: () => query.canUndo() && query.history.undo(),
	redo: () => query.canRedo() && query.history.redo(),
})

onBeforeUnmount(() => {
	query.activeOperationIdx = query.doc.operations.length - 1
})
</script>

<template>
	<div class="flex flex-1 overflow-hidden">
		<div class="relative flex h-full flex-1 flex-col gap-3 overflow-hidden px-4 pb-4 pt-3">
			<QueryBuilderSourceSelector v-if="!query.doc.operations.length" />
			<template v-else>
				<QueryHeader>
					<div ref="$find" class="flex"></div>
					<QueryActions />
				</QueryHeader>
				<QueryBuilderTable :find-target="$find" />
			</template>
		</div>
		<div
			class="relative flex h-full w-[19rem] flex-shrink-0 flex-col overflow-y-auto bg-surface-base"
		>
			<QueryInfo />
			<QueryOperations />
		</div>
	</div>
</template>
