<script setup lang="ts">
import { Badge, Button, Dialog, Dropdown } from 'frappe-ui'
import { ChartCard, ChartContainer } from 'frappe-ui/charts'
import { AlertTriangle, ChevronDown, ChevronRight, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { __ } from '../../translation'
import DrillBreakdown from './DrillBreakdown.vue'
import { columnLabel, type DrillLevelData, type DrillStack } from './drill_stack'
import type { ChartSegmentClick } from './segment_click'

// One card for the whole drill, with a back-stack inside it.
//
// Every crumb pops to the level it reads. Nothing is fetched twice: the stack
// holds each level's answer for as long as the dialog is open, so back and crumb
// clicks are instant.
//
// Nothing here is a destination. There is no route, nothing is persisted, and
// closing loses the stack — this is an inspection.
//
// It is a `bare` Dialog: what makes this a modal is the overlay, Esc,
// click-outside and the focus trap, and `bare` keeps all of them. What it drops
// is the header block and its padding — a 24px band between a title and the
// body, where a chart card puts six. What the drill wants above the plot is not
// a dialog title anyway. Crumbs, a grain and the way out are a toolbar.
//
// So the whole surface is one card: a toolbar, a plot, and a line under it. The
// only chrome drawn here is that toolbar. The states around the plot and the
// label naming its measure come from the chart, the way they do on a dashboard.
const props = defineProps<{
	stack: DrillStack
	title: string
	answer?: DrillLevelData
	/** the grains this level could be asked for. Empty unless it is a date. */
	grains?: readonly { label: string; value: string }[]
	loading?: boolean
	failed?: boolean
}>()

const emit = defineEmits<{
	segmentClick: [click: ChartSegmentClick]
	// eslint-disable-next-line no-unused-vars
	popTo: [depth: number]
	// eslint-disable-next-line no-unused-vars
	regrain: [granularity: string]
	/** after the dialog has gone, so the stack it held goes with it */
	closed: []
}>()

// The rows level is drawn by whoever mounted the drill: it is a query, and a
// query is the builder. A reading surface that offers no rows level passes no
// slot, and imports none of it.
//
// `actions` is what a surface may do with the drill wherever it stands, and sits
// in the title row. `level-actions` acts on the level being read, and sits in
// the pins row with the find.
defineSlots<{
	actions?: () => any
	'level-actions'?: () => any
	// eslint-disable-next-line no-unused-vars
	rows?: (props: { answer: DrillLevelData; findTarget: HTMLElement | null }) => any
}>()

const open = defineModel<boolean>({ default: false })

// The find belongs to the level's own result pane, but it is drawn up here with
// the level's own actions, out of the pane's border — the shape the query
// builder already has.
const $find = ref<HTMLElement | null>(null)

/** Whether there is a level to draw. Anything else is one of the three states. */
const ready = computed(() => !props.loading && !props.failed && Boolean(props.answer))

// A drill that will not load says so in one line. The container's own wording is
// about a chart failing to render, which is not what happened here.
const failure = computed(() =>
	!props.loading && (props.failed || !props.answer) ? __('This drill is not available') : null,
)

const action = computed(() => props.stack.current?.level.action)
const breakdown = computed(() => {
	const current = action.value
	return current && 'breakdown' in current ? current : undefined
})

// A rows level brings a find and an editor toggle with it, so the row that holds
// them is drawn even when the stack pinned nothing on the way here.
const rowsLevel = computed(() => Boolean(action.value && 'rows' in action.value))

// One crumb per level, and every one of them goes somewhere its neighbour does
// not. The chart's own name is not among them: it heads the trail as a title,
// which is what it is. A title is not a destination, and the way back to the
// chart is the close button in the same row.
//
// The stack's own crumbs, unwrapped: the trail is drawn here, so nothing has to
// be reshaped into what a Breadcrumbs component wants.
const crumbs = computed(() => props.stack.crumbs)

// A Dimension with an order of its own is read in that order, at a grain. The
// server picks one from the span it is looking at. This says which, and lets the
// reader ask for another. Nothing to choose on a ranked breakdown or on a rows level.
const ordered = computed(() => Boolean(breakdown.value && props.answer?.ordered))
const grain = computed(
	() => props.grains?.find((option) => option.value === props.answer?.granularity),
)

const grainOptions = computed(() =>
	(props.grains || []).map((option) => ({
		label: option.label,
		selected: option.value === grain.value?.value,
		onClick: () => emit('regrain', option.value),
	})),
)

/**
 * Where the server cut a breakdown, said only when it cut one. Real paging is
 * not built, so the honest thing when rows were left behind is to name the
 * bound; a level that came back whole has nothing to declare. Which few came
 * back is the level's own reading: a ranked breakdown is cut to the biggest
 * slices, and an ordered one to the most recent stretch — so one says "top" and
 * the other says "latest". A rows level says its own count, from its grid.
 */
const bound = computed(() => {
	if (!breakdown.value || !props.answer) return ''
	const shown = props.answer.rows.length
	const total = props.answer.total_row_count
	if (!total || total <= shown) return ''
	return ordered.value
		? __('latest {0} of {1} periods', shown.toLocaleString(), total.toLocaleString())
		: __('top {0} of {1} groups', shown.toLocaleString(), total.toLocaleString())
})
</script>

<template>
	<Dialog v-model:open="open" size="5xl" bare @after-leave="emit('closed')">
		<template #default="{ close }">
			<!-- `px-4 py-3` is a chart card's own padding.

			     The height does not follow what is drawn: a box that resized as the
			     reader descended would move the plot out from under the pointer. It
			     is tall enough for a ranking at the server's bound, and still short
			     enough for a laptop. -->
			<div class="flex h-[clamp(24rem,60vh,40rem)] w-full flex-col gap-2 px-4 py-3">
				<!-- The card's title row, and the whole of where the reader is: the
				     chart's name and every level under it, in one trail at one type
				     size and one ink.

				     Hand-rolled rather than `Breadcrumbs`, which carries a type scale
				     of its own and would set the trail against the title it continues.
				     Only what goes somewhere is a button: the chart's name navigates
				     nowhere, and neither does the last crumb, which is where the
				     reader already stands. Closing is the button at the end of the row.

				     The trail starts at the padding edge, in line with the plot's
				     y-axis. Nothing sits in front of it — that is why there is no back
				     button, and with one crumb per level the crumb before the last is
				     already the way back. -->
				<div class="flex min-w-0 flex-shrink-0 items-center gap-2">
					<div class="flex min-w-0 items-center gap-1.5 text-p-base text-ink-gray-8">
						<span class="truncate">{{ props.title }}</span>
						<template v-for="(crumb, index) in crumbs" :key="crumb.depth">
							<ChevronRight
								class="h-3.5 w-3.5 flex-shrink-0 text-ink-gray-4"
								stroke-width="1.5"
							/>
							<span v-if="index === crumbs.length - 1" class="max-w-48 truncate">
								{{ crumb.label }}
							</span>
							<button
								v-else
								class="max-w-48 truncate hover:underline"
								@click="emit('popTo', crumb.depth)"
							>
								{{ crumb.label }}
							</button>
						</template>
						<!-- the grain the last crumb is read at, after the crumb it
						     qualifies: part of where the reader is, not an action on it -->
						<Dropdown v-if="ordered && grainOptions.length" :options="grainOptions">
							<button
								class="flex flex-shrink-0 items-center gap-0.5 text-ink-gray-5 hover:text-ink-gray-7"
							>
								{{ grain?.label || __('Grain') }}
								<ChevronDown class="h-3.5 w-3.5" stroke-width="1.5" />
							</button>
						</Dropdown>
					</div>

					<!-- what a surface may do with the drill wherever it stands, next
					     to the way out. Empty on a reading surface, which has nothing to
					     offer beyond the stack. -->
					<div class="ml-auto flex flex-shrink-0 items-center gap-1 pl-2">
						<slot name="actions" />
						<!-- `bare` draws no close button of its own, which is the point:
						     the way out belongs in this row with the other actions. -->
						<Button variant="ghost" :tooltip="__('Close')" @click="close">
							<template #icon>
								<X class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</template>
						</Button>
					</div>
				</div>

				<!-- What the stack has pinned to get the reader here, and what can be
				     done to the level they are reading. A row of its own, under the
				     trail rather than in it: a crumb is somewhere to go, a pin is
				     something that is true, and reading them as one line is what made
				     the two hard to tell apart.

				     Each pin names its column. "FY 2024-25" and "Lighting" say nothing
				     about what they are values of, and a reader three levels down has
				     no way left to ask.

				     `h-7` because the row holds chips on some levels and buttons on
				     others, and a row that took its height from what landed in it
				     would move the plot as the reader descends.

				     This row is where a chart's own filters would surface, if charts
				     grow a filter affordance of their own. -->
				<div
					v-if="stack.pins.length || rowsLevel"
					class="flex h-7 flex-shrink-0 items-center gap-1.5"
				>
					<Badge v-for="(pin, index) in stack.pins" :key="`${index}-${pin.column}`">
						<span class="text-ink-gray-5">{{ columnLabel(pin.column) }}</span>
						<span class="ml-1 text-ink-gray-7">{{ pin.value }}</span>
					</Badge>

					<div class="ml-auto flex flex-shrink-0 items-center gap-1 pl-2">
						<!-- `contents` so an empty host on a breakdown level takes no
						     space and adds no gap of its own -->
						<div ref="$find" class="contents"></div>
						<slot name="level-actions" />
					</div>
				</div>

				<div class="min-h-0 flex-1">
					<template v-if="ready">
						<DrillBreakdown
							v-if="breakdown"
							:answer="props.answer!"
							:dimension="breakdown.breakdown"
							@segment-click="emit('segmentClick', $event)"
						/>
						<slot v-else name="rows" :answer="props.answer!" :find-target="$find" />
					</template>

					<!-- Every state but the answer, from the same component a card
					     draws them with. The placeholder holds the shape of the plot
					     rather than turning a spinner in an empty box. -->
					<ChartCard v-else class="h-full" :card="false">
						<ChartContainer :loading="props.loading" :error="failure" :empty="true">
							<template #error>
								<div class="flex items-center gap-1.5 text-p-base text-ink-gray-5">
									<AlertTriangle
										class="h-3.5 w-3.5 shrink-0 text-ink-red-5"
										stroke-width="1.5"
									/>
									<span>{{ failure }}</span>
								</div>
							</template>
						</ChartContainer>
					</ChartCard>
				</div>

				<p v-if="ready && bound" class="flex-shrink-0 text-p-sm text-ink-gray-5">
					{{ bound }}
				</p>
			</div>
		</template>
	</Dialog>
</template>
