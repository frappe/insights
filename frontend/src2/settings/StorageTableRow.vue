<script setup lang="ts">
import { ChevronDown, ChevronRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import StackedBar from '../components/StackedBar.vue'
import { formatNumber } from '../helpers'
import { __ } from '../translation'
import {
	BarSegment,
	columnsBySize,
	formatBytes,
	StoredColumn,
	StoredTable,
} from './data_store_storage'
import StorageAction from './StorageAction.vue'

const props = defineProps<{
	table: StoredTable
	segments: BarSegment[]
	max: number
	skipColumn: (table: StoredTable, column: StoredColumn) => Promise<unknown>
	skipMessage: (table: StoredTable, column: StoredColumn) => string
}>()

const emit = defineEmits<{ changed: [] }>()

const expanded = ref(false)
const columns = computed(() => (expanded.value ? columnsBySize(props.table) : []))

function readersLabel(column: StoredColumn) {
	if (!column.readers.length) return __('No readers')
	if (column.readers.length === 1) return __('1 reader')
	return __('{0} readers', String(column.readers.length))
}
</script>

<template>
	<div class="flex flex-col">
		<div class="flex cursor-pointer items-center gap-3 py-2" @click="expanded = !expanded">
			<Button
				variant="ghost"
				:icon="expanded ? ChevronDown : ChevronRight"
				:aria-label="expanded ? __('Collapse') : __('Expand')"
				@click.stop="expanded = !expanded"
			/>
			<div class="flex min-w-0 flex-1 flex-col">
				<span class="truncate text-base-medium text-ink-gray-8">{{ table.label }}</span>
				<span class="truncate text-p-sm text-ink-gray-5">
					{{ table.data_source }} · {{ __('{0} rows', formatNumber(table.rows)) }} ·
					{{ table.sync_mode === 'Incremental' ? __('Incremental') : __('Full') }}
				</span>
			</div>
			<div class="w-1/3">
				<StackedBar :segments="segments" :max="max" />
			</div>
			<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
				{{ formatBytes(table.bytes) }}
			</span>
		</div>

		<div v-if="expanded" class="mb-2 ml-9 flex flex-col divide-y divide-outline-gray-1">
			<div v-for="column in columns" :key="column.name" class="flex h-9 items-center gap-3">
				<span class="min-w-0 flex-1 truncate font-mono text-sm text-ink-gray-7">
					{{ column.name }}
				</span>
				<Tooltip :disabled="!column.readers.length">
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
					<span class="w-24 text-p-sm text-ink-gray-5">{{ readersLabel(column) }}</span>
				</Tooltip>
				<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
					{{ formatBytes(column.bytes) }}
				</span>
				<div class="flex w-40 justify-end">
					<span v-if="column.skipped" class="text-p-sm text-ink-gray-5">
						{{ __('Removed at next import') }}
					</span>
					<span v-else-if="!column.skippable" class="text-p-sm text-ink-gray-5">
						{{ __('Used by the import') }}
					</span>
					<StorageAction
						v-else-if="!column.readers.length"
						:label="__('Skip')"
						:title="__('Skip {0}', column.name)"
						:table="table"
						:message="skipMessage(table, column)"
						:action="() => skipColumn(table, column)"
						@done="emit('changed')"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
