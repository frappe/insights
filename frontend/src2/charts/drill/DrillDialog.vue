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
// body, where a chart card puts six. Above the plot the drill needs a toolbar —
// crumbs, grain, close — not a dialog title.
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
	/** ask the level again, for a reader whose only way out was closing the card */
	retry: []
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

// The find belongs to the level's result pane, but the dialog draws it here with
// the level actions, outside the pane border — the shape the query builder
// already has.
const $find = ref<HTMLElement | null>(null)

/** Whether there is a level to draw. Anything else is one of the three states. */
const ready = computed(() => !props.loading && !props.failed && Boolean(props.answer))

// A drill that will not load says so in one line. `ChartContainer`'s own wording is
// about a chart failing to render, which is not what happened here.
const failure = computed(() =>
	!props.loading && (props.failed || !props.answer) ? __('This drill is not available') : null,
)

const action = computed(() => props.stack.current?.level.action)
const breakdown = computed(() => {
	const current = action.value
	return current && 'breakdown' in current ? current : undefined
})

// One crumb per level. The chart's name heads the trail as a title, not a crumb
// — the way back to the chart is the close button.
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
 * not built, so when the server drops rows, name the bound. A level that came
 * back whole has nothing to declare. Which few came back is the level's own
 * reading: a ranked breakdown is cut to the biggest segments, and an ordered one
 * to the most recent stretch — so one says "top" and the other says "latest".
 * A rows level says its own count, from its grid.
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
								class="max-w-48 truncate rounded-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
								@click="emit('popTo', crumb.depth)"
							>
								{{ crumb.label }}
							</button>
						</template>
						<!-- the grain the last crumb is read at, after the crumb it
						     qualifies: part of where the reader is, not an action on it -->
						<Dropdown v-if="ordered && grainOptions.length" :options="grainOptions">
							<button
								class="flex flex-shrink-0 items-center gap-0.5 rounded-4 text-ink-gray-5 hover:text-ink-gray-7 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							>
								{{ grain?.label || __('Grain') }}
								<ChevronDown class="h-3.5 w-3.5" stroke-width="1.5" />
							</button>
						</Dropdown>
					</div>

					<!-- what a surface may do with the drill wherever it stands, next
					     to the close button. Empty on a reading surface, which has
					     nothing to offer beyond the stack. -->
					<div class="ml-auto flex flex-shrink-0 items-center gap-1 pl-2">
						<slot name="actions" />
						<!-- `bare` draws no close button, so close belongs in this row
						     with the other actions. -->
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

				     Drawn on every level, empty where the level pinned nothing and
				     offers nothing: `h-7` fixes the height, and a row that came and
				     went would move the plot as the reader descends. -->
				<div class="flex h-7 min-w-0 flex-shrink-0 items-center gap-1.5">
					<!-- a pin is capped and ellipsised the way a crumb is: a Heatmap or
					     a Sankey click pins two, and a long value clipped mid-word
					     reads as a different value -->
					<Badge
						v-for="(pin, index) in stack.pins"
						:key="`${index}-${pin.column}`"
						class="min-w-0"
					>
						<span class="max-w-32 truncate text-ink-gray-5">
							{{ columnLabel(pin.column) }}
						</span>
						<span class="ml-1 max-w-48 truncate text-ink-gray-7">{{ pin.value }}</span>
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
								<div class="flex flex-col items-center gap-2">
									<div
										class="flex items-center gap-1.5 text-p-base text-ink-gray-5"
									>
										<AlertTriangle
											class="h-3.5 w-3.5 shrink-0 text-ink-red-5"
											stroke-width="1.5"
										/>
										<span>{{ failure }}</span>
									</div>
									<!-- the first level has no crumb to go back to, so
									     without this the only way out is closing the card -->
									<Button
										variant="outline"
										:label="__('Retry')"
										@click="emit('retry')"
									/>
								</div>
							</template>
						</ChartContainer>
					</ChartCard>
				</div>

				<!-- Drawn on every level, empty where the level has nothing to
				     declare. A line that came and went as the reader descended would
				     take its height out of the plot, which is what `h-7` above keeps
				     the pins row from doing. -->
				<p class="h-4 flex-shrink-0 text-p-sm leading-4 text-ink-gray-5">
					{{ ready ? bound : '' }}
				</p>
			</div>
		</template>
	</Dialog>
</template>
