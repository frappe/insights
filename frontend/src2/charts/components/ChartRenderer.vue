<script setup lang="ts">
import { Button, Tooltip } from 'frappe-ui'
import { Maximize, XIcon } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { ChartRead } from '../chart_read'
import { __ } from '../../translation'
import AuthoringDrillDown from '../drill/AuthoringDrillDown.vue'
import type { ChartSegmentClick } from '../drill/segment_click'
import ChartCardFrame from './ChartCardFrame.vue'

// The chart with the affordances the builder and the SPA give it: expand, and
// drill into the rows behind a segment. The card itself is ChartCardFrame.
// `actionsRevealed`: a host whose own action is open (a portaled popover, a
// find box) has taken the pointer out of the hover group, and says so
const props = defineProps<{
	chart: ChartRead
	column?: string
	hideMaximize?: boolean
	actionsRevealed?: boolean
}>()

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

// The expanded chart opens in one of two shapes. A card that is already wide
// opens as a band, everything else opens tall. The dialog caps the width at
// `7xl` whatever we ask for, so the height is the only thing that says which.
const WIDE_RATIO = 2

const card = ref<HTMLElement>()
const expandWide = ref(false)

function expand() {
	const rect = card.value?.getBoundingClientRect()
	expandWide.value = Boolean(rect && rect.height > 0 && rect.width / rect.height > WIDE_RATIO)
	showExpandedChartDialog.value = true
}
</script>

<template>
	<div ref="card" class="group relative h-full w-full">
		<ChartCardFrame
			:chart="props.chart"
			:column="props.column"
			@segment-click="clicked = $event"
		>
			<!-- The card's own header row, and the only place acts are drawn: a
			     host that heads its page with the card — the builder — puts the
			     page's acts here, and the ones this card offers follow them in the
			     same row. A second bar in the same corner would sit on top of the
			     first. -->
			<template v-if="$slots.actions || $slots.hoverActions || canMaximize" #actions>
				<div class="flex items-center gap-1">
					<slot name="actions" />
					<!-- what the card offers over the chart it draws, read off the card
					     rather than asked for: shown on hover, so a dashboard of cards
					     is a page of pictures until one is pointed at -->
					<div
						v-if="canMaximize || $slots.hoverActions"
						class="flex gap-1 transition-opacity group-hover:opacity-100"
						:class="props.actionsRevealed ? '' : 'opacity-0'"
					>
						<slot name="hoverActions" />
						<Tooltip v-if="canMaximize" :text="__('Expand')">
							<Button variant="ghost" @click="expand()">
								<Maximize class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
							</Button>
						</Tooltip>
					</div>
				</div>
			</template>
		</ChartCardFrame>
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
			<div class="relative w-full" :class="expandWide ? 'h-[50vh]' : 'h-[75vh]'">
				<ChartCardFrame
					:chart="props.chart"
					:column="props.column"
					@segment-click="clicked = $event"
				/>
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
