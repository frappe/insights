<script setup>
import 'gridstack/dist/gridstack.min.css'
import GridStack from 'gridstack/dist/gridstack-all.js'
import { computed, nextTick, onMounted, watch } from 'vue'

const emit = defineEmits(['layoutChange'])
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

const key = computed(() => props.itemKey)
const items = computed(() => props.items)

let grid = null

onMounted(async () => {
	await nextTick()
	initializeGrid()
	attachChangeEvent()
	watchProps()
})

function initializeGrid() {
	grid = GridStack.init({
		animate: true,
		column: 20,
		float: false,
		...props.options,
	})
}

function attachChangeEvent() {
	grid.on('change', function (evt, updatedItems) {
		emit(
			'layoutChange',
			updatedItems.map((item) => {
				return {
					id: item.el.getAttribute('gs-id'),
					x: item.x,
					y: item.y,
					w: item.w,
					h: item.h,
				}
			})
		)
	})
}

function watchProps() {
	watch(() => props.disabled, disableGrid, { immediate: true })
}

function disableGrid(disabled) {
	if (disabled) {
		grid.disable()
	} else {
		grid.enable()
	}
}
</script>

<template>
	<div class="grid-stack">
		<div
			v-for="item in items"
			:key="item[key]"
			class="grid-stack-item"
			:gs-id="item[key]"
			:gs-w="item.w"
			:gs-h="item.h"
			:gs-x="item.x"
			:gs-y="item.y"
		>
			<div class="grid-stack-item-content">
				<slot name="item" v-bind="{ item }"> {{ item[key] }}</slot>
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
</style>
