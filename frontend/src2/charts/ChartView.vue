<script setup lang="ts">
import { Button, Dialog, Tooltip } from 'frappe-ui'
import { AlertTriangle, Maximize, XIcon } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { __ } from '../translation'
import type { ChartRead } from './chart_view'
import ChartChrome from './components/ChartChrome.vue'
import ViewDrillDown from './drill/ViewDrillDown.vue'
import type { ChartSegmentClick } from './drill/segment_click'

// The page passes the read in. Several cells can show one chart (a Number chart
// has one cell per reading), and they share one request for rows.
//
// A host that frames the chart itself, such as a desk widget, fills the default
// slot with the body alone. It keeps the drill and gets no second border.
//
// The drill is a slot because the two drills import different code. A reader's
// drill loads on the click that opens it. An author's drill can also add a level
// to the workbook as a query.
const props = withDefaults(
	defineProps<{
		// undefined while the page loads, or when the cell's chart no longer exists
		chart?: ChartRead
		reading?: string
		// whether a filter applies to this card, so an empty card can say why
		filtered?: boolean
		/**
		 * True for a reader, who cannot act on the rows: sorting needs a query, and
		 * a reader cannot run one. It also selects the reader's wording of each
		 * message.
		 */
		readonly?: boolean
		hideMaximize?: boolean
		/**
		 * Set while a host action is open, such as a portaled popover or a find box.
		 * The pointer is then outside the hover group, so the actions stay visible.
		 */
		actionsRevealed?: boolean
	}>(),
	{ readonly: true },
)

const emit = defineEmits<{ resetFilters: [] }>()

// The read says whether the chart can be drilled. Guest cannot, and the endpoint
// refuses Guest too. This check keeps the app from showing a drill that the
// server would refuse.
const clicked = ref<ChartSegmentClick>()
function onSegmentClick(click: ChartSegmentClick) {
	if (!props.chart?.drillable) return
	clicked.value = click
}

// A new chart closes the drill: the stack belongs to the click that started it.
watch(
	() => props.chart,
	() => (clicked.value = undefined),
)

// A Number card shows a reading, not a plot, so expanding it shows nothing more.
const canMaximize = computed(
	() => !props.hideMaximize && Boolean(props.chart) && props.chart?.doc.chart_type !== 'Number',
)

// The expanded chart opens short for a wide card and tall for any other. The
// dialog caps the width at `7xl` in both cases, so only the height differs.
const WIDE_RATIO = 2

const card = ref<HTMLElement>()
const expanded = ref(false)
const expandWide = ref(false)

function expand() {
	const rect = card.value?.getBoundingClientRect()
	expandWide.value = Boolean(rect && rect.height > 0 && rect.width / rect.height > WIDE_RATIO)
	expanded.value = true
}

// Hidden actions get zero width, not transparency: a transparent action still
// takes width from the title. They are not `hidden`, because that removes them
// from the tab order, and on most cards nothing else can take focus to reveal
// them. The group is named `card` because the grid cell around it is also a
// group, and a bare `group-hover` would react to the cell and its gutter.
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
				<!-- The card's header row, and the only place for actions. A host that
				     uses the card as its page header, such as the builder, puts its
				     page actions here, and the card's own actions follow in the same
				     row. A second bar in the same corner would overlap the first.

				     While the expanded dialog is open, it renders this row instead.
				     The actions hold state the host owns, so mounting them twice
				     would bind one model in two places. -->
				<template
					v-if="!expanded && ($slots.actions || $slots.hoverActions || canMaximize)"
					#actions
				>
					<div class="flex items-center gap-1">
						<slot name="actions" :expanded="false" />
						<!-- shown on hover, so a dashboard shows only charts until
						     the user points at one -->
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

		<!-- not a card state: a cell that names no chart has no store to be
		     loading, failed or empty. The layout is wrong, not the read. -->
		<div
			v-else
			class="flex h-full flex-1 flex-col items-center justify-center rounded-4 border border-outline-gray-2"
		>
			<div class="flex items-center gap-1.5 text-p-base text-ink-gray-4">
				<AlertTriangle class="h-3.5 w-3.5 shrink-0 text-ink-red-5" stroke-width="1.5" />
				<span>{{ __('Chart not found') }}</span>
			</div>
		</div>

		<!-- The drill mounts in the box the reader clicked: the card or the
		     expanded dialog. Its placeholder positions itself against the box
		     that contains it, and the drill dialog renders over an overlay
		     that covers this card. -->
		<slot v-if="!expanded" name="drill" :clicked="clicked" :close="() => (clicked = undefined)">
			<ViewDrillDown
				v-if="clicked && chart"
				:subject="chart.drillSubject"
				:clicked="clicked"
				@close="clicked = undefined"
			/>
		</slot>
	</div>

	<!-- The same card, expanded. It renders outside the card's box, so no action
	     hides behind a hover: the pointer is already over the dialog. -->
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
							<!-- `expanded` tells the host not to hide its actions behind
							     a hover: the hover group is the card, and the dialog
							     renders outside it -->
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
