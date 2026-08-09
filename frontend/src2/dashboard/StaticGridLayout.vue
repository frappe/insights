<script setup lang="ts">
import { useElementSize } from '@vueuse/core'
import { computed, ref } from 'vue'
import { GridLayoutItem, ROW_HEIGHT, placeGrid } from './grid_placement'

// The dashboard grid a reader gets: the same cells in the same places, drawn by
// CSS grid instead of by a layout engine.
//
// It takes the props `VueGridLayout` takes and ignores the two only an author
// can use, so the feed can carry either one and the page cannot tell them apart.
// `disabled` is always true here by construction — this is the grid that cannot
// be dragged — and nothing is ever written back, so there is no update to emit.
const props = defineProps<{
	modelValue?: GridLayoutItem[]
	cols?: number
	disabled?: boolean
	verticalCompact?: boolean
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

const gridStyle = computed(() => ({
	gridTemplateColumns: `repeat(${placement.value.columns}, minmax(0, 1fr))`,
	gridAutoRows: `${ROW_HEIGHT}px`,
}))

function cellStyle(layout: GridLayoutItem) {
	const cell = placement.value.cells[layout.i]
	if (!cell) return undefined
	return {
		gridColumn: `${cell.x + 1} / span ${cell.w}`,
		gridRow: `${cell.y + 1} / span ${cell.h}`,
	}
}
</script>

<template>
	<div ref="container" class="grid w-full" :style="gridStyle">
		<div
			v-for="(layout, index) in layouts"
			:key="layout.i"
			:style="cellStyle(layout)"
			class="min-w-0"
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
