<script setup lang="ts">
import { ChevronDown, ChevronRight, Clock, Lock } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import StackedBar from '../components/StackedBar.vue'
import { formatNumber } from '../helpers'
import { __ } from '../translation'
import {
	BarSegment,
	columnClass,
	columnsBySize,
	columnState,
	formatBytes,
	readersLabel,
	StoredColumn,
	StoredTable,
} from './data_store_storage'
import StorageAction from './StorageAction.vue'

const props = defineProps<{
	table: StoredTable
	segments: BarSegment[]
	max: number
	skipColumn: (table: StoredTable, column: StoredColumn) => Promise<unknown>
	removeTable: (table: StoredTable) => Promise<unknown>
}>()

const emit = defineEmits<{ changed: [] }>()

const expanded = ref(false)
const columns = computed(() => (expanded.value ? columnsBySize(props.table) : []))

const details = computed(() =>
	[
		props.table.data_source,
		__('{0} rows', formatNumber(props.table.rows)),
		props.table.sync_mode === 'Incremental' ? __('Incremental') : __('Full'),
	].join(' · '),
)
</script>

<template>
	<div class="flex flex-col">
		<div
			class="group/table flex cursor-pointer items-center gap-2 py-2"
			role="button"
			tabindex="0"
			:aria-expanded="expanded"
			@click="expanded = !expanded"
			@keydown.enter.prevent="expanded = !expanded"
			@keydown.space.prevent="expanded = !expanded"
		>
			<component
				:is="expanded ? ChevronDown : ChevronRight"
				class="h-4 w-4 shrink-0 text-ink-gray-5"
				:class="
					expanded
						? ''
						: 'opacity-0 group-hover/table:opacity-100 group-focus-within/table:opacity-100'
				"
				aria-hidden="true"
			/>
			<div class="flex min-w-0 flex-1 items-baseline gap-2">
				<Tooltip :text="details">
					<span class="truncate text-base-medium text-ink-gray-8">{{ table.label }}</span>
				</Tooltip>
				<span
					v-if="table.unread_bytes > 0"
					class="shrink-0 text-p-sm tabular-nums text-ink-gray-5"
				>
					{{ __('{0} unused', formatBytes(table.unread_bytes)) }}
				</span>
			</div>
			<div class="w-1/4">
				<StackedBar :segments="segments" :max="max" />
			</div>
			<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
				{{ formatBytes(table.bytes) }}
			</span>
			<div class="flex w-24 justify-end">
				<StorageAction
					v-if="table.unread"
					:label="__('Remove')"
					:tooltip="__('Remove from the Data Store')"
					:title="__('Remove {0} from the Data Store', table.label)"
					:table="table"
					:action="() => removeTable(table)"
					reveal-class="opacity-0 group-hover/table:opacity-100 group-focus-within/table:opacity-100"
					@done="emit('changed')"
				/>
			</div>
		</div>

		<div v-if="expanded" class="mb-2 ml-6 flex flex-col divide-y divide-outline-gray-1">
			<div
				v-for="column in columns"
				:key="column.name"
				class="group/column flex h-9 items-center gap-2"
			>
				<span
					class="h-2 w-2 shrink-0 rounded-full"
					:class="columnClass(table, column)"
				></span>
				<span class="min-w-0 flex-1 truncate font-mono text-sm text-ink-gray-7">
					{{ column.name }}
				</span>
				<div class="w-20 text-right">
					<Tooltip v-if="column.readers.length">
						<template #content>
							<div class="flex flex-col gap-0.5">
								<span
									v-for="reader in column.readers"
									:key="reader.doctype + reader.name"
								>
									{{ reader.title }}
								</span>
							</div>
						</template>
						<span class="text-p-sm text-ink-gray-5">
							{{ readersLabel(column.readers) }}
						</span>
					</Tooltip>
				</div>
				<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
					{{ formatBytes(column.bytes) }}
				</span>
				<div class="flex w-24 justify-end">
					<Tooltip
						v-if="columnState(column) === 'skipped'"
						:text="__('Removed at the next import')"
					>
						<Clock class="h-4 w-4 text-ink-gray-4" />
					</Tooltip>
					<Tooltip
						v-else-if="columnState(column) === 'needed'"
						:text="__('The import needs this column')"
					>
						<Lock class="h-4 w-4 text-ink-gray-4" />
					</Tooltip>
					<StorageAction
						v-else-if="columnState(column) === 'unread'"
						:label="__('Skip')"
						:title="__('Skip {0}', column.name)"
						:table="table"
						:action="() => skipColumn(table, column)"
						reveal-class="opacity-0 group-hover/column:opacity-100 group-focus-within/column:opacity-100"
						@done="emit('changed')"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
