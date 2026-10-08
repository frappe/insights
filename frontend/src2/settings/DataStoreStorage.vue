<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Alert, call, LoadingIndicator, toast, Tree } from 'frappe-ui'
import type { TreeKey } from 'frappe-ui'
import { RefreshCw } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref } from 'vue'
import StackedBar from '../components/StackedBar.vue'
import dayjs from '../helpers/dayjs'
import { showErrorToast } from '../helpers'
import { __ } from '../translation'
import {
	DataStoreStorage,
	formatBytes,
	StorageNode,
	storageSegments,
	storageTree,
	StoredColumn,
	StoredTable,
	unusedBytes,
} from './data_store_storage'
import StorageTreeLabel from './StorageTreeLabel.vue'

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

const tree = computed(() => (storage.value ? storageTree(storage.value) : []))
const largestNode = computed(() => Math.max(...tree.value.map((node) => node.bytes), 1))
const expanded = ref<TreeKey[]>([])
</script>

<template>
	<div class="flex flex-col gap-6">
		<div class="flex items-center justify-between gap-4">
			<h2 class="text-lg-semibold text-ink-gray-8">{{ __('Storage') }}</h2>
			<div v-if="storage?.measured_on" class="flex items-center gap-1">
				<span class="text-sm text-ink-gray-5">
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
				<p class="text-p-base text-ink-gray-8">{{ summary }}</p>
				<StackedBar size="lg" :segments="segments" />
				<div class="flex flex-wrap gap-x-3 gap-y-1">
					<div v-for="s in segments" :key="s.key" class="flex items-center gap-1">
						<span class="h-2 w-2 shrink-0 rounded-full" :class="s.class"></span>
						<span class="text-sm text-ink-gray-6">{{ s.label }}</span>
						<span class="text-sm tabular-nums text-ink-gray-5">
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

			<Tree
				v-if="tree.length"
				v-model:expanded="expanded"
				:nodes="tree"
				node-key="key"
				guides="none"
			>
				<template #item-label="{ node }">
					<StorageTreeLabel
						:node="node as StorageNode"
						:skip-column="skipColumn"
						:remove-table="removeTable"
						@changed="load"
					/>
				</template>
				<template #item-suffix="{ node }">
					<div class="flex items-center gap-3 pl-3">
						<div v-if="(node as StorageNode).segments.length" class="w-44">
							<StackedBar
								:segments="(node as StorageNode).segments"
								:max="largestNode"
							/>
						</div>
						<span class="w-16 text-right text-base tabular-nums text-ink-gray-7">
							{{ formatBytes((node as StorageNode).bytes) }}
						</span>
					</div>
				</template>
			</Tree>
		</template>
	</div>
</template>
