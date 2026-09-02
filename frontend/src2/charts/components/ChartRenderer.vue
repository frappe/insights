<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Maximize, XIcon } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { ChartRead } from '../chart_read'
import AuthoringDrillDown from '../drill/AuthoringDrillDown.vue'
import type { ChartSegmentClick } from '../drill/segment_click'
import ChartCardFrame from './ChartCardFrame.vue'

// The chart with the affordances the builder and the SPA give it: expand, and
// drill into the rows behind a segment. The card itself is ChartCardFrame.
const props = defineProps<{ chart: ChartRead; hideMaximize?: boolean }>()

// The author's drill is the reader's drill plus "open as query" — one dialog,
// two feeds. What the card's store was built from decides which endpoint answers
// a level, so nothing here says.
const clicked = ref<ChartSegmentClick>()
// a new card is a new drill: the stack belongs to the click that started it
watch(
	() => props.chart,
	() => (clicked.value = undefined),
)

const showExpandedChartDialog = ref(false)
const canMaximize = computed(
	() => !props.hideMaximize && props.chart && props.chart.doc.chart_type !== 'Number',
)
</script>

<template>
	<div class="group relative h-full w-full">
		<ChartCardFrame :chart="props.chart" @segment-click="clicked = $event" />

		<div
			v-if="canMaximize"
			class="absolute top-0 right-0 p-2 opacity-0 transition-opacity group-hover:opacity-100"
		>
			<Button variant="ghost" @click="showExpandedChartDialog = true">
				<Maximize class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
			</Button>
		</div>
	</div>

	<!-- keyed on the click, so every drill starts from an empty stack -->
	<AuthoringDrillDown
		v-if="clicked"
		:subject="props.chart.drillSubject"
		:clicked="clicked"
		:adhoc-filters="props.chart.routedFilters"
		@close="clicked = undefined"
	/>

	<Dialog v-if="chart" v-model:open="showExpandedChartDialog" size="7xl" bare>
		<template #default>
			<div class="h-[85vh] w-full">
				<ChartCardFrame :chart="props.chart" @segment-click="clicked = $event" />
				<div class="absolute top-2 right-2">
					<Button variant="ghost" @click="showExpandedChartDialog = false">
						<template #icon>
							<XIcon class="size-4 text-ink-gray-6" />
						</template>
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
