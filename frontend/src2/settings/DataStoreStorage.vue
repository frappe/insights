<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Alert, call, LoadingIndicator, toast } from 'frappe-ui'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref } from 'vue'
import StackedBar from '../components/StackedBar.vue'
import dayjs from '../helpers/dayjs'
import { showErrorToast } from '../helpers'
import { __ } from '../translation'
import {
	cleanupReason,
	DataStoreStorage,
	formatBytes,
	giveBackItems,
	groupSegment,
	storageSegments,
	StoredColumn,
	StoredTable,
	tableSegments,
} from './data_store_storage'
import StorageAction from './StorageAction.vue'
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
	toast.success(__('Weekly cleanup resumed'))
	await load()
}

function skipColumn(table: StoredTable, column: StoredColumn) {
	return call('run_doc_method', {
		dt: 'Insights Table v3',
		dn: table.name,
		method: 'skip_columns',
		args: { columns: [column.name] },
	}).then(() => toast.success(__('{0} is removed at the next import', column.name)))
}

function removeTable(table: StoredTable) {
	return call('run_doc_method', {
		dt: 'Insights Table v3',
		dn: table.name,
		method: 'clear_warehouse_data',
	}).then(() => toast.success(__('{0} removed from the Data Store', table.label)))
}

function skipMessage(table: StoredTable, column: StoredColumn) {
	return __(
		'The next import leaves out {0} and removes it from the stored table. {1} imports incrementally, so rows the source no longer holds cannot be imported again.',
		column.name,
		table.label,
	)
}

function removeMessage(table: StoredTable) {
	return __(
		'{0} is removed from the Data Store. It imports incrementally, so rows the source no longer holds cannot be imported again.',
		table.label,
	)
}

const summary = computed(() => {
	if (!storage.value) return ''
	return __(
		'{0} on disk. Queries read {1} of it.',
		formatBytes(storage.value.file_bytes),
		formatBytes(storage.value.groups.read),
	)
})

const segments = computed(() => (storage.value ? storageSegments(storage.value) : []))

const giveBack = computed(() => (storage.value ? giveBackItems(storage.value) : []))
const giveBackBytes = computed(() => giveBack.value.reduce((sum, item) => sum + item.bytes, 0))

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
const cleanupExpanded = ref(false)

const cleanupTitle = computed(() => {
	const count = cleanupTables.value.length
	if (storage.value?.cleanup.stopped) {
		return count === 1
			? __('1 table the weekly cleanup would remove')
			: __('{0} tables the weekly cleanup would remove', String(count))
	}
	return count === 1
		? __('1 table the weekly cleanup removes')
		: __('{0} tables the weekly cleanup removes', String(count))
})
</script>

<template>
	<div class="flex flex-col gap-6">
		<div class="flex items-center justify-between gap-4">
			<h2 class="text-lg-semibold text-ink-gray-8">{{ __('Storage') }}</h2>
			<div v-if="storage?.measured_on" class="flex items-center gap-2">
				<span class="text-p-sm text-ink-gray-5">
					{{ measuring ? __('Measuring…') : __('Measured {0}', measuredAgo) }}
				</span>
				<Button
					:label="__('Measure')"
					variant="ghost"
					:loading="measuring"
					@click="measure"
				/>
			</div>
		</div>

		<div v-if="loading" class="flex h-24 items-center justify-center">
			<LoadingIndicator class="h-5 w-5 text-ink-gray-5" />
		</div>

		<div
			v-else-if="storage && !storage.measured_on"
			class="flex flex-col items-center gap-3 rounded-6 border border-dashed border-outline-gray-2 px-6 py-10 text-center"
		>
			<div class="flex flex-col gap-1">
				<span class="text-base-medium text-ink-gray-8">
					{{ __('The Data Store has not been measured yet') }}
				</span>
				<span class="text-p-sm text-ink-gray-5">
					{{
						__(
							'Measuring reads the size of every stored table and column. It runs in the background.',
						)
					}}
				</span>
			</div>
			<Button
				:label="measuring ? __('Measuring…') : __('Measure')"
				variant="solid"
				:loading="measuring"
				@click="measure"
			/>
		</div>

		<template v-else-if="storage">
			<div class="flex flex-col gap-3">
				<p class="text-p-lg text-ink-gray-8">{{ summary }}</p>
				<StackedBar size="lg" :segments="segments" />
				<div class="flex flex-wrap gap-x-4 gap-y-1.5">
					<div v-for="s in segments" :key="s.key" class="flex items-center gap-1.5">
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
				:title="
					storage.cleanup.stopped_on
						? __(
								'Weekly cleanup is paused since {0}',
								dayjs(storage.cleanup.stopped_on).format('D MMM'),
						  )
						: __('Weekly cleanup is paused')
				"
				:description="__('The cleanup drops tables no query uses and compacts the file.')"
				:primary-action="{ label: __('Resume'), onClick: resumeCleanup }"
			/>

			<div v-if="giveBack.length" class="flex flex-col gap-2">
				<h3 class="text-base-semibold text-ink-gray-8">
					{{ __('You can give back {0}', formatBytes(giveBackBytes)) }}
				</h3>
				<div class="flex flex-col divide-y divide-outline-gray-1">
					<div
						v-for="item in giveBack"
						:key="
							item.kind === 'column'
								? `${item.table.name}.${item.column.name}`
								: item.table.name
						"
						class="flex min-h-12 items-center gap-3 py-2"
					>
						<div class="flex min-w-0 flex-1 flex-col">
							<span
								v-if="item.kind === 'column'"
								class="truncate text-base-medium text-ink-gray-8"
							>
								<span class="font-mono">{{ item.column.name }}</span>
								<span class="text-ink-gray-5"> · {{ item.table.label }}</span>
							</span>
							<span v-else class="truncate text-base-medium text-ink-gray-8">
								{{ item.table.label }}
							</span>
							<span class="truncate text-p-sm text-ink-gray-5">
								{{
									item.kind === 'column'
										? __('No query or chart names this column')
										: __(
												'No query read this table in {0} days',
												String(storage.unread_days),
										  )
								}}
							</span>
						</div>
						<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
							{{ formatBytes(item.bytes) }}
						</span>
						<div class="flex w-40 justify-end">
							<StorageAction
								v-if="item.kind === 'column'"
								:label="__('Skip')"
								:title="__('Skip {0}', item.column.name)"
								:table="item.table"
								:message="skipMessage(item.table, item.column)"
								:action="() => skipColumn(item.table, item.column)"
								@done="load"
							/>
							<StorageAction
								v-else
								:label="__('Remove from Data Store')"
								:title="__('Remove {0} from the Data Store', item.table.label)"
								:table="item.table"
								:message="removeMessage(item.table)"
								:action="() => removeTable(item.table)"
								@done="load"
							/>
						</div>
					</div>
				</div>
			</div>

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
						:skip-message="skipMessage"
						@changed="load"
					/>
					<div v-if="cleanupTables.length" class="flex flex-col">
						<div
							class="flex cursor-pointer items-center gap-3 py-2"
							@click="cleanupExpanded = !cleanupExpanded"
						>
							<Button
								variant="ghost"
								:icon="cleanupExpanded ? ChevronDown : ChevronRight"
								:aria-label="cleanupExpanded ? __('Collapse') : __('Expand')"
								@click.stop="cleanupExpanded = !cleanupExpanded"
							/>
							<div class="flex min-w-0 flex-1 flex-col">
								<span class="truncate text-base-medium text-ink-gray-8">
									{{ cleanupTitle }}
								</span>
								<span
									v-if="storage.cleanup.stopped"
									class="truncate text-p-sm text-ink-gray-5"
								>
									{{ __('The weekly cleanup is paused, so these stay') }}
								</span>
							</div>
							<div class="w-1/3">
								<StackedBar :segments="cleanupSegments" :max="largestTable" />
							</div>
							<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
								{{ formatBytes(cleanupBytes) }}
							</span>
						</div>
						<div
							v-if="cleanupExpanded"
							class="mb-2 ml-9 flex flex-col divide-y divide-outline-gray-1"
						>
							<div
								v-for="t in cleanupTables"
								:key="`${t.schema}.${t.table}`"
								class="flex h-9 items-center gap-3"
							>
								<span
									class="min-w-0 flex-1 truncate font-mono text-sm text-ink-gray-7"
								>
									{{ t.schema }}.{{ t.table }}
								</span>
								<span class="w-56 truncate text-p-sm text-ink-gray-5">
									{{ cleanupReason(t.reason) }}
								</span>
								<span
									class="w-16 text-right text-base tabular-nums text-ink-gray-7"
								>
									{{ formatBytes(t.bytes) }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>
