<script setup lang="ts">
import { Button, LoadingIndicator, Tooltip } from 'frappe-ui'
import { ChevronLeft, ChevronRight, RefreshCw } from 'lucide-vue-next'
import { ref } from 'vue'
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
	<div class="flex flex-shrink-0 items-center border-t px-2 py-1">
		<div class="flex flex-1 items-center">
			<slot name="left">
				<div
					v-if="pagination && !pagination.isSinglePage.value"
					class="flex items-center gap-1 tnum text-sm text-gray-500"
				>
					Showing {{ pagination.from.value }}–{{ pagination.to.value }} of
					<template v-if="totalRowCount">
						{{ totalRowCount.toLocaleString() }}
					</template>
					<template v-else-if="onFetchCount">
						<template v-if="localFetchingCount">
							<LoadingIndicator class="inline h-3.5 w-3.5 text-gray-500" />
						</template>
						<Tooltip v-else text="Load Count">
							<RefreshCw
								class="inline-flex h-3.5 w-3.5 cursor-pointer transition-all hover:text-gray-800"
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
			<template v-if="pagination && !pagination.isSinglePage.value">
				<Button
					variant="ghost"
					:disabled="pagination.isFirstPage.value"
					@click="emit('prev')"
				>
					<template #icon>
						<ChevronLeft class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
				<span class="tnum min-w-[3rem] text-center text-sm text-gray-600">
					Page {{ pagination.currentPage.value }}
				</span>
				<Button
					variant="ghost"
					:disabled="pagination.isLastPage.value"
					@click="emit('next')"
				>
					<template #icon>
						<ChevronRight class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<slot name="actions" />
		</div>
	</div>
</template>
