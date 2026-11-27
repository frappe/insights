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
import { workbookKey } from '../../workbook/workbook_key'
import { __ } from '../../translation'

const query = inject<Query>('query')!
const $find = ref<HTMLElement>()
const workbook = inject(workbookKey)!
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
			<!-- picking its source is editing it -->
			<p
				v-if="!query.doc.operations.length && workbook.readOnly"
				class="py-8 text-center text-base text-ink-gray-5"
			>
				{{ __('This query has no data yet.') }}
			</p>
			<QueryBuilderSourceSelector v-else-if="!query.doc.operations.length" />
			<template v-else>
				<QueryHeader>
					<div ref="$find" class="flex"></div>
					<QueryActions />
				</QueryHeader>
				<QueryBuilderTable :find-target="$find" />
			</template>
		</div>
		<div
			class="relative flex h-full w-[19rem] flex-shrink-0 flex-col overflow-y-auto bg-surface-base max-sm:hidden"
		>
			<QueryInfo />
			<QueryOperations />
		</div>
	</div>
</template>
