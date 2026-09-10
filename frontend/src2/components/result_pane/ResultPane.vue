<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Button, LoadingIndicator } from 'frappe-ui'
import { Search, Table2Icon, TriangleAlert } from 'lucide-vue-next'
import { computed, provide, ref, watch } from 'vue'
import { usePagination } from '../../composables/usePagination'
import type { ResultTable } from '../../query/result_table'
import session from '../../session'
import { __ } from '../../translation'
import ExportDialog from '../ExportDialog.vue'
import { findRows } from './find'
import ResultFind from './ResultFind.vue'
import ResultFooter from './ResultFooter.vue'
import { RESULT_GRID_HOST, type ResultGrid } from './result_grid'
import ResultStatus from './ResultStatus.vue'
import { fetchTiming } from './status'

// The one card around a query result: a header, the grid, and a footer. Every
// editor used to assemble this by hand, which is why the cache line was written
// three times and the execution error was a banner that pushed the grid down.
//
// Everything here acts on the *result*. What acts on the query — Execute, the
// query menu, the data source — is the page header's, above the editor.
//
// The grid itself is the host's, through `#grid`: what a cell can be renamed,
// sorted or drilled into is the host's to know. What the pane owns is the
// chrome — the find, the paging cursor and the status line.
const props = defineProps<{
	query: ResultTable
	/** the result no longer answers the editor above it — SQL and script only */
	stale?: boolean
	/** Where the host wants the find control. Without one it sits in the pane's own header. */
	findTarget?: HTMLElement | null
	/** a host whose rows only back a picture above them has nothing to find in */
	noFind?: boolean
}>()

const columns = computed(() => props.query.result.columns || [])
const loadedRows = computed(() => props.query.result.formattedRows || [])

// --- find: client-only, over the rows already loaded ------------------------

const term = ref('')
const $find = ref<InstanceType<typeof ResultFind> | null>(null)
const matchedRows = computed(() => findRows(loadedRows.value, term.value))

function clearFind() {
	$find.value?.clear()
}

// The grid is the host's, so where a column sits is the grid's to know. The
// pane knows only that the find asked for one.
const $grid = ref<ResultGrid>()
provide(RESULT_GRID_HOST, { setGrid: (grid?: ResultGrid) => ($grid.value = grid) })

function jumpToColumn(column_name: string) {
	$grid.value?.scrollToColumn(column_name)
}

// --- paging: one cursor, owned here so the footer can print its range -------

const pageSize = computed(() => props.query.pageSize ?? loadedRows.value.length + 1)
const pagination = usePagination({
	pageSize,
	rowCount: computed(() => matchedRows.value.length),
	totalRowCount: computed(() => props.query.result.totalRowCount || undefined),
	currentPage: computed(() => props.query.currentPage),
	onPageChange: props.query.goToPage,
	enabled: true,
})
const pageRows = computed(() =>
	matchedRows.value.slice(pagination.startIndex.value, pagination.endIndex.value),
)

// --- states -----------------------------------------------------------------

const running = computed(() => props.query.executing)
const failed = computed(() => Boolean(props.query.executionError))

const bodyState = computed<'error' | 'loading' | 'nomatch' | 'nodata' | null>(() => {
	if (failed.value) return 'error'
	// a first run has no columns to dim, so it gets an indicator instead of
	// "no data" — the answer is on its way, not missing
	if (running.value && !columns.value.length) return 'loading'
	if (!columns.value.length) return 'nodata'
	if (!matchedRows.value.length) return term.value ? 'nomatch' : 'nodata'
	return null
})

// there is a range to page through only when the grid is what the body draws
const pageRange = computed(() => (bodyState.value ? undefined : pagination))

const timeAgo = useTimeAgo(() => props.query.result.lastExecutedAt)
const lastRun = computed(() => (props.query.result.executedSQL ? timeAgo.value : ''))
const timing = computed(() => fetchTiming(props.query.result))
const narrowed = computed(() =>
	term.value ? { matched: matchedRows.value.length, loaded: loadedRows.value.length } : undefined,
)

// --- export ------------------------------------------------------------------

const canExport = computed(
	() => session.user.can_download && Boolean(props.query.exportResults) && !failed.value,
)
const showExportDialog = ref(false)
const exportDefaultName = computed(() => {
	const now = new Date()
	return `export_${now.getDate()}_${now.getMonth()}_${now.getFullYear()}`
})

watch(
	() => props.query.downloading,
	(downloading, wasDownloading) => {
		if (wasDownloading && !downloading) showExportDialog.value = false
	},
)
</script>

<template>
	<div class="flex h-full min-h-0 w-full flex-1 flex-col rounded-4 border border-outline-gray-2">
		<!-- The find is the pane's — it knows the rows and the columns — but a
		     host with a header of its own places it there. Outside the clip
		     below either way, so the find panel can hang past the border. -->
		<Teleport v-if="props.findTarget && !props.noFind" :to="props.findTarget">
			<ResultFind
				ref="$find"
				v-model="term"
				:columns="columns"
				:match-count="matchedRows.length"
				@jump="jumpToColumn"
			/>
		</Teleport>
		<div
			v-else-if="!props.noFind || $slots['header-left'] || $slots.actions"
			class="relative flex h-10 flex-shrink-0 items-center justify-between gap-3 border-b px-3"
		>
			<div class="min-w-0">
				<slot name="header-left" />
			</div>
			<div class="flex flex-shrink-0 items-center gap-2">
				<slot name="actions" />
				<ResultFind
					v-if="!props.noFind"
					ref="$find"
					v-model="term"
					:columns="columns"
					:match-count="matchedRows.length"
					@jump="jumpToColumn"
				/>
			</div>
		</div>

		<!-- With the find teleported away there is no header bar, so this clip is the
		     pane's top edge too: its corners must round or the grid's header fill
		     squares them off. A Teleport leaves only comment nodes behind, so
		     `first:` still sees this as the first child. -->
		<div
			class="flex min-h-0 w-full flex-1 flex-col overflow-hidden rounded-b-4 first:rounded-t-4"
		>
			<!-- one slot, three states: the body is replaced, never banner-ed -->
			<div
				v-if="bodyState"
				class="flex flex-1 items-center justify-center overflow-auto p-6"
				:class="running && bodyState !== 'loading' ? 'opacity-50' : ''"
			>
				<LoadingIndicator v-if="bodyState === 'loading'" class="h-5 w-5 text-ink-gray-4" />

				<div
					v-else-if="bodyState === 'error'"
					class="flex max-w-2xl flex-col items-center gap-2"
				>
					<TriangleAlert class="h-8 w-8 text-ink-red-4" stroke-width="1.5" />
					<div
						class="whitespace-pre-wrap text-center font-mono text-xs leading-5 text-ink-red-4"
					>
						{{ props.query.executionError }}
					</div>
				</div>

				<div v-else-if="bodyState === 'nomatch'" class="flex flex-col items-center gap-2">
					<Search class="h-16 w-16 text-ink-gray-2" stroke-width="1.5" />
					<p class="text-center text-ink-gray-4">
						{{ __('No rows match “{0}”', term) }}
					</p>
					<Button variant="subtle" :label="__('Clear')" @click="clearFind" />
				</div>

				<div v-else class="flex flex-col items-center gap-2">
					<Table2Icon class="h-16 w-16 text-ink-gray-2" stroke-width="1.5" />
					<p class="text-center text-ink-gray-4">{{ __('No data to display.') }}</p>
				</div>
			</div>

			<div v-else class="relative flex min-h-0 w-full flex-1 overflow-hidden">
				<slot
					name="grid"
					:rows="pageRows"
					:current-page="pagination.currentPage.value"
					:page-size="pageSize"
				/>
			</div>

			<ResultFooter
				:pagination="pageRange"
				:on-export="canExport ? () => (showExportDialog = true) : undefined"
			>
				<template #left>
					<ResultStatus
						:running="running"
						:stale="props.stale"
						:failed="failed"
						:paging="pageRange"
						:loaded-count="loadedRows.length"
						:total-row-count="props.query.result.totalRowCount || undefined"
						:on-fetch-count="props.query.fetchResultCount"
						:timing="timing"
						:last-run="lastRun"
						:narrowed="narrowed"
					/>
				</template>
			</ResultFooter>
		</div>
	</div>

	<ExportDialog
		v-model="showExportDialog"
		:downloading="props.query.downloading"
		:default-filename="exportDefaultName"
		@export="(format, filename) => props.query.exportResults?.(format, filename)"
		@cancel="props.query.cancelDownload?.()"
	/>
</template>
