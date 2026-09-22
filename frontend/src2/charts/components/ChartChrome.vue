<script setup lang="ts">
import { Button, Dialog, Tooltip } from 'frappe-ui'
import { ChartCard } from 'frappe-ui/charts'
import { Maximize, XIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { __ } from '../../translation'
import { drawsOwnCards } from '../adapter'
import { ChartRead } from '../chart_read'
import type { ChartSegmentClick } from '../drill/segment_click'
import ChartBody from './ChartBody.vue'

// The chrome an Insights surface puts a chart in: the surface, the title, expand,
// and whatever the surface puts beside the title through `#actions`. Inside it is
// ChartBody, which draws the chart and nothing else, so a host with chrome of
// its own — a desk island — mounts the body instead and gets no second border
// and no second title.
// `actionsRevealed`: a host whose own action is open (a portaled popover, a
// find box) has taken the pointer out of the hover group, and says so
const props = defineProps<{
	chart: ChartRead
	/** Which reading to draw, for a Number Chart. See `ChartBody`. */
	reading?: string
	readonly?: boolean
	filtered?: boolean
	hideMaximize?: boolean
	actionsRevealed?: boolean
}>()

const emit = defineEmits<{
	segmentClick: [click: ChartSegmentClick]
	resetFilters: []
}>()

const card = computed(() => !drawsOwnCards(props.chart.doc.chart_type))

const showExpandedChartDialog = ref(false)
const canMaximize = computed(() => !props.hideMaximize && props.chart.doc.chart_type !== 'Number')

// The expanded chart opens in one of two shapes. A card that is already wide
// opens as a band, everything else opens tall. The dialog caps the width at
// `7xl` whatever we ask for, so the height is the only thing that says which.
const WIDE_RATIO = 2

const root = ref<HTMLElement>()
const expandWide = ref(false)

function expand() {
	const rect = root.value?.getBoundingClientRect()
	expandWide.value = Boolean(rect && rect.height > 0 && rect.width / rect.height > WIDE_RATIO)
	showExpandedChartDialog.value = true
}
</script>

<template>
	<div ref="root" class="group relative flex h-full w-full flex-col">
		<div class="min-h-0 w-full flex-1">
			<!-- `--chart-card-inset` is this card's own horizontal padding, named so
			     that a filler running to the card edge measures against it. Unset,
			     which is what a body with no card around it reads, the bleed is
			     nothing. -->
			<ChartCard
				class="h-full border-outline-gray-2"
				:class="card ? '[--chart-card-inset:1rem]' : undefined"
				:card="card"
			>
				<ChartBody
					:chart="props.chart"
					:title="props.chart.doc.title"
					:reading="props.reading"
					:readonly="props.readonly"
					:filtered="props.filtered"
					@segment-click="emit('segmentClick', $event)"
					@reset-filters="emit('resetFilters')"
				>
					<!-- The card's own header row, and the only place acts are drawn: a
					     host that heads its page with the card — the builder — puts the
					     page's acts here, and the ones this card offers follow them in the
					     same row. A second bar in the same corner would sit on top of the
					     first. -->
					<!-- while the expanded dialog is up it draws this same row, and the acts
					     in it hold state the host owns: mounted twice they would answer the
					     same model from two places -->
					<template
						v-if="
							!showExpandedChartDialog &&
							($slots.actions || $slots.hoverActions || canMaximize)
						"
						#actions
					>
						<div class="flex items-center gap-1">
							<slot name="actions" :expanded="false" />
							<!-- what the card offers over the chart it draws, read off the card
							     rather than asked for: shown on hover, so a dashboard of cards
							     is a page of pictures until one is pointed at. Hidden acts get zero
							     width, not transparency, because a transparent act still takes its
							     width from the title. They are not `hidden`, because a hidden act
							     leaves the tab order, and on most cards nothing else can take focus
							     to show it -->
							<div
								v-if="canMaximize || $slots.hoverActions"
								class="flex gap-1"
								:class="
									props.actionsRevealed
										? ''
										: 'w-0 overflow-hidden group-focus-within:w-auto group-focus-within:overflow-visible group-hover:w-auto group-hover:overflow-visible'
								"
							>
								<slot name="hoverActions" />
								<Tooltip v-if="canMaximize" :text="__('Expand')">
									<Button variant="ghost" @click="expand()">
										<Maximize
											class="h-3.5 w-3.5 text-ink-gray-6"
											stroke-width="1.5"
										/>
									</Button>
								</Tooltip>
							</div>
						</div>
					</template>
				</ChartBody>
			</ChartCard>
		</div>
	</div>

	<Dialog v-if="canMaximize" v-model:open="showExpandedChartDialog" size="7xl" bare>
		<template #default>
			<div class="relative w-full" :class="expandWide ? 'h-[50vh]' : 'h-[75vh]'">
				<!-- the same header row as the card, with close where expand was:
				     nothing here hides behind hover, the dialog is already pointed at -->
				<ChartChrome
					:chart="props.chart"
					:reading="props.reading"
					:readonly="props.readonly"
					:filtered="props.filtered"
					hide-maximize
					@segment-click="emit('segmentClick', $event)"
					@reset-filters="emit('resetFilters')"
				>
					<template #actions>
						<div class="flex items-center gap-1">
							<!-- `expanded` is how the host knows not to hide its acts behind a
							     hover: the group that reveals them is the card, and the dialog
							     is drawn outside it -->
							<slot name="actions" :expanded="true" />
							<slot name="hoverActions" />
							<Button variant="ghost" @click="showExpandedChartDialog = false">
								<template #icon>
									<XIcon class="size-4 text-ink-gray-6" />
								</template>
							</Button>
						</div>
					</template>
				</ChartChrome>
			</div>
		</template>
	</Dialog>
</template>
