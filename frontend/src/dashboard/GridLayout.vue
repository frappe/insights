<script setup>
import 'gridstack/dist/gridstack.min.css'
import GridStack from 'gridstack/dist/gridstack-all.js'
import { nextTick, onMounted, watch, ref } from 'vue'
import { debounce } from 'frappe-ui'

const props = defineProps({
	items: {
		type: Array,
		required: true,
	},
	itemKey: {
		type: String,
		default: 'id',
	},
	disabled: {
		type: Boolean,
		default: false,
	},
	options: {
		type: Object,
		default: {},
	},
})

let grid = null
const gridRef = ref(null)
defineExpose({ grid: gridRef })

onMounted(async () => {
	await nextTick()
	initializeGrid()
	watchProps()
})

function initializeGrid() {
	grid = GridStack.init({
		animate: true,
		column: 20,
		float: false,
		alwaysShowResizeHandle: true,
		...props.options,
	})
	gridRef.value = grid
}

function watchProps() {
	watch(() => props.disabled, toggleGrid, { immediate: true })
	watch(() => props.items, debounce(updateGrid, 300))
}

function toggleGrid() {
	if (props.disabled) {
		grid.disable()
	} else {
		grid.enable()
	}
}

async function updateGrid() {
	grid.destroy(false)
	initializeGrid()
	toggleGrid()
}
</script>

<template>
	<div class="grid-stack">
		<div
			v-for="item in props.items"
			:key="item[props.itemKey]"
			class="grid-stack-item"
			:gs-id="item[props.itemKey]"
			:gs-w="item.w"
			:gs-h="item.h"
			:gs-x="item.x"
			:gs-y="item.y"
		>
			<div class="grid-stack-item-content">
				<slot name="item" v-bind="{ item }"> {{ item[props.itemKey] }}</slot>
			</div>
		</div>
	</div>
</template>

<style lang="scss">
/* prettier-ignore */
.grid-stack > .grid-stack-item {
	min-width: 5% !important;
}
.grid-stack .grid-stack-placeholder > .placeholder-content {
	@apply rounded-md bg-gray-100;
}
@for $i from 1 through 20 {
	.grid-stack > .grid-stack-item[gs-w='#{$i}'] {
		width: percentage(calc($i / 20));
	}
	.grid-stack > .grid-stack-item[gs-x='#{$i}'] {
		left: percentage(calc($i / 20));
	}
	.grid-stack > .grid-stack-item[gs-min-w='#{$i}'] {
		min-width: percentage(calc($i / 20));
	}
	.grid-stack > .grid-stack-item[gs-max-w='#{$i}'] {
		max-width: percentage(calc($i / 20));
	}
}
.grid-stack > .grid-stack-item > .ui-resizable-se {
	@apply mr-1 mb-1 h-4 w-4 rotate-0 border-r-4 border-b-4 bg-none;
	z-index: 0 !important;
}
</style>
