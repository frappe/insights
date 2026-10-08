<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Alert, call, LoadingIndicator, toast } from 'frappe-ui'
import { ChevronDown, ChevronRight, RefreshCw } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref } from 'vue'
import StackedBar from '../components/StackedBar.vue'
import dayjs from '../helpers/dayjs'
import { showErrorToast } from '../helpers'
import { __ } from '../translation'
import {
	cleanupReason,
	DataStoreStorage,
	formatBytes,
	groupSegment,
	storageSegments,
	StoredColumn,
	StoredTable,
	tableSegments,
	unusedBytes,
} from './data_store_storage'
import StorageTableRow from './StorageTableRow.vue'

const POLL_INTERVAL = 3000

const storage = ref<DataStoreStorage | null>(null)
const loading = ref(true)
let pollTimer: ReturnType<typeof setTimeout> | undefined
let unmounted = false

function load() {
	return call<DataStoreStorage>('insights.api.data_store.get_storage')
		.then((data) => (storage.value = data))
		.catch((err: Error) => showErrorToast(err, false))
		.finally(() => (loading.value = false))
}

function pollWhileMeasuring(measuredOn: string | null) {
	clearTimeout(pollTimer)
	if (unmounted || !storage.value?.measuring || storage.value.measured_on !== measuredOn) return
	pollTimer = setTimeout(() => load().then(() => pollWhileMeasuring(measuredOn)), POLL_INTERVAL)
}

load().then(() => pollWhileMeasuring(storage.value?.measured_on ?? null))
onBeforeUnmount(() => {
	unmounted = true
	clearTimeout(pollTimer)
})

const measuring = computed(() => Boolean(storage.value?.measuring))
const measuredAgo = useTimeAgo(() => storage.value?.measured_on || '')

async function measure() {
	const measuredOn = storage.value?.measured_on ?? null
	try {
		await call('insights.api.data_store.measure')
	} catch (err) {
		return showErrorToast(err as Error, false)
	}
	await load()
	pollWhileMeasuring(measuredOn)
}

async function resumeCleanup() {
	try {
		await call('insights.api.data_store.resume_cleanup')
	} catch (err) {
		return showErrorToast(err as Error, false)
	}
	toast.success(__('Cleanup resumed'))
	await load()
}

function skipColumn(table: StoredTable, column: StoredColumn) {
	return call('run_doc_method', {
		dt: 'Insights Table v3',
		dn: table.name,
		method: 'skip_columns',
		args: { columns: [column.name] },
	}).then(() => toast.success(__('Skipped {0}', column.name)))
}

function removeTable(table: StoredTable) {
	return call('run_doc_method', {
		dt: 'Insights Table v3',
		dn: table.name,
		method: 'clear_warehouse_data',
	}).then(() => toast.success(__('Removed {0}', table.label)))
}

const summary = computed(() => {
	if (!storage.value) return ''
	const onDisk = formatBytes(storage.value.file_bytes)
	const read = formatBytes(storage.value.groups.read)
	const unused = unusedBytes(storage.value)
	if (!unused) return __('{0} on disk. Queries read {1}.', onDisk, read)
	return __('{0} on disk. Queries read {1}, {2} is unused.', onDisk, read, formatBytes(unused))
})

const segments = computed(() => (storage.value ? storageSegments(storage.value) : []))

const largestTable = computed(() => {
	const tables = storage.value?.tables || []
	return Math.max(cleanupBytes.value, ...tables.map((table) => table.bytes), 1)
})

const cleanupTables = computed(() =>
	[...(storage.value?.cleanup_tables || [])].sort((a, b) => b.bytes - a.bytes),
)
const cleanupBytes = computed(() => cleanupTables.value.reduce((sum, t) => sum + t.bytes, 0))
const cleanupSegments = computed(() => [
	groupSegment('cleanup', cleanupBytes.value, storage.value?.unread_days ?? 0),
])
const cleanupCount = computed(() =>
	cleanupTables.value.length === 1
		? __('1 table')
		: __('{0} tables', String(cleanupTables.value.length)),
)
const cleanupExpanded = ref(false)
</script>

<template>
	<div class="flex flex-col gap-6">
		<div class="flex items-center justify-between gap-4">
			<h2 class="text-lg-semibold text-ink-gray-8">{{ __('Storage') }}</h2>
			<div v-if="storage?.measured_on" class="flex items-center gap-1">
				<span class="text-p-sm text-ink-gray-5">
					{{ measuring ? __('Measuring…') : __('Measured {0}', measuredAgo) }}
				</span>
				<Tooltip :text="__('Measure again')">
					<Button
						variant="ghost"
						:icon="RefreshCw"
						:loading="measuring"
						:aria-label="__('Measure again')"
						@click="measure"
					/>
				</Tooltip>
			</div>
		</div>

		<div v-if="loading && !storage" class="flex h-24 items-center justify-center">
			<LoadingIndicator class="h-5 w-5 text-ink-gray-5" />
		</div>

		<div
			v-else-if="storage && !storage.measured_on"
			class="flex flex-col items-center gap-3 rounded-6 border border-dashed border-outline-gray-2 px-6 py-10"
		>
			<span class="text-base-medium text-ink-gray-8">{{ __('Not measured yet') }}</span>
			<Button :label="__('Measure')" variant="solid" :loading="measuring" @click="measure" />
		</div>

		<template v-else-if="storage">
			<div class="flex flex-col gap-2.5">
				<p class="text-p-lg text-ink-gray-8">{{ summary }}</p>
				<StackedBar size="lg" :segments="segments" />
				<div class="flex flex-wrap gap-x-3 gap-y-1">
					<div v-for="s in segments" :key="s.key" class="flex items-center gap-1">
						<span class="h-2 w-2 shrink-0 rounded-full" :class="s.class"></span>
						<span class="text-p-sm text-ink-gray-6">{{ s.label }}</span>
						<span class="text-p-sm tabular-nums text-ink-gray-5">
							{{ formatBytes(s.value) }}
						</span>
					</div>
				</div>
			</div>

			<Alert
				v-if="storage.cleanup.stopped"
				theme="amber"
				:primary-action="{ label: __('Resume'), onClick: resumeCleanup }"
			>
				<template #title>
					<Tooltip
						:text="__('Cleanup removes tables no query reads and compacts the file.')"
					>
						<span>
							{{
								storage.cleanup.stopped_on
									? __(
											'Weekly cleanup paused since {0}',
											dayjs(storage.cleanup.stopped_on).format('D MMM'),
									  )
									: __('Weekly cleanup paused')
							}}
						</span>
					</Tooltip>
				</template>
			</Alert>

			<div v-if="storage.tables.length || cleanupTables.length" class="flex flex-col gap-2">
				<h3 class="text-base-semibold text-ink-gray-8">{{ __('Tables') }}</h3>
				<div class="flex flex-col divide-y divide-outline-gray-1">
					<StorageTableRow
						v-for="table in storage.tables"
						:key="table.name"
						:table="table"
						:segments="tableSegments(storage, table)"
						:max="largestTable"
						:skip-column="skipColumn"
						:remove-table="removeTable"
						@changed="load"
					/>
					<div v-if="cleanupTables.length" class="flex flex-col">
						<div
							class="group/cleanup flex cursor-pointer items-center gap-2 py-2"
							role="button"
							tabindex="0"
							:aria-expanded="cleanupExpanded"
							@click="cleanupExpanded = !cleanupExpanded"
							@keydown.enter.prevent="cleanupExpanded = !cleanupExpanded"
							@keydown.space.prevent="cleanupExpanded = !cleanupExpanded"
						>
							<component
								:is="cleanupExpanded ? ChevronDown : ChevronRight"
								class="h-4 w-4 shrink-0 text-ink-gray-5"
								:class="
									cleanupExpanded
										? ''
										: 'opacity-0 group-hover/cleanup:opacity-100 group-focus-within/cleanup:opacity-100'
								"
								aria-hidden="true"
							/>
							<div class="flex min-w-0 flex-1 items-baseline gap-2">
								<span class="truncate text-base-medium text-ink-gray-8">
									{{ __('Cleanup removes') }}
								</span>
								<span class="shrink-0 text-p-sm tabular-nums text-ink-gray-5">
									{{ cleanupCount }}
								</span>
							</div>
							<div class="w-1/4">
								<StackedBar :segments="cleanupSegments" :max="largestTable" />
							</div>
							<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
								{{ formatBytes(cleanupBytes) }}
							</span>
							<div class="w-24"></div>
						</div>
						<div
							v-if="cleanupExpanded"
							class="mb-2 ml-6 flex flex-col divide-y divide-outline-gray-1"
						>
							<div
								v-for="t in cleanupTables"
								:key="`${t.schema}.${t.table}`"
								class="flex h-9 items-center gap-2"
							>
								<span
									class="min-w-0 flex-1 truncate font-mono text-sm text-ink-gray-7"
								>
									{{ t.schema }}.{{ t.table }}
								</span>
								<span class="w-40 truncate text-p-sm text-ink-gray-5">
									{{ cleanupReason(t.reason) }}
								</span>
								<span
									class="w-16 text-right text-base tabular-nums text-ink-gray-7"
								>
									{{ formatBytes(t.bytes) }}
								</span>
								<div class="w-24"></div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>
