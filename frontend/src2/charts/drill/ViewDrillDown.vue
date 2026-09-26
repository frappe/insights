<script setup lang="ts">
import { Button, LoadingIndicator } from 'frappe-ui'
import { AlertTriangle, XIcon } from 'lucide-vue-next'
import { defineAsyncComponent, shallowRef, ref, type Component } from 'vue'
import { __ } from '../../translation'
import DrillPlaceholder from './DrillPlaceholder.vue'
import type { DrillSubject } from './drill_stack'
import type { ChartSegmentClick } from './segment_click'

// It loads on the click that opens it. The dialog, its breakdown chart and the
// stack sit behind a click a reader may never make. The rows pane (a result
// pane, a grid, a filter picker and an export dialog) is the heaviest code a
// dashboard can reach. The app ships one island stylesheet built from every
// chunk, so the shadow root already has the styles these chunks need.
//
// The chunk's three states are kept here, not in `defineAsyncComponent`. Vue
// gives an `errorComponent` only the error, with no parent props and no
// listeners. A Dismiss inside it could not close anything, and the banner would
// stay after every later click. So the banner lives here, where it can emit
// `close` to the parent that holds the click.
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
	// The dialog is already open with its answer when this renders, so a chunk
	// still loading would leave an empty box where the rows go. It shows the
	// level's own placeholder from the first frame. A drill opened cold fetches
	// this chunk after the dialog's, and no delay is short enough to be worth a
	// blank box.
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
		<!-- A reader can see the rows behind a segment, so they render here. The
		     server sorts, searches and pages them. The answer does not include the
		     pipeline, the client does not ask for it, and this file imports no
		     editor that could run it. -->
		<template #rows="{ answer, levels, findTarget }">
			<DrillRowsView
				:answer="answer"
				:levels="levels"
				:subject="props.subject"
				:find-target="findTarget"
			/>
		</template>
	</component>

	<!-- This chunk mounts the menu. Until it loads, the click would show nothing
	     at all: no menu, no cursor change and no sign of loading. -->
	<div
		v-else-if="!failed"
		class="pointer-events-none absolute inset-0 flex items-center justify-center"
	>
		<LoadingIndicator class="w-6 text-ink-gray-5" />
	</div>

	<!-- The chunk did not load: the user is offline, or a deploy replaced the
	     asset index. -->
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
