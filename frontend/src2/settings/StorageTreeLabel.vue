<script setup lang="ts">
import { Clock, Lock } from 'lucide-vue-next'
import { computed } from 'vue'
import { formatNumber } from '../helpers'
import { __ } from '../translation'
import {
	cleanupReason,
	columnClass,
	columnState,
	formatBytes,
	readersLabel,
	StorageNode,
	StoredColumn,
	StoredTable,
} from './data_store_storage'
import StorageAction from './StorageAction.vue'

const props = defineProps<{
	node: StorageNode
	skipColumn: (table: StoredTable, column: StoredColumn) => Promise<unknown>
	removeTable: (table: StoredTable) => Promise<unknown>
}>()

const emit = defineEmits<{ changed: [] }>()

const details = computed(() => {
	if (props.node.kind !== 'table') return ''
	const table = props.node.table
	return [
		table.data_source,
		__('{0} rows', formatNumber(table.rows)),
		table.sync_mode === 'Incremental' ? __('Incremental') : __('Full'),
	].join(' · ')
})

const cleanupCount = computed(() => {
	if (props.node.kind !== 'cleanup') return ''
	const count = props.node.children.length
	return count === 1 ? __('1 table') : __('{0} tables', String(count))
})
</script>

<template>
	<div class="flex min-w-0 items-center gap-2">
		<template v-if="node.kind === 'table'">
			<Tooltip :text="details">
				<span class="truncate text-base-medium text-ink-gray-8">{{ node.label }}</span>
			</Tooltip>
			<span
				v-if="node.table.unread_bytes > 0"
				class="shrink-0 text-sm tabular-nums text-ink-gray-5"
			>
				{{ __('{0} unused', formatBytes(node.table.unread_bytes)) }}
			</span>
			<StorageAction
				v-if="node.table.unread"
				:label="__('Remove')"
				:tooltip="__('Remove from the Data Store')"
				:title="__('Remove {0} from the Data Store', node.label)"
				:table="node.table"
				:action="removeTable.bind(null, node.table)"
				@done="emit('changed')"
			/>
		</template>

		<template v-else-if="node.kind === 'column'">
			<span
				class="h-2 w-2 shrink-0 rounded-full"
				:class="columnClass(node.table, node.column)"
			></span>
			<span class="truncate text-base text-ink-gray-7">{{ node.label }}</span>
			<Tooltip v-if="node.column.readers.length">
				<template #content>
					<div class="flex flex-col gap-0.5">
						<span
							v-for="reader in node.column.readers"
							:key="reader.doctype + reader.name"
						>
							{{ reader.title }}
						</span>
					</div>
				</template>
				<span class="shrink-0 text-sm text-ink-gray-5">
					{{ readersLabel(node.column.readers) }}
				</span>
			</Tooltip>
			<Tooltip
				v-if="columnState(node.column) === 'skipped'"
				:text="__('Removed at the next import')"
			>
				<Clock class="h-4 w-4 shrink-0 text-ink-gray-4" />
			</Tooltip>
			<Tooltip
				v-else-if="columnState(node.column) === 'needed'"
				:text="__('The import needs this column')"
			>
				<Lock class="h-4 w-4 shrink-0 text-ink-gray-4" />
			</Tooltip>
			<StorageAction
				v-else-if="columnState(node.column) === 'unread'"
				:label="__('Skip')"
				:title="__('Skip {0}', node.label)"
				:table="node.table"
				:action="skipColumn.bind(null, node.table, node.column)"
				@done="emit('changed')"
			/>
		</template>

		<template v-else-if="node.kind === 'cleanup'">
			<span class="truncate text-base-medium text-ink-gray-8">{{ node.label }}</span>
			<span class="shrink-0 text-sm tabular-nums text-ink-gray-5">{{ cleanupCount }}</span>
		</template>

		<template v-else>
			<span class="truncate text-base text-ink-gray-7">{{ node.label }}</span>
			<span class="shrink-0 text-sm text-ink-gray-5">
				{{ cleanupReason(node.cleanupTable.reason) }}
			</span>
		</template>
	</div>
</template>
