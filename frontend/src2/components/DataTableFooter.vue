<script setup lang="ts">
import { computed, useSlots } from 'vue'
import { Button } from 'frappe-ui'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import type { PaginationState } from '../composables/usePagination'

const props = defineProps<{
	pagination?: PaginationState
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
</script>

<template>
	<!-- the bar is one button tall with or without its buttons, so a footer that
	     is only a status line stands as high as one with a pager -->
	<div v-if="hasContent" class="flex h-9 flex-shrink-0 items-center border-t px-2">
		<div class="flex flex-1 items-center">
			<!-- What a result is, in words, is `ResultStatus`'s — the bar only
			     holds the place for it. -->
			<slot name="left" />
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
