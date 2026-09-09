<script setup lang="ts">
import { LoadingIndicator, Tooltip } from 'frappe-ui'
import { RefreshCw } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import type { PaginationState } from '../../composables/usePagination'
import { __ } from '../../translation'

// What the result is, in one line: how many rows, what the run cost, and when.
// Every editor used to write its own copy of the cache line. This is the one.
const props = defineProps<{
	running?: boolean
	/** edited since the last run — only an editor that does not auto-run can say so */
	stale?: boolean
	failed?: boolean
	/** where in the result the reader is, when there is more than one page */
	paging?: PaginationState
	/** the rows the browser holds, which is what a find counts against */
	loadedCount: number
	/** the count the server reported, once it has been asked for one */
	totalRowCount?: number
	onFetchCount?: () => Promise<void> | void
	/** "fetched in 1.2s" or "from cache" — empty before the first run */
	timing?: string
	lastRun?: string
	/** what a find left, when one is active */
	narrowed?: { matched: number; loaded: number }
}>()

/**
 * The count, when one is settled: the server's if it reported one, and the
 * loaded count when nobody is going to ask for one. A count still to be
 * fetched is not settled, so it reads as unknown rather than as the page.
 */
const settledCount = computed(() => {
	if (props.totalRowCount) return props.totalRowCount
	return props.onFetchCount ? undefined : props.loadedCount
})

/**
 * True when the page is the whole result. A range that starts at the first row
 * and ends at the last one says nothing the count does not, so the line drops
 * it and reads as one number.
 */
const showsEverything = computed(() => {
	if (!props.paging || settledCount.value === undefined) return false
	return props.paging.from.value === 1 && props.paging.to.value === settledCount.value
})

const fetchingCount = ref(false)
async function fetchCount() {
	if (!props.onFetchCount) return
	fetchingCount.value = true
	try {
		await props.onFetchCount()
	} finally {
		fetchingCount.value = false
	}
}
</script>

<template>
	<div class="tnum flex items-center gap-1 text-sm text-ink-gray-5">
		<span v-if="props.stale">{{ __('Edited since last run') }}</span>

		<template v-else-if="props.failed">
			<span>{{ __('Failed') }}</span>
			<template v-if="props.lastRun">
				<span class="text-ink-gray-4">·</span>
				<span>{{ props.lastRun }}</span>
			</template>
		</template>

		<template v-else>
			<!-- A find covers what is loaded, so it counts against that and not
			     against the row count the server reported. -->
			<span v-if="props.narrowed">
				{{
					__(
						'Showing {0} of {1} loaded rows',
						String(props.narrowed.matched),
						String(props.narrowed.loaded),
					)
				}}
			</span>
			<span v-else-if="showsEverything">
				{{ __('Showing {0} rows', settledCount!.toLocaleString()) }}
			</span>
			<template v-else-if="props.paging">
				<span>
					{{
						__(
							'Showing {0}–{1} of',
							String(props.paging.from.value),
							String(props.paging.to.value),
						)
					}}
				</span>
				<template v-if="props.totalRowCount">
					{{ props.totalRowCount.toLocaleString() }}
				</template>
				<template v-else-if="props.onFetchCount">
					<LoadingIndicator
						v-if="fetchingCount"
						class="inline h-3.5 w-3.5 text-ink-gray-4"
					/>
					<Tooltip v-else :text="__('Load Count')">
						<RefreshCw
							class="inline-flex h-3.5 w-3.5 cursor-pointer transition-all hover:text-ink-gray-7"
							stroke-width="1.5"
							@click="fetchCount"
						/>
					</Tooltip>
				</template>
				<template v-else>{{ props.loadedCount.toLocaleString() }}</template>
				<span>{{ __('rows') }}</span>
			</template>
			<span v-else>{{ __('Showing 0 rows') }}</span>

			<!-- Only the tail changes while a run is on, so the count holds its
			     place and nothing jumps when the answer lands. -->
			<Transition
				enter-active-class="transition-opacity duration-150"
				leave-active-class="transition-opacity duration-150"
				enter-from-class="opacity-0"
				leave-to-class="opacity-0"
				mode="out-in"
			>
				<span v-if="props.running" class="flex items-center gap-1">
					<span class="text-ink-gray-4">·</span>
					<LoadingIndicator class="h-3.5 w-3.5 text-ink-gray-4" />
					<span>{{ __('fetching…') }}</span>
				</span>
				<span v-else-if="props.timing || props.lastRun" class="flex items-center gap-1">
					<template v-if="props.timing">
						<span class="text-ink-gray-4">·</span>
						<span>{{ props.timing }}</span>
					</template>
					<template v-if="props.lastRun">
						<span class="text-ink-gray-4">·</span>
						<span>{{ props.lastRun }}</span>
					</template>
				</span>
			</Transition>
		</template>
	</div>
</template>
