<script setup lang="ts">
import { computed, ref } from 'vue'
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
// Which door the levels come through is the subject's business. Nothing here
// knows whether a chart was ever saved.
//
// `#actions` is what a surface may add next to the way out, on any level;
// `#level-actions` acts on the level being read and is drawn in the pins row
// beside the find. `#rows` is how the surface draws the rows level. Slots rather
// than props so that an authoring affordance and everything it imports — the
// whole query editor, for the rows level — stay out of a surface that only
// reads.
const props = defineProps<{
	/** what is being drilled: the shape a click is read against, and the door */
	subject: DrillSubject
	/** the click that opened this */
	clicked: ChartSegmentClick
}>()

const emit = defineEmits<{ close: [] }>()

defineSlots<{
	// eslint-disable-next-line no-unused-vars
	actions?: (props: { answer: DrillLevelData; rows: boolean }) => any
	// eslint-disable-next-line no-unused-vars
	'level-actions'?: (props: { answer: DrillLevelData }) => any
	// eslint-disable-next-line no-unused-vars
	rows?: (props: { answer: DrillLevelData; findTarget: HTMLElement | null }) => any
}>()

const stack = makeDrillStack()
const open = ref(false)
const answer = ref<DrillLevelData>()
const loading = ref(false)
const failed = ref(false)

// what the menu is currently offering to split, and where it is drawn
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

const rowsLevel = computed(() => {
	const action = stack.current?.level.action
	return Boolean(action && 'rows' in action)
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

offerMenu(props.clicked, props.subject.chart)

function descend(action: DrillAction) {
	const offered = pending.value
	if (!offered) return
	pending.value = undefined

	stack.push({
		level: { segment_filters: offered.segment.filters, action },
		pins: offered.segment.pins,
		actionLabel: 'rows' in action ? __('Rows') : `${__('by')} ${columnLabel(action.breakdown)}`,
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

// Dismissing the menu without choosing is the whole of the interaction when
// nothing is open behind it.
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

function popTo(depth: number) {
	if (depth <= 0) {
		open.value = false
		return
	}
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
		failed.value = false
		return
	}

	loading.value = true
	failed.value = false
	try {
		const fetched = await props.subject.fetch(stack.levels)
		if (token !== inFlight) return
		stack.remember(fetched)
		answer.value = fetched
	} catch (error) {
		if (token !== inFlight) return
		console.error('[insights] Could not drill down.', error)
		failed.value = true
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
		@segment-click="(click) => offerMenu(click, clickedChart)"
		@regrain="regrain"
		@pop-to="popTo"
		@closed="emit('close')"
	>
		<template v-if="answer" #actions>
			<slot name="actions" :answer="answer" :rows="rowsLevel" />
		</template>

		<template v-if="answer" #level-actions>
			<slot name="level-actions" :answer="answer" />
		</template>

		<template #rows="{ answer: level, findTarget }">
			<slot name="rows" :answer="level" :find-target="findTarget" />
		</template>
	</DrillDialog>
</template>
