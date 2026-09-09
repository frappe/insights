<script setup lang="ts">
import { useElementSize } from '@vueuse/core'
import { computed, onBeforeUnmount, ref } from 'vue'
import type { BreakpointKey, Layout, WorkbookDashboardItemLayout } from '../types/workbook.types'
import StaticGridLayout from './StaticGridLayout.vue'
import {
	BREAKPOINTS,
	ROW_HEIGHT,
	breakpointFor,
	placementsFor,
	resolveLayouts,
} from './grid_placement'

// The dashboard grid an author gets: the reader's grid, plus a pointer.
//
// It draws nothing itself. The cells are laid out by `StaticGridLayout`, the
// same component a reader is served, so the two surfaces cannot drift apart —
// what an author drags a card into is the grid a reader will be shown. All this
// component adds is the gesture: it turns pointer movement into a column and a
// row, hands the disturbed grid to `resolveLayouts`, and passes the answer back
// down to be drawn.
//
// The layout is only written back when the pointer is released. A drag is one
// edit, not one per frame, so undo and autosave see a move rather than a trail.
const props = defineProps<{
	items?: WorkbookDashboardItemLayout[]
	/** Arrange this breakpoint rather than the one the grid measures. */
	breakpoint?: BreakpointKey
	disabled?: boolean
	verticalCompact?: boolean
}>()

// A move names the breakpoint it arranged. Every breakpoint is dragged on the
// same grid, so the gesture cannot tell the parent where to store it.
const emit = defineEmits<{ move: [key: BreakpointKey, layouts: Layout[]] }>()

const container = ref<HTMLElement>()
const { width } = useElementSize(container)

// The one place a breakpoint is picked for this grid. The drawing half is told
// which one, rather than measuring the same box a second time and risking a
// gesture that arranges a breakpoint other than the one on screen.
const active = computed(
	() => BREAKPOINTS.find((item) => item.key === props.breakpoint) || breakpointFor(width.value),
)

const stored = computed(() => placementsFor(props.items || [], active.value.key))

const editable = computed(() => !props.disabled)

type Gesture = {
	/** the cell under the pointer */
	i: string
	kind: 'move' | 'resize'
	pointerX: number
	pointerY: number
	/** the grid as it stood when the pointer went down — see `resolveLayouts` */
	from: Layout[]
	/** the cell the pointer is asking for, before the grid has its say */
	asked: Layout
	/** where the grid put it. What the card is held away from. */
	landed: Layout
	/** how far the card is held from `landed`, so it stays under the hand */
	offsetX: number
	offsetY: number
}

const gesture = ref<Gesture>()
// what the grid looks like mid-gesture. Nothing else may write it.
const settling = ref<Layout[]>()

const layouts = computed(() => settling.value || stored.value)

// A card carries its own controls, and a press on one of those is a press on the
// control. Everything else on a card is somewhere to grab it by.
const CONTROLS = 'button, a, input, select, textarea, [contenteditable]'

function clamp(value: number, min: number, max: number) {
	return Math.min(Math.max(value, min), max)
}

function sameCell(a: Layout, b: Layout) {
	return a.x === b.x && a.y === b.y && a.w === b.w && a.h === b.h
}

function start(kind: Gesture['kind'], i: string, event: PointerEvent) {
	if (!editable.value || event.button !== 0) return
	if (kind === 'move' && (event.target as HTMLElement).closest(CONTROLS)) return

	// Settled first, because a stored layout is not always the layout on screen —
	// compaction can be turned on over a grid saved loosely. The drag has to start
	// from the cells the author can see, or the card jumps on the first move.
	const from = resolveLayouts(stored.value, {
		verticalCompact: props.verticalCompact ?? true,
	})
	const grabbed = from.find((item) => item.i === i)
	if (!grabbed) return

	gesture.value = {
		i,
		kind,
		pointerX: event.clientX,
		pointerY: event.clientY,
		from,
		asked: grabbed,
		landed: grabbed,
		offsetX: 0,
		offsetY: 0,
	}
	event.preventDefault()

	// Listened for on the window, not on the card: a fast drag leaves the card
	// behind and the gesture has to keep following the pointer, and a pointer
	// released off the grid — or over a card that unmounted — still ends it.
	window.addEventListener('pointermove', track)
	window.addEventListener('pointerup', finish)
	window.addEventListener('pointercancel', finish)
}

function track(event: PointerEvent) {
	const current = gesture.value
	if (!current) return

	const columnWidth = width.value / active.value.columns
	const dragged = current.from.find((item) => item.i === current.i)
	if (!dragged || !columnWidth) return

	const dx = event.clientX - current.pointerX
	const dy = event.clientY - current.pointerY
	const acrossColumns = Math.round(dx / columnWidth)
	const downRows = Math.round(dy / ROW_HEIGHT)

	const asked =
		current.kind === 'move'
			? {
					...dragged,
					x: clamp(dragged.x + acrossColumns, 0, active.value.columns - dragged.w),
					y: Math.max(dragged.y + downRows, 0),
			  }
			: {
					...dragged,
					w: clamp(dragged.w + acrossColumns, 1, active.value.columns - dragged.x),
					h: Math.max(dragged.h + downRows, 1),
			  }

	// The grid is only settled again when the pointer has asked for a different
	// cell. Between two snaps it is the same grid, and re-laying it out on every
	// pointer event is work the drag has to pay for at 120 events a second.
	if (!sameCell(asked, current.asked)) {
		const settled = resolveLayouts(
			current.from.map((item) => (item.i === current.i ? asked : item)),
			{ pinned: current.i, verticalCompact: props.verticalCompact ?? true },
		)
		current.asked = asked
		current.landed = settled.find((item) => item.i === current.i) || asked
		settling.value = settled
	}

	// How far the card is held from the slot it will drop into, so it stays under
	// the hand.
	//
	// Measured against where the cell `landed`, never against where the pointer
	// `asked`. Compaction can move a cell above the row the pointer asked for, and
	// an offset taken from the request would leave the card up there.
	//
	// A resize is not held at all. It snaps outright, because a card drawn at a
	// width it will not keep is a card whose contents lay out twice.
	const held = current.kind === 'move'
	current.offsetX = held ? dx - (current.landed.x - dragged.x) * columnWidth : 0
	current.offsetY = held ? dy - (current.landed.y - dragged.y) * ROW_HEIGHT : 0
}

function finish() {
	stopListening()
	const resolved = settling.value
	gesture.value = undefined
	if (resolved) emit('move', active.value.key, resolved)
	// dropped only after the parent has been told, so the grid is never drawn
	// from the layout the gesture started at
	settling.value = undefined
}

function stopListening() {
	window.removeEventListener('pointermove', track)
	window.removeEventListener('pointerup', finish)
	window.removeEventListener('pointercancel', finish)
}

onBeforeUnmount(stopListening)

// The card under the hand, as the grid needs to be told about it. Drawing it —
// holding it off its slot, raising it, leaving the slot showing — is the grid's
// job, so all that is handed over is how far it is being held.
const lifted = computed(() => {
	const current = gesture.value
	if (!current) return undefined
	return { i: current.i, x: current.offsetX, y: current.offsetY }
})
</script>

<template>
	<div ref="container" class="w-full">
		<StaticGridLayout
			:layouts="layouts"
			:breakpoint="active.key"
			:verticalCompact="verticalCompact"
			:lifted="lifted"
		>
			<template #item="cell">
				<!-- `touch-none` is what makes a finger drag a card rather than
				     scroll the page. The browser decides between the two the moment
				     a touch lands, before any handler runs, so it has to be told in
				     CSS beforehand — a `preventDefault` in `pointerdown` is already
				     too late. Only while editing: it costs the reader nothing, and
				     an author who wants to scroll starts the drag off a card. -->
				<div
					class="relative h-full w-full"
					:class="[
						editable ? 'cursor-grab touch-none' : '',
						gesture?.i === cell.i ? 'cursor-grabbing' : '',
					]"
					@pointerdown="start('move', cell.i, $event)"
				>
					<!-- The card being carried is raised by a shadow laid under it,
					     inset to the card's own edges. Under it, and not on it: a
					     `filter` on the card would re-render its chart canvas on
					     every frame of the drag, which is the one thing a drag
					     cannot spend. -->
					<div
						v-if="gesture?.i === cell.i"
						class="pointer-events-none absolute inset-2 rounded-4 bg-surface-base shadow-2xl"
					/>
					<slot name="item" v-bind="cell" />
					<!-- The corner an author grabs is 24px, the corner they see is
					     8px. A mark big enough to take a fingertip would be a mark
					     that draws the eye away from the card it sits on. -->
					<div
						v-if="editable"
						class="absolute right-0 bottom-0 h-6 w-6 cursor-se-resize"
						@pointerdown.stop="start('resize', cell.i, $event)"
					>
						<div
							class="absolute right-3 bottom-3 h-2 w-2 border-r-2 border-b-2 border-outline-gray-5"
						/>
					</div>
				</div>
			</template>
		</StaticGridLayout>
	</div>
</template>
