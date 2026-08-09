<script setup lang="ts">
import { Breadcrumbs, Button, Dialog, LoadingIndicator } from 'frappe-ui'
import { AlertTriangle, ChevronLeft } from 'lucide-vue-next'
import { computed } from 'vue'
import { __ } from '../../translation'
import DrillBreakdown from './DrillBreakdown.vue'
import DrillRecords from './DrillRecords.vue'
import type { DrillLevelData, DrillStack } from './drill_stack'
import type { ChartSegmentClick } from './segment_click'

// One dialog for the whole drill, with a back-stack inside it.
//
// The reader's path is the breadcrumb trail, and every crumb pops to the level
// it reads. Nothing is fetched twice: the stack holds each level's answer for as
// long as the dialog is open, so back and crumb clicks are instant.
//
// Nothing here is a destination. There is no route, nothing is persisted, and
// closing loses the path — this is an inspection.
const props = defineProps<{
	stack: DrillStack
	title: string
	data?: DrillLevelData
	loading?: boolean
	failed?: boolean
}>()

const emit = defineEmits<{
	segmentClick: [click: ChartSegmentClick]
	// eslint-disable-next-line no-unused-vars
	popTo: [depth: number]
	/** after the dialog has gone, so the path it held goes with it */
	closed: []
}>()

const open = defineModel<boolean>({ default: false })

const action = computed(() => props.stack.current?.level.action)
const breakdown = computed(() => {
	const current = action.value
	return current && 'breakdown' in current ? current : undefined
})

// The trail, with the page's own name at the head of it, so a reader three
// levels down still knows which card they came from. The last crumb is where
// they are; frappe-ui draws it as the plain one.
const crumbs = computed(() => [
	{ label: props.title, onClick: () => emit('popTo', 0) },
	...props.stack.crumbs.map((crumb) => ({
		label: crumb.label,
		onClick: () => emit('popTo', crumb.depth),
	})),
])

/**
 * What the reader is seeing, out of what there is. Real paging is not built —
 * the honest thing until someone hits the bound is to say where it is.
 */
const bound = computed(() => {
	if (!props.data) return ''
	const shown = props.data.rows.length
	const total = props.data.total_row_count
	if (!total || total <= shown) return __('{0} rows', shown.toLocaleString())
	return __('{0} of {1} rows', shown.toLocaleString(), total.toLocaleString())
})
</script>

<template>
	<Dialog v-model:open="open" size="5xl" @after-leave="emit('closed')">
		<template #title>
			<div class="flex min-w-0 flex-1 items-center gap-2">
				<Button
					variant="ghost"
					:disabled="!stack.depth"
					@click="emit('popTo', stack.depth - 1)"
				>
					<template #icon>
						<ChevronLeft class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
				<Breadcrumbs class="min-w-0" :items="crumbs" />
				<!-- what a surface may do with the level it is reading. Empty on a
				     reading surface, which has nothing to offer beyond the ladder. -->
				<div class="ml-auto flex flex-shrink-0 items-center gap-2 pl-2">
					<slot name="actions" />
				</div>
			</div>
		</template>

		<div class="flex h-[32rem] w-full flex-col gap-2">
			<div v-if="props.loading" class="flex h-full w-full items-center justify-center">
				<LoadingIndicator class="h-5 w-5 text-ink-gray-5" />
			</div>

			<div
				v-else-if="props.failed || !props.data"
				class="flex h-full w-full flex-col items-center justify-center gap-2"
			>
				<AlertTriangle class="h-6 w-6 text-ink-gray-4" stroke-width="1" />
				<p class="text-p-base text-ink-gray-5">{{ __('This drill is not available') }}</p>
			</div>

			<template v-else>
				<div class="min-h-0 flex-1 overflow-hidden rounded border border-outline-gray-2">
					<DrillBreakdown
						v-if="breakdown"
						:data="props.data"
						:dimension="breakdown.breakdown"
						:measure="breakdown.measure || ''"
						@segment-click="emit('segmentClick', $event)"
					/>
					<DrillRecords v-else :data="props.data" />
				</div>
				<p class="flex-shrink-0 px-1 text-p-sm text-ink-gray-5">{{ bound }}</p>
			</template>
		</div>
	</Dialog>
</template>
