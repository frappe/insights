<script setup lang="ts">
import { useElementSize } from '@vueuse/core'
import { computed, ref } from 'vue'
import { GridLayoutItem, ROW_HEIGHT, placeGrid } from './grid_placement'

// The dashboard grid, drawn. It works out where every cell goes and puts it
// there — no pointer, no measurement beyond its own width, and it never writes a
// layout back.
//
// A reader is served this component directly. An author is served
// `EditableGridLayout`, which wraps it and adds the gesture. So there is one
// piece of code that decides where a card sits on a dashboard, and both surfaces
// get their answer from it.
//
// A cell is taken out of the flow and moved by `transform`, rather than dropped
// into a CSS grid slot, because grid placement cannot be animated and a
// transform can. That is the whole reason: when an author drags one card, the
// cards it displaces have to slide out of the way, and cards that jump between
// slots read as the page glitching. Nothing is measured to do it — a column is a
// share of the grid's width, so the shift is written in percent and the browser
// works out the pixels.
//
// `disabled` is accepted and ignored: this grid cannot be dragged either way,
// and taking the prop lets the feed carry either grid without the page asking
// which one it has.
const props = defineProps<{
	modelValue?: GridLayoutItem[]
	cols?: number
	disabled?: boolean
	verticalCompact?: boolean
	/**
	 * One cell held above the grid, offset from where it belongs by this many
	 * pixels. It is what a card being dragged looks like: it follows the hand
	 * rather than the layout, and the slot it will drop into stays empty behind
	 * it. A surface with nothing to drag passes nothing.
	 */
	lifted?: { i: string; x: number; y: number }
}>()

const layouts = computed(() => props.modelValue || [])

// Measured off the grid's own box rather than the window: an island sits in
// whatever width the desk page gives it, which is not the viewport's.
const container = ref<HTMLElement>()
const { width } = useElementSize(container)

const placement = computed(() =>
	placeGrid(layouts.value, {
		columns: props.cols || 12,
		width: width.value,
		verticalCompact: props.verticalCompact ?? true,
	}),
)

// Every cell is out of the flow, so there is nothing left to give the grid a
// height. It is as tall as its lowest cell reaches.
const height = computed(() => {
	const rows = Object.values(placement.value.cells).map((cell) => cell.y + cell.h)
	return Math.max(0, ...rows) * ROW_HEIGHT
})

/** Where a cell's slot is: the box it occupies when nothing is being held. */
function slotStyle(i: string) {
	const cell = placement.value.cells[i]
	if (!cell) return undefined

	// A cell is `w` of the grid's `columns` wide, so shifting it `x` columns is
	// shifting it `x / w` of its own width — which is what a percentage in
	// `translate` means. No column is ever measured in pixels.
	return {
		width: `${(cell.w / placement.value.columns) * 100}%`,
		height: `${cell.h * ROW_HEIGHT}px`,
		across: `${(cell.x / cell.w) * 100}%`,
		down: `${cell.y * ROW_HEIGHT}px`,
	}
}

function cellStyle(layout: GridLayoutItem) {
	const slot = slotStyle(layout.i)
	if (!slot) return undefined

	const { across, down, ...box } = slot
	if (props.lifted?.i !== layout.i) {
		return { ...box, transform: `translate(${across}, ${down})` }
	}

	// The held cell is drawn where the hand is, above the rest, and it does not
	// animate — a card that eases towards the cursor is a card that lags it.
	return {
		...box,
		transform: `translate(calc(${across} + ${props.lifted.x}px), calc(${down} + ${props.lifted.y}px))`,
		transition: 'none',
		zIndex: '3',
	}
}

/** The empty slot under a held cell, so the grid shows where it will drop. */
const landingStyle = computed(() => {
	const slot = props.lifted && slotStyle(props.lifted.i)
	if (!slot) return undefined
	const { across, down, ...box } = slot
	return { ...box, transform: `translate(${across}, ${down})` }
})
</script>

<template>
	<div ref="container" class="relative w-full" :style="{ height: `${height}px` }">
		<!-- Padded like a card, so the outline lands exactly where the card will. -->
		<div
			v-if="landingStyle"
			:style="landingStyle"
			class="absolute top-0 left-0 p-2 transition-[transform,width,height] duration-150 ease-out"
		>
			<div
				class="h-full w-full rounded-4 border border-dashed border-outline-gray-3 bg-surface-gray-2"
			/>
		</div>

		<div
			v-for="(layout, index) in layouts"
			:key="layout.i"
			:style="cellStyle(layout)"
			class="absolute top-0 left-0 transition-[transform,width,height] duration-150 ease-out"
		>
			<slot
				name="item"
				:index="index"
				:i="layout.i"
				:x="layout.x"
				:y="layout.y"
				:w="layout.w"
				:h="layout.h"
			/>
		</div>
	</div>
</template>
