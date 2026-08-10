<script setup lang="ts">
import { Dialog, LoadingIndicator } from 'frappe-ui'
import { provide, ref } from 'vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import QueryExecutionStatus from '../../query/components/QueryExecutionStatus.vue'
import QueryOperations from '../../query/components/QueryOperations.vue'
import QueryToolbar from '../../query/components/QueryToolbar.vue'
import { makeAdhocQuery } from '../../query/query'
import { __ } from '../../translation'
import type { AdhocFilters } from '../../types/query.types'
import type { DrillLevelData } from './drill_stack'

// A drill level, continued in the full builder.
//
// The pipeline is the server's — the same slice it ran to answer the level — so
// nothing here derives anything. It is loaded into an ad-hoc query, which is a
// document nobody owns until someone saves it: closing this leaves the workbook
// exactly as it was.
const props = defineProps<{
	/** an authoring level, which is the only kind that carries a pipeline */
	level: DrillLevelData
	title: string
	/** what the surface's own filters narrowed to, which the slice does not carry */
	adhocFilters?: AdhocFilters
}>()

const emit = defineEmits<{ closed: [] }>()

const open = ref(true)
const ready = ref(false)

const query = makeAdhocQuery()
query.doc.title = `${props.title} — ${__('Drill Down')}`
query.doc.use_live_connection = props.level.use_live_connection
query.setOperations(props.level.operations || [])
if (props.adhocFilters) query.adhocFilters = props.adhocFilters
// from here on it is the reader's query: every edit in the sidebar re-runs it
query.autoExecute = true
query.execute(true).finally(() => (ready.value = true))

provide('query', query)
</script>

<template>
	<Dialog v-model:open="open" size="5xl" :title="__('Drill Down')" @after-leave="emit('closed')">
		<div v-if="!ready" class="flex h-[32rem] w-full items-center justify-center">
			<LoadingIndicator class="h-5 w-5 text-ink-gray-5" />
		</div>
		<div v-else class="relative flex h-[32rem] w-full flex-1 gap-4 overflow-hidden">
			<div class="flex h-full flex-1 flex-col gap-2 overflow-hidden p-0.5">
				<QueryToolbar>
					<QueryExecutionStatus />
				</QueryToolbar>
				<div class="flex flex-1 overflow-hidden rounded-4 border border-outline-gray-2">
					<!-- no drill from here: the ladder is behind this dialog, and a
					     second one started inside it is the recursion ticket 11 retired -->
					<QueryDataTable :query="query" :enable-sort="true" />
				</div>
			</div>
			<div
				class="relative flex h-full w-[17rem] flex-shrink-0 overflow-y-auto rounded-4 border border-outline-gray-2"
			>
				<QueryOperations />
			</div>
		</div>
	</Dialog>
</template>
