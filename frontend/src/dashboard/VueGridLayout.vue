<template>
	<grid-layout ref="grid" :layout="layouts" v-bind="options" @update:layout="layouts = $event">
		<template #default="{ gridItemProps }">
			<grid-item
				v-for="(layout, index) in layouts"
				v-bind="gridItemProps"
				:key="layout.i"
				:i="layout.i"
				:x="layout.x"
				:y="layout.y"
				:w="layout.w"
				:h="layout.h"
			>
				<slot name="item" :item="props.items[index]">
					<pre class="h-full w-full rounded bg-white p-4 shadow">

						{{ { i: layout.i, x: layout.x, y: layout.y, w: layout.w, h: layout.h } }}

					</pre
					>
				</slot>
			</grid-item>
		</template>
	</grid-layout>
</template>

<script setup>
import { reactive, ref, watch, watchEffect, computed } from 'vue'

const emit = defineEmits(['update:layouts'])
const props = defineProps({
	items: { type: Array, required: true },
	layouts: { type: Array, required: true },
	disabled: { type: Boolean, default: false },
})
const options = reactive({
	colNum: 20,
	margin: [0, 0],
	rowHeight: 30,
	isDraggable: false,
	isResizable: false,
	responsive: true,
	verticalCompact: false,
	preventCollision: true,
	useCssTransforms: true,
	cols: { lg: 20, md: 20, sm: 20, xs: 1, xxs: 1 },
})
const layouts = computed({
	get: () => props.layouts,
	set: (value) => emit('update:layouts', value),
})

async function toggleEnable(disable) {
	if (options.isDraggable === !disable && options.isResizable === !disable) return
	options.isDraggable = !disable
	options.isResizable = !disable
}
watch(() => props.disabled, toggleEnable, 200)
</script>

<style lang="scss">
.vgl-layout {
	--vgl-placeholder-bg: #b1b1b1;
	--vgl-placeholder-opacity: 20%;
	--vgl-placeholder-z-index: 2;

	--vgl-item-resizing-z-index: 3;
	--vgl-item-resizing-opacity: 60%;
	--vgl-item-dragging-z-index: 3;
	--vgl-item-dragging-opacity: 100%;

	--vgl-resizer-size: 10px;
	--vgl-resizer-border-color: #444;
	--vgl-resizer-border-width: 2px;
}

.vgl-item--placeholder {
	z-index: var(--vgl-placeholder-z-index, 2);
	user-select: none;
	background-color: var(--vgl-placeholder-bg);
	opacity: var(--vgl-placeholder-opacity);
	transition-duration: 100ms;
	border-radius: 1rem;
}

.vgl-item__resizer {
	position: absolute;
	right: 10px;
	bottom: 10px;
	box-sizing: border-box;
	width: var(--vgl-resizer-size);
	height: var(--vgl-resizer-size);
	cursor: se-resize;
}

.vgl-item__resizer:before {
	position: absolute;
	inset: 0 3px 3px 0;
	content: '';
	border: 0 solid var(--vgl-resizer-border-color);
	border-right-width: var(--vgl-resizer-border-width);
	border-bottom-width: var(--vgl-resizer-border-width);
}
</style>
