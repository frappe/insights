<script setup lang="ts">
import { computed, ref, useSlots } from 'vue'
import { Button, LoadingIndicator, Tooltip } from 'frappe-ui'
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-vue-next'
import type { PaginationState } from '../composables/usePagination'

const props = defineProps<{
	pagination?: PaginationState
	totalRowCount?: number
	onFetchCount?: () => void
}>()

const emit = defineEmits<{
	prev: []
	next: []
}>()

const slots = useSlots()

// An empty bar is still a rule and padding under the last row, so a table with
// one page and no actions gets no bar at all.
const activePagination = computed(() =>
	props.pagination && !props.pagination.isSinglePage.value ? props.pagination : undefined,
)
const hasContent = computed(
	() => Boolean(activePagination.value) || Boolean(slots.left) || Boolean(slots.actions),
)

const localFetchingCount = ref(false)
async function handleFetchCount() {
	if (!props.onFetchCount) return
	localFetchingCount.value = true
	try {
		await props.onFetchCount()
	} finally {
		localFetchingCount.value = false
	}
}
</script>

<template>
	<div v-if="hasContent" class="flex flex-shrink-0 items-center border-t px-2 py-1">
		<div class="flex flex-1 items-center">
			<slot name="left">
				<div
					v-if="activePagination"
					class="flex items-center gap-1 tnum text-sm text-ink-gray-4"
				>
					Showing {{ activePagination.from.value }}–{{ activePagination.to.value }} of
					<template v-if="totalRowCount">
						{{ totalRowCount.toLocaleString() }}
					</template>
					<template v-else-if="onFetchCount">
						<template v-if="localFetchingCount">
							<LoadingIndicator class="inline h-3.5 w-3.5 text-ink-gray-4" />
						</template>
						<Tooltip v-else text="Load Count">
							<RefreshCw
								class="inline-flex h-3.5 w-3.5 cursor-pointer transition-all hover:text-ink-gray-7"
								stroke-width="1.5"
								@click="handleFetchCount"
							/>
						</Tooltip>
					</template>
					rows
				</div>
			</slot>
		</div>
		<div class="flex items-center gap-1">
			<template v-if="activePagination">
				<Button
					variant="ghost"
					:disabled="activePagination.isFirstPage.value"
					@click="emit('prev')"
				>
					<template #icon>
						<ChevronLeft class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
				<span class="tnum min-w-[3rem] text-center text-sm text-ink-gray-5">
					Page {{ activePagination.currentPage.value }}
				</span>
				<Button
					variant="ghost"
					:disabled="activePagination.isLastPage.value"
					@click="emit('next')"
				>
					<template #icon>
						<ChevronRight class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<slot name="actions" />
		</div>
	</div>
</template>
