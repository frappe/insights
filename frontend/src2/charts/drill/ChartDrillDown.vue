<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getErrorMessage } from '../../helpers'
import { __ } from '../../translation'
import { breakdownChart } from './breakdown_chart'
import DrillDialog from './DrillDialog.vue'
import DrillMenu from './DrillMenu.vue'
import {
	breakdownCandidates,
	columnLabel,
	declaredDimensionColumns,
	grainsFor,
	makeDrillStack,
	segmentOf,
	type DrillAction,
	type DrillChart,
	type DrillDimension,
	type DrillLevel,
	type DrillLevelData,
	type DrillSegment,
	type DrillSubject,
} from './drill_stack'
import type { ChartSegmentClick } from './segment_click'

// The drill, as a surface offers it: a menu where the reader pointed, and one
// dialog behind whichever item they chose.
//
// A surface mounts this and hands over what was clicked. Everything past that
// lives here and dies with it, so closing is all it takes to forget the stack.
// The subject owns which endpoint answers a level. Nothing here knows whether a
// chart was ever saved.
//
// `#actions` is what a surface may add next to the close button, on any level;
// `#rows` renders the rows level. They are slots, not props, so that builder
// actions and their imports stay out of a View.
const props = defineProps<{
	/** what is being drilled: the shape a click is read against, and the endpoint */
	subject: DrillSubject
	clicked: ChartSegmentClick
}>()

const emit = defineEmits<{ close: [] }>()

defineSlots<{
	// eslint-disable-next-line no-unused-vars
	actions?: (props: { answer: DrillLevelData }) => any
	rows?: (props: {
		// eslint-disable-next-line no-unused-vars
		answer: DrillLevelData
		// eslint-disable-next-line no-unused-vars
		levels: DrillLevel[]
		// eslint-disable-next-line no-unused-vars
		findTarget: HTMLElement | null
	}) => any
}>()

const stack = makeDrillStack()
const open = ref(false)
const answer = ref<DrillLevelData>()
const loading = ref(false)
const failed = ref<string>()
// The server refused the level: the reader cannot read the data behind it, so
// nothing ran. It is an answer, not a failure, and there is nothing to retry. So
// it is kept apart from `failed` and shown as its own state.
const refused = ref<string[]>()

const pending = ref<{ segment: DrillSegment; point: { x: number; y: number } }>()

// The level being read is the chart a click inside the dialog is read against.
// A rows level has nothing to click, so there is nothing to read it against.
const clickedChart = computed<DrillChart>(() => {
	const action = stack.current?.level.action
	if (action && 'breakdown' in action) {
		return breakdownChart(action.breakdown, answer.value || { columns: [], rows: [] })
	}
	return props.subject.chart
})

// The grains the level being read can be asked for. A breakdown of anything but
// a date has none, and the dialog draws no control where there is nothing to
// choose between.
const grains = computed(() => {
	const action = stack.current?.level.action
	if (!action || !('breakdown' in action)) return []
	return grainsFor(props.subject.dimensions, action.breakdown)
})

const candidates = computed<DrillDimension[]>(() =>
	breakdownCandidates(
		props.subject.dimensions,
		[...stack.pinnedColumns, ...(pending.value?.segment.pins || []).map((pin) => pin.column)],
		declaredDimensionColumns(props.subject.chart),
	),
)

function offerMenu(click: ChartSegmentClick, chart: DrillChart) {
	pending.value = { segment: segmentOf(chart, click.target), point: click.point }
}

// A surface can hand a live instance a new click, as the query builder does when
// a second click lands before the first one's round trip is back.
watch(
	() => props.clicked,
	(click) => offerMenu(click, props.subject.chart),
	{ immediate: true },
)

function descend(action: DrillAction) {
	const offered = pending.value
	if (!offered) return
	pending.value = undefined

	stack.push({
		level: {
			segment_filters: offered.segment.filters,
			action,
			drawn_on: props.subject.drawnOn,
			// the chart as the card showed it, so the server refuses a drill if it
			// changed since
			modified: props.subject.modified,
		},
		pins: offered.segment.pins,
		actionLabel: 'rows' in action ? __('Rows') : __('by {0}', columnLabel(action.breakdown)),
	})
	open.value = true
	load()
}

function chooseRows() {
	descend({ rows: true, measure: pending.value?.segment.measure })
}

function chooseBreakdown(dimension: DrillDimension) {
	descend({ breakdown: dimension.name, measure: pending.value?.segment.measure })
}

// With no dialog open, dismissing the menu ends the drill.
function dismissMenu() {
	pending.value = undefined
	if (!open.value) emit('close')
}

// A grain is a different question about the same level, so it re-asks the level
// instead of descending. The reader stays exactly where they are.
function regrain(granularity: string) {
	stack.regrain(granularity)
	load()
}

// A crumb is the level it names, counted from one, so there is no crumb for the
// card the reader started on and no depth of zero to close the dialog on.
function popTo(depth: number) {
	stack.popTo(depth)
	load()
}

// Every load claims the answer slot, cached or not: a pop that costs nothing
// still has to disown a request that is still out, or its rows would land under
// the level the reader popped back to.
let inFlight = 0
async function load() {
	const token = ++inFlight

	// a level already answered for costs nothing to return to
	const cached = stack.answer()
	if (cached) {
		answer.value = cached
		loading.value = false
		failed.value = undefined
		refused.value = undefined
		return
	}

	loading.value = true
	failed.value = undefined
	refused.value = undefined
	try {
		const fetched = await props.subject.fetch(stack.levels)
		if (token !== inFlight) return
		// nothing ran, so there is no level to cache and no empty result to show
		if (fetched.not_permitted) {
			refused.value = fetched.not_permitted.doctypes || []
			answer.value = undefined
			return
		}
		stack.remember(fetched)
		answer.value = fetched
	} catch (error) {
		if (token !== inFlight) return
		console.error('[insights] Could not drill down.', error)
		// the server's message, if it sent one: when the chart changed after the
		// card loaded, only a Refresh fixes it
		failed.value = getErrorMessage(error)
		answer.value = undefined
	} finally {
		if (token === inFlight) loading.value = false
	}
}
</script>

<template>
	<DrillMenu
		v-if="pending"
		:point="pending.point"
		:dimensions="candidates"
		:can-rows="props.subject.canRows !== false"
		@rows="chooseRows"
		@breakdown="chooseBreakdown"
		@close="dismissMenu"
	/>

	<!-- Both ways out are the same way out: nothing here is kept, so once the
	     dialog is gone the surface is back to where it started. -->
	<DrillDialog
		v-model="open"
		:stack="stack"
		:title="props.subject.title"
		:answer="answer"
		:grains="grains"
		:loading="loading"
		:failed="failed"
		:refused="refused"
		@segment-click="(click) => offerMenu(click, clickedChart)"
		@regrain="regrain"
		@retry="load"
		@pop-to="popTo"
		@closed="emit('close')"
	>
		<template v-if="answer" #actions>
			<slot name="actions" :answer="answer" />
		</template>

		<template #rows="{ answer: level, levels, findTarget }">
			<slot name="rows" :answer="level" :levels="levels" :find-target="findTarget" />
		</template>
	</DrillDialog>
</template>
