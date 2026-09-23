<script setup lang="ts">
import { Button, Dialog, Tooltip } from 'frappe-ui'
import { AlertTriangle, Maximize, XIcon } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { __ } from '../translation'
import type { ChartRead } from './chart_view'
import ChartChrome from './components/ChartChrome.vue'
import ViewDrillDown from './drill/ViewDrillDown.vue'
import type { ChartSegmentClick } from './drill/segment_click'

// One chart in a card, wherever Insights draws one: a dashboard grid, a public
// link, a desk widget, the chart builder. The card is the whole of it — the
// chrome, the acts beside the title, the hover rule that hides them, and the
// same card given the screen.
//
// The read is handed over rather than made here, because several cells can draw
// one chart — a Number chart is one cell per reading — and the rows behind them
// are one request. Whoever owns the page owns the read.
//
// It draws an Insights card by default and offers the chart to whoever wants a
// different frame. A host that frames the chart itself — a desk widget — fills
// the slot with the body alone, and gets the same drill without a second border
// around it.
//
// The drill is a slot because of what each one imports. A reader's drill loads
// on the click that opens it; an author's adds a level to the workbook as a
// query. `ChartRenderer` is this card with that drill in the
// slot, and nothing else.
const props = withDefaults(
	defineProps<{
		// absent while the page is still loading, and for a cell naming a chart that
		// is no longer there
		chart?: ChartRead
		/** Which reading to draw, for a Number chart. */
		reading?: string
		// whether a filter currently reaches this card, so an empty one can say why
		filtered?: boolean
		/**
		 * Whether the card's reader may act on the rows. A reader cannot: sorting
		 * is a query, and a reader has no way to ask for one. It is also what picks
		 * the reader's half of every message the chart has.
		 */
		readonly?: boolean
		/** A surface that draws the chart at full size already has nowhere to expand to. */
		hideMaximize?: boolean
		/**
		 * A host whose own act is open — a portaled popover, a find box — has taken
		 * the pointer out of the hover group, and says so.
		 */
		actionsRevealed?: boolean
	}>(),
	{ readonly: true },
)

const emit = defineEmits<{ resetFilters: [] }>()

// The read says whether a drill leads anywhere: an anonymous reader is not
// offered one, and the endpoint refuses Guest as well. This check keeps the app
// from drawing a control that would only answer with a refusal.
const clicked = ref<ChartSegmentClick>()
function onSegmentClick(click: ChartSegmentClick) {
	if (!props.chart?.drillable) return
	clicked.value = click
}

// A new card is a new drill: the stack belongs to the click that started it.
watch(
	() => props.chart,
	() => (clicked.value = undefined),
)

// The picture, bigger: what a card on a grid offers over the chart it draws. A
// Number card is a reading rather than a plot, so it is the one type with
// nothing more to show.
const canMaximize = computed(
	() => !props.hideMaximize && Boolean(props.chart) && props.chart?.doc.chart_type !== 'Number',
)

// The expanded chart opens in one of two shapes. A card that is already wide
// opens as a band, everything else opens tall. The dialog caps the width at
// `7xl` whatever we ask for, so the height is the only thing that says which.
const WIDE_RATIO = 2

const card = ref<HTMLElement>()
const expanded = ref(false)
const expandWide = ref(false)

function expand() {
	const rect = card.value?.getBoundingClientRect()
	expandWide.value = Boolean(rect && rect.height > 0 && rect.width / rect.height > WIDE_RATIO)
	expanded.value = true
}

// Hidden acts get zero width, not transparency, because a transparent act still
// takes its width from the title. They are not `hidden`, because a hidden act
// leaves the tab order, and on most cards nothing else can take focus to show
// it. The group is the card and is named: the grid cell around it is a group
// too, and a bare `group-hover` would answer to the cell and its gutter.
const HIDDEN_UNTIL_POINTED_AT =
	'w-0 overflow-hidden group-focus-within/card:w-auto group-focus-within/card:overflow-visible group-hover/card:w-auto group-hover/card:overflow-visible'
</script>

<template>
	<div ref="card" class="group/card relative h-full w-full">
		<slot v-if="chart" :chart="chart" :on-segment-click="onSegmentClick">
			<ChartChrome
				:chart="chart"
				:reading="props.reading"
				:readonly="props.readonly"
				:filtered="props.filtered"
				@segment-click="onSegmentClick"
				@reset-filters="emit('resetFilters')"
			>
				<!-- The card's own header row, and the only place acts are drawn: a
				     host that heads its page with the card — the builder — puts the
				     page's acts here, and the ones this card offers follow them in the
				     same row. A second bar in the same corner would sit on top of the
				     first.

				     While the expanded dialog is up it draws this same row, and the
				     acts in it hold state the host owns: mounted twice they would
				     answer one model from two places. -->
				<template
					v-if="!expanded && ($slots.actions || $slots.hoverActions || canMaximize)"
					#actions
				>
					<div class="flex items-center gap-1">
						<slot name="actions" :expanded="false" />
						<!-- shown on hover, so a dashboard of cards is a page of
						     pictures until one is pointed at -->
						<div
							v-if="canMaximize || $slots.hoverActions"
							class="flex gap-1"
							:class="props.actionsRevealed ? '' : HIDDEN_UNTIL_POINTED_AT"
						>
							<slot name="hoverActions" />
							<Tooltip v-if="canMaximize" :text="__('Expand')">
								<Button
									variant="ghost"
									:aria-label="__('Expand')"
									@click="expand()"
								>
									<Maximize
										class="h-3.5 w-3.5 text-ink-gray-6"
										stroke-width="1.5"
									/>
								</Button>
							</Tooltip>
						</div>
					</div>
				</template>
			</ChartChrome>
		</slot>

		<!-- not one of the card's states: a cell that names no chart has no store
		     to be loading, failed or empty. The layout is wrong, not a read. -->
		<div
			v-else
			class="flex h-full flex-1 flex-col items-center justify-center rounded-4 border border-outline-gray-2"
		>
			<div class="flex items-center gap-1.5 text-p-base text-ink-gray-4">
				<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
				<span>{{ __('Chart not found') }}</span>
			</div>
		</div>

		<!-- The drill waits, and says so, over the box that was clicked in — so it
		     is mounted in whichever of the two boxes the reader is looking at. A
		     placeholder is positioned against the box that contains it, and the
		     dialog below is drawn over an overlay this card is under. -->
		<slot v-if="!expanded" name="drill" :clicked="clicked" :close="() => (clicked = undefined)">
			<ViewDrillDown
				v-if="clicked && chart"
				:subject="chart.drillSubject"
				:clicked="clicked"
				@close="clicked = undefined"
			/>
		</slot>
	</div>

	<!-- The same card, given the screen. It is drawn outside the card's box, so
	     nothing in it hides behind a hover: the dialog is already pointed at. -->
	<Dialog v-if="chart && canMaximize" v-model:open="expanded" size="7xl" bare>
		<template #default>
			<div class="relative w-full" :class="expandWide ? 'h-[50vh]' : 'h-[75vh]'">
				<ChartChrome
					:chart="chart"
					:reading="props.reading"
					:readonly="props.readonly"
					:filtered="props.filtered"
					@segment-click="onSegmentClick"
					@reset-filters="emit('resetFilters')"
				>
					<template #actions>
						<div class="flex items-center gap-1">
							<!-- `expanded` is how the host knows not to hide its acts
							     behind a hover: the group that reveals them is the card,
							     and the dialog is drawn outside it -->
							<slot name="actions" :expanded="true" />
							<slot name="hoverActions" />
							<Button
								variant="ghost"
								:aria-label="__('Close')"
								@click="expanded = false"
							>
								<template #icon>
									<XIcon class="size-4 text-ink-gray-6" />
								</template>
							</Button>
						</div>
					</template>
				</ChartChrome>

				<slot
					v-if="expanded"
					name="drill"
					:clicked="clicked"
					:close="() => (clicked = undefined)"
				>
					<ViewDrillDown
						v-if="clicked && chart"
						:subject="chart.drillSubject"
						:clicked="clicked"
						@close="clicked = undefined"
					/>
				</slot>
			</div>
		</template>
	</Dialog>
</template>
