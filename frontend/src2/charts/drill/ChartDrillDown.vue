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
// lives here and dies with it — the stack is ephemeral by design, so closing is
// all it takes to forget the path. Which door the levels come through is the
// subject's business; nothing here knows whether a chart was ever saved.
//
// `#actions` is what a surface may add to the level it is reading. It is a slot
// rather than a prop so that an authoring affordance and everything it imports
// stay out of the bundles that only read.
const props = defineProps<{
	/** what is being drilled: the shape a click is read against, and the door */
	subject: DrillSubject
	/** the click that opened this */
	clicked: ChartSegmentClick
}>()

const emit = defineEmits<{ close: [] }>()

defineSlots<{
	// eslint-disable-next-line no-unused-vars
	actions?: (props: { level: DrillLevelData }) => any
}>()

const stack = makeDrillStack()
const open = ref(false)
const data = ref<DrillLevelData>()
const loading = ref(false)
const failed = ref(false)

// what the menu is currently offering to split, and where it is drawn
const pending = ref<{ segment: DrillSegment; point: { x: number; y: number } }>()

// The level being read is the chart a click inside the dialog is read against.
// A records level has nothing to click, so there is nothing to read it against.
const clickedChart = computed<DrillChart>(() => {
	const action = stack.current?.level.action
	if (action && 'breakdown' in action) {
		return breakdownChart(action.breakdown, action.measure || '', data.value?.columns || [])
	}
	return props.subject.chart
})

const candidates = computed<DrillDimension[]>(() =>
	breakdownCandidates(
		props.subject.dimensions,
		[...stack.pinned, ...(pending.value?.segment.pins || [])],
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
		segmentLabel: offered.segment.label,
		actionLabel:
			'records' in action ? __('Records') : `${__('by')} ${columnLabel(action.breakdown)}`,
	})
	open.value = true
	load()
}

function chooseRecords() {
	descend({ records: true, measure: pending.value?.segment.measure })
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
	const remembered = stack.answer()
	if (remembered) {
		data.value = remembered
		loading.value = false
		failed.value = false
		return
	}

	loading.value = true
	failed.value = false
	try {
		const answer = await props.subject.fetch(stack.levels)
		if (token !== inFlight) return
		stack.remember(answer)
		data.value = answer
	} catch (error) {
		if (token !== inFlight) return
		console.error('[insights] Could not drill down.', error)
		failed.value = true
		data.value = undefined
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
		@records="chooseRecords"
		@breakdown="chooseBreakdown"
		@close="dismissMenu"
	/>

	<!-- Both ways out are the same way out: nothing here is kept, so once the
	     dialog is gone the surface is back to where it started. -->
	<DrillDialog
		v-model="open"
		:stack="stack"
		:title="props.subject.title"
		:data="data"
		:loading="loading"
		:failed="failed"
		@segment-click="(click) => offerMenu(click, clickedChart)"
		@pop-to="popTo"
		@closed="emit('close')"
	>
		<template v-if="data" #actions>
			<slot name="actions" :level="data" />
		</template>
	</DrillDialog>
</template>
