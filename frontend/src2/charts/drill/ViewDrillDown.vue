<script setup lang="ts">
import { Button, LoadingIndicator } from 'frappe-ui'
import { AlertTriangle, XIcon } from 'lucide-vue-next'
import { defineAsyncComponent, shallowRef, ref, type Component } from 'vue'
import { __ } from '../../translation'
import DrillPlaceholder from './DrillPlaceholder.vue'
import type { DrillSubject } from './drill_stack'
import type { ChartSegmentClick } from './segment_click'

// The same drill an author gets, minus everything only an author can do — the
// counterpart of `BuilderDrillDown`, for a surface that only reads.
//
// It is loaded on the click that opens it and not before. The dialog, its
// breakdown chart and the stack behind them are reached by a click a reader may
// never make, and the rows pane — a result pane, a grid, a filter picker and an
// export dialog — is the heaviest thing a dashboard can reach and the one
// furthest from what it draws. The app ships one island stylesheet, built from
// every chunk of the bundle, so the rules these chunks need are already in the
// sheet the shadow root adopted.
//
// The three states the chunk can be in are held here rather than handed to
// `defineAsyncComponent`: Vue builds an `errorComponent` with the error and
// nothing else — no parent props and no listeners — so a Dismiss drawn inside
// one reaches nothing, and the banner outlives every later click. The dismiss
// belongs where the click it takes back is held, which is the surface above.
const props = defineProps<{ subject: DrillSubject; clicked: ChartSegmentClick }>()

const emit = defineEmits<{ close: [] }>()

const ChartDrillDown = shallowRef<Component>()
const failed = ref(false)

import('./ChartDrillDown.vue')
	.then((module) => (ChartDrillDown.value = module.default))
	.catch((error) => {
		console.error('[insights] Could not load the drill down.', error)
		failed.value = true
	})

const DrillRowsView = defineAsyncComponent({
	loader: () => import('./DrillRowsView.vue'),
	// The dialog is already open and already answered for by the time this
	// renders, so a chunk still in flight would leave the reader an empty box
	// where the rows are. It waits behind the placeholder the level itself loads
	// behind, from the first frame — a drill opened cold fetches this chunk after
	// the dialog's, and there is no delay short enough to be worth a blank.
	loadingComponent: DrillPlaceholder,
	delay: 0,
})
</script>

<template>
	<component
		:is="ChartDrillDown"
		v-if="ChartDrillDown"
		:subject="props.subject"
		:clicked="props.clicked"
		@close="emit('close')"
	>
		<!-- A reader is offered the rows behind a segment, so this is where they
		     are drawn. Sorting, finding and paging them is the server's: the
		     pipeline that produced them is not on the answer, is not asked for, and
		     none of the editor that would run it is imported here. -->
		<template #rows="{ answer, levels, findTarget }">
			<DrillRowsView
				:answer="answer"
				:levels="levels"
				:subject="props.subject"
				:find-target="findTarget"
			/>
		</template>
	</component>

	<!-- This is what mounts the menu, so until it lands the click has drawn
	     nothing at all — no menu, no cursor change and nothing to wait on. -->
	<div
		v-else-if="!failed"
		class="pointer-events-none absolute inset-0 flex items-center justify-center"
	>
		<LoadingIndicator class="w-6 text-ink-gray-5" />
	</div>

	<!-- The chunk did not land — offline, or an asset index a deploy left behind.
	     The drill has nothing to draw, so it says so and ends: the reader takes
	     the click back and the card is theirs again. -->
	<div
		v-else
		class="absolute inset-x-2 bottom-2 flex items-center gap-2 rounded-4 border border-outline-gray-2 bg-surface-white px-2 py-1.5"
	>
		<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
		<span class="flex-1 text-p-sm text-ink-gray-6">
			{{ __('Could not open the drill down') }}
		</span>
		<Button variant="ghost" :aria-label="__('Dismiss')" @click="emit('close')">
			<template #icon>
				<XIcon class="size-4 text-ink-gray-6" />
			</template>
		</Button>
	</div>
</template>
